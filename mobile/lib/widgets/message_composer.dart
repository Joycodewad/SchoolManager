import 'dart:async';
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import '../api/client.dart';
import '../core/theme.dart';
import 'attachments.dart';

/// Fichier choisi, en attente d'envoi.
class PendingAttachment {
  PendingAttachment({
    required this.path,
    required this.name,
    this.isAudio = false,
    this.durationSeconds,
  });

  final String path;
  final String name;
  final bool isAudio;
  final int? durationSeconds;

  UploadFile toUpload() => UploadFile(path: path, filename: name);
}

/// Barre de rédaction : texte, pièces jointes et enregistrement vocal.
///
/// Le bouton de droite change de rôle selon la saisie : micro quand le champ
/// est vide, envoi dès qu'il y a du texte ou un fichier — la convention des
/// messageries que tout le monde connaît.
class MessageComposer extends StatefulWidget {
  const MessageComposer({
    super.key,
    required this.controller,
    required this.sending,
    required this.onSend,
  });

  final TextEditingController controller;
  final bool sending;

  /// Appelé avec le texte et les fichiers ; le parent gère l'envoi réseau.
  final Future<void> Function(String body, List<PendingAttachment> files) onSend;

  @override
  State<MessageComposer> createState() => _MessageComposerState();
}

class _MessageComposerState extends State<MessageComposer> {
  final _recorder = AudioRecorder();
  final List<PendingAttachment> _pending = [];

  bool _recording = false;
  Duration _elapsed = Duration.zero;
  Timer? _ticker;
  String? _recordingPath;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onTextChanged);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onTextChanged);
    _ticker?.cancel();
    _recorder.dispose();
    super.dispose();
  }

  void _onTextChanged() => setState(() {});

  bool get _canSend =>
      widget.controller.text.trim().isNotEmpty || _pending.isNotEmpty;

  // ── Pièces jointes ────────────────────────────────────────────────────

  Future<void> _pickImages() async {
    final picker = ImagePicker();
    final images = await picker.pickMultiImage();
    if (images.isEmpty) return;
    setState(() {
      for (final image in images) {
        _pending.add(PendingAttachment(path: image.path, name: image.name));
      }
    });
  }

  Future<void> _takePhoto() async {
    final image = await ImagePicker().pickImage(source: ImageSource.camera);
    if (image == null) return;
    setState(() =>
        _pending.add(PendingAttachment(path: image.path, name: image.name)));
  }

  Future<void> _pickVideo() async {
    final video = await ImagePicker().pickVideo(source: ImageSource.gallery);
    if (video == null) return;
    setState(() =>
        _pending.add(PendingAttachment(path: video.path, name: video.name)));
  }

  Future<void> _pickDocuments() async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: true,
      type: FileType.custom,
      // Les types que le serveur accepte : proposer davantage exposerait à un
      // refus après coup.
      allowedExtensions: const [
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv',
      ],
    );
    if (result == null) return;
    setState(() {
      for (final file in result.files) {
        if (file.path == null) continue;
        _pending.add(PendingAttachment(path: file.path!, name: file.name));
      }
    });
  }

  void _showAttachMenu() {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (final entry in [
              (Icons.photo_library_outlined, 'Photos', _pickImages),
              (Icons.photo_camera_outlined, 'Appareil photo', _takePhoto),
              (Icons.videocam_outlined, 'Vidéo', _pickVideo),
              (Icons.attach_file, 'Document (PDF, Word, Excel)', _pickDocuments),
            ])
              ListTile(
                leading: Icon(entry.$1, color: AppColors.primary),
                title: Text(entry.$2),
                onTap: () {
                  Navigator.of(sheetContext).pop();
                  entry.$3();
                },
              ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }

  // ── Enregistrement vocal ──────────────────────────────────────────────

  Future<void> _startRecording() async {
    if (!await _recorder.hasPermission()) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Autorisez l’accès au micro pour enregistrer.'),
        ),
      );
      return;
    }

    final directory = await getTemporaryDirectory();
    final path =
        '${directory.path}/vocal_${DateTime.now().millisecondsSinceEpoch}.m4a';
    // AAC dans un conteneur M4A : lu partout, et bien plus léger que du WAV
    // sur un forfait mobile.
    await _recorder.start(
      const RecordConfig(encoder: AudioEncoder.aacLc, bitRate: 64000),
      path: path,
    );

    setState(() {
      _recording = true;
      _recordingPath = path;
      _elapsed = Duration.zero;
    });
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) {
        setState(() => _elapsed += const Duration(seconds: 1));
      }
    });
  }

  Future<void> _stopRecording({required bool keep}) async {
    _ticker?.cancel();
    final path = await _recorder.stop();
    final seconds = _elapsed.inSeconds;
    if (!mounted) return;

    setState(() {
      _recording = false;
      _elapsed = Duration.zero;
    });

    final file = path ?? _recordingPath;
    if (file == null) return;

    if (!keep) {
      // Annulation : le fichier temporaire n'a plus de raison d'exister.
      await File(file).delete().catchError((_) => File(file));
      return;
    }
    // Un vocal d'une seconde est presque toujours un appui accidentel.
    if (seconds < 1) {
      await File(file).delete().catchError((_) => File(file));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Enregistrement trop court.')),
        );
      }
      return;
    }

    setState(() {
      _pending.add(PendingAttachment(
        path: file,
        name: 'message-vocal.m4a',
        isAudio: true,
        durationSeconds: seconds,
      ));
    });
  }

  Future<void> _submit() async {
    final body = widget.controller.text.trim();
    final files = List<PendingAttachment>.from(_pending);
    await widget.onSend(body, files);
    if (mounted) setState(() => _pending.clear());
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(
        left: 8,
        right: 8,
        top: 8,
        bottom: MediaQuery.of(context).viewInsets.bottom + 10,
      ),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: AppColors.border)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (_pending.isNotEmpty) _PendingStrip(
            items: _pending,
            onRemove: (index) => setState(() => _pending.removeAt(index)),
          ),
          if (_recording)
            _RecordingBar(
              elapsed: _elapsed,
              onCancel: () => _stopRecording(keep: false),
              onStop: () => _stopRecording(keep: true),
            )
          else
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                IconButton(
                  onPressed: widget.sending ? null : _showAttachMenu,
                  icon: const Icon(Icons.add_circle_outline),
                  color: AppColors.slate,
                  tooltip: 'Joindre un fichier',
                ),
                Expanded(
                  child: TextField(
                    controller: widget.controller,
                    minLines: 1,
                    maxLines: 4,
                    textCapitalization: TextCapitalization.sentences,
                    decoration: const InputDecoration(
                      hintText: 'Votre message…',
                      isDense: true,
                      contentPadding:
                          EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    ),
                  ),
                ),
                const SizedBox(width: 6),
                // Micro quand il n'y a rien à envoyer, avion sinon.
                IconButton.filled(
                  onPressed: widget.sending
                      ? null
                      : _canSend
                          ? _submit
                          : _startRecording,
                  icon: widget.sending
                      ? const SizedBox(
                          height: 18,
                          width: 18,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white),
                        )
                      : Icon(_canSend ? Icons.send : Icons.mic, size: 20),
                  tooltip: _canSend ? 'Envoyer' : 'Enregistrer un message vocal',
                ),
              ],
            ),
        ],
      ),
    );
  }
}

