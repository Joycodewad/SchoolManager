import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/material.dart';
import 'package:open_filex/open_filex.dart';

import '../core/theme.dart';
import '../models/communication.dart';

/// Icône et couleur d'un document, d'après son extension.
({IconData icon, Color color}) documentStyle(String name) {
  final lower = name.toLowerCase();
  if (lower.endsWith('.pdf')) {
    return (icon: Icons.picture_as_pdf, color: AppColors.danger);
  }
  if (lower.endsWith('.doc') || lower.endsWith('.docx')) {
    return (icon: Icons.description, color: AppColors.primary);
  }
  if (lower.endsWith('.xls') || lower.endsWith('.xlsx') ||
      lower.endsWith('.csv')) {
    return (icon: Icons.table_chart, color: AppColors.success);
  }
  return (icon: Icons.insert_drive_file, color: AppColors.muted);
}

/// Pièce jointe telle qu'elle apparaît dans une bulle de message.
class AttachmentView extends StatelessWidget {
  const AttachmentView({
    super.key,
    required this.attachment,
    required this.isMine,
  });

  final Attachment attachment;
  final bool isMine;

  @override
  Widget build(BuildContext context) {
    return switch (attachment.kind) {
      AttachmentKind.image => _ImageAttachment(attachment: attachment),
      AttachmentKind.audio =>
        AudioAttachment(attachment: attachment, isMine: isMine),
      AttachmentKind.video =>
        _FileAttachment(attachment: attachment, isMine: isMine, isVideo: true),
      AttachmentKind.document =>
        _FileAttachment(attachment: attachment, isMine: isMine, isVideo: false),
    };
  }
}

class _ImageAttachment extends StatelessWidget {
  const _ImageAttachment({required this.attachment});

  final Attachment attachment;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => _ImageViewer(attachment: attachment),
        ),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(10),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 220, minWidth: 140),
          child: Image.network(
            attachment.url,
            fit: BoxFit.cover,
            loadingBuilder: (context, child, progress) => progress == null
                ? child
                : const SizedBox(
                    height: 140,
                    width: 180,
                    child: Center(child: CircularProgressIndicator()),
                  ),
            // Une image illisible ne doit pas casser le fil : on retombe sur
            // une vignette d'échec, cliquable comme les autres.
            errorBuilder: (context, error, stack) => Container(
              height: 120,
              width: 180,
              color: AppColors.border,
              child: const Center(
                child: Icon(Icons.broken_image_outlined,
                    color: AppColors.muted, size: 30),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Image en plein écran, avec zoom.
class _ImageViewer extends StatelessWidget {
  const _ImageViewer({required this.attachment});

  final Attachment attachment;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text(
          attachment.name,
          style: const TextStyle(color: Colors.white, fontSize: 15),
        ),
      ),
      body: Center(
        child: InteractiveViewer(
          maxScale: 5,
          child: Image.network(
            attachment.url,
            errorBuilder: (context, error, stack) => const Icon(
              Icons.broken_image_outlined,
              color: Colors.white38,
              size: 60,
            ),
          ),
        ),
      ),
    );
  }
}

/// Vidéo ou document : une tuile qui ouvre le fichier avec l'application du
/// téléphone. Embarquer un lecteur vidéo et un lecteur PDF alourdirait
/// l'application pour un usage que le système sait déjà rendre.
class _FileAttachment extends StatefulWidget {
  const _FileAttachment({
    required this.attachment,
    required this.isMine,
    required this.isVideo,
  });

  final Attachment attachment;
  final bool isMine;
  final bool isVideo;

  @override
  State<_FileAttachment> createState() => _FileAttachmentState();
}

class _FileAttachmentState extends State<_FileAttachment> {
  bool _opening = false;