/// Bandeau des fichiers en attente d'envoi.
class _PendingStrip extends StatelessWidget {
  const _PendingStrip({required this.items, required this.onRemove});

  final List<PendingAttachment> items;
  final void Function(int index) onRemove;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 74,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.fromLTRB(6, 4, 6, 8),
        itemCount: items.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final item = items[index];
          final isImage = RegExp(r'\.(jpe?g|png|gif|webp|heic)$',
                  caseSensitive: false)
              .hasMatch(item.name);

          return Stack(
            clipBehavior: Clip.none,
            children: [
              Container(
                width: 62,
                height: 62,
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  border: Border.all(color: AppColors.border),
                  borderRadius: BorderRadius.circular(9),
                ),
                clipBehavior: Clip.antiAlias,
                child: isImage
                    ? Image.file(File(item.path), fit: BoxFit.cover)
                    : Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            item.isAudio
                                ? Icons.mic
                                : documentStyle(item.name).icon,
                            size: 22,
                            color: item.isAudio
                                ? AppColors.primary
                                : documentStyle(item.name).color,
                          ),
                          const SizedBox(height: 3),
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 3),
                            child: Text(
                              item.isAudio
                                  ? '${item.durationSeconds}s'
                                  : item.name,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                  fontSize: 9, color: AppColors.muted),
                            ),
                          ),
                        ],
                      ),
              ),
              Positioned(
                top: -6,
                right: -6,
                child: GestureDetector(
                  onTap: () => onRemove(index),
                  child: Container(
                    padding: const EdgeInsets.all(2),
                    decoration: const BoxDecoration(
                      color: AppColors.navy,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.close,
                        size: 13, color: Colors.white),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

/// Barre affichée pendant l'enregistrement d'un vocal.
class _RecordingBar extends StatelessWidget {
  const _RecordingBar({
    required this.elapsed,
    required this.onCancel,
    required this.onStop,
  });

  final Duration elapsed;
  final VoidCallback onCancel;
  final VoidCallback onStop;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
      child: Row(
        children: [
          IconButton(
            onPressed: onCancel,
            icon: const Icon(Icons.delete_outline, color: AppColors.danger),
            tooltip: 'Annuler',
          ),
          const SizedBox(width: 4),
          const _PulsingDot(),
          const SizedBox(width: 10),
          Text(
            '${elapsed.inMinutes}:'
            '${(elapsed.inSeconds % 60).toString().padLeft(2, '0')}',
            style: const TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w600,
              color: AppColors.navy,
            ),
          ),
          const Spacer(),
          const Text(
            'Enregistrement…',
            style: TextStyle(fontSize: 12.5, color: AppColors.muted),
          ),
          const SizedBox(width: 10),
          IconButton.filled(
            onPressed: onStop,
            icon: const Icon(Icons.check, size: 20),
            tooltip: 'Terminer',
          ),
        ],
      ),
    );
  }
}

/// Point rouge clignotant : le repère habituel d'un enregistrement en cours.
class _PulsingDot extends StatefulWidget {
  const _PulsingDot();

  @override
  State<_PulsingDot> createState() => _PulsingDotState();
}

class _PulsingDotState extends State<_PulsingDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _controller,
      child: Container(
        height: 11,
        width: 11,
        decoration: const BoxDecoration(
          color: AppColors.danger,
          shape: BoxShape.circle,
        ),
      ),
    );
  }
}