  Future<void> _open() async {
    setState(() => _opening = true);
    // `OpenFilex` accepte une URL : le téléchargement puis l'ouverture sont
    // délégués au système, qui sait choisir l'application adaptée.
    final result = await OpenFilex.open(widget.attachment.url);
    if (!mounted) return;
    setState(() => _opening = false);
    if (result.type != ResultType.done) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Aucune application ne peut ouvrir ce fichier.'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final style = widget.isVideo
        ? (icon: Icons.play_circle_outline, color: AppColors.info)
        : documentStyle(widget.attachment.name);
    final onDark = widget.isMine;

    return InkWell(
      onTap: _opening ? null : _open,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: onDark
              ? Colors.white.withValues(alpha: 0.16)
              : AppColors.surface,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (_opening)
              const SizedBox(
                height: 26,
                width: 26,
                child: CircularProgressIndicator(strokeWidth: 2.2),
              )
            else
              Icon(style.icon,
                  size: 26, color: onDark ? Colors.white : style.color),
            const SizedBox(width: 10),
            Flexible(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    widget.attachment.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: onDark ? Colors.white : AppColors.navy,
                    ),
                  ),
                  Text(
                    [
                      widget.attachment.readableSize,
                      if (widget.attachment.readableDuration.isNotEmpty)
                        widget.attachment.readableDuration,
                    ].join(' · '),
                    style: TextStyle(
                      fontSize: 11,
                      color: onDark ? Colors.white70 : AppColors.muted,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Lecteur de message vocal : bouton, progression et durée.
class AudioAttachment extends StatefulWidget {
  const AudioAttachment({
    super.key,
    required this.attachment,
    required this.isMine,
  });

  final Attachment attachment;
  final bool isMine;

  @override
  State<AudioAttachment> createState() => _AudioAttachmentState();
}

class _AudioAttachmentState extends State<AudioAttachment> {
  late final AudioPlayer _player = AudioPlayer();
  Duration _position = Duration.zero;
  Duration _total = Duration.zero;
  bool _playing = false;

  @override
  void initState() {
    super.initState();
    final declared = widget.attachment.durationSeconds;
    if (declared != null && declared > 0) {
      _total = Duration(seconds: declared);
    }
    _player.onPositionChanged.listen((value) {
      if (mounted) setState(() => _position = value);
    });
    _player.onDurationChanged.listen((value) {
      if (mounted) setState(() => _total = value);
    });
    _player.onPlayerComplete.listen((_) {
      if (!mounted) return;
      // Remise à zéro en fin de lecture, pour pouvoir réécouter d'un tap.
      setState(() {
        _playing = false;
        _position = Duration.zero;
      });
    });
  }

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }

  Future<void> _toggle() async {
    if (_playing) {
      await _player.pause();
      if (mounted) setState(() => _playing = false);
      return;
    }
    await _player.play(UrlSource(widget.attachment.url));
    if (mounted) setState(() => _playing = true);
  }

  String _stamp(Duration value) =>
      '${value.inMinutes}:${(value.inSeconds % 60).toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) {
    final onDark = widget.isMine;
    final progress = _total.inMilliseconds == 0
        ? 0.0
        : (_position.inMilliseconds / _total.inMilliseconds).clamp(0.0, 1.0);

    return SizedBox(
      width: 210,
      child: Row(
        children: [
          IconButton(
            onPressed: _toggle,
            icon: Icon(
              _playing ? Icons.pause_circle_filled : Icons.play_circle_fill,
              size: 34,
              color: onDark ? Colors.white : AppColors.primary,
            ),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(3),
                  child: LinearProgressIndicator(
                    value: progress,
                    minHeight: 4,
                    backgroundColor: onDark
                        ? Colors.white.withValues(alpha: 0.3)
                        : AppColors.border,
                    valueColor: AlwaysStoppedAnimation(
                      onDark ? Colors.white : AppColors.primary,
                    ),
                  ),
                ),
                const SizedBox(height: 5),
                Text(
                  _playing || _position > Duration.zero
                      ? '${_stamp(_position)} / ${_stamp(_total)}'
                      : _stamp(_total),
                  style: TextStyle(
                    fontSize: 11,
                    color: onDark ? Colors.white70 : AppColors.muted,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
