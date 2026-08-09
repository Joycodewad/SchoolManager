import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/client.dart';
import '../../api/services.dart';
import '../../core/roles.dart';
import '../../core/theme.dart';
import '../../models/communication.dart';
import '../../state/session_state.dart';
import '../../widgets/common.dart';
import '../../widgets/screen_scaffold.dart';

/// Couleur d'une priorité d'annonce.
Color priorityColor(String priority) => switch (priority) {
      'urgente' => AppColors.danger,
      'importante' => AppColors.warning,
      _ => AppColors.info,
    };

/// Annonces de l'établissement.
///
/// Le serveur ne renvoie que celles qui concernent l'utilisateur : une annonce
/// ciblant les comptables n'atteint pas les enseignants.
class AnnouncementsScreen extends StatefulWidget {
  const AnnouncementsScreen({super.key});

  @override
  State<AnnouncementsScreen> createState() => _AnnouncementsScreenState();
}

class _AnnouncementsScreenState extends State<AnnouncementsScreen> {
  Future<({List<Announcement> items, int unread, bool canPublish})>? _future;
  int? _loadedFor;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final session = context.watch<SessionState>();
    final key = Object.hash(session.school?.id, session.year?.id);
    if (_loadedFor != key) {
      _loadedFor = key;
      _future = _load(session);
    }
  }

  Future<({List<Announcement> items, int unread, bool canPublish})> _load(
      SessionState session) {
    final schoolId = session.school?.id;
    if (schoolId == null) {
      return Future.value((items: <Announcement>[], unread: 0, canPublish: false));
    }
    return AnnouncementService(session.client).list(schoolId);
  }

  Future<void> _open(Announcement announcement) async {
    final session = context.read<SessionState>();
    final schoolId = session.school?.id;

    // Marquée lue à l'ouverture, sans attendre la réponse : l'affichage ne
    // doit pas dépendre du réseau pour un accusé de lecture.
    if (!announcement.isRead && schoolId != null) {
      setState(() => announcement.isRead = true);
      AnnouncementService(session.client)
          .markRead(schoolId, announcement.id)
          .catchError((_) {
        // Sans connexion, l'annonce redeviendra non lue au rechargement :
        // c'est le comportement honnête.
      });
    }

    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => _AnnouncementSheet(announcement: announcement),
    );
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionState>();

    return ScreenScaffold(
      title: 'Annonces',
      floatingActionButton: session.can(Capability.publishAnnouncements)
          ? FloatingActionButton.extended(
              onPressed: () => _openForm(session),
              icon: const Icon(Icons.add),
              label: const Text('Publier'),
            )
          : null,
      child: RefreshIndicator(
        onRefresh: () async {
          setState(() => _future = _load(session));
          await _future;
        },
        child: AsyncView<({List<Announcement> items, int unread, bool canPublish})>(
          future: _future,
          onRetry: () => setState(() => _future = _load(session)),
          emptyCheck: (data) => data.items.isEmpty,
          empty: const EmptyState(
            icon: Icons.campaign_outlined,
            title: 'Aucune annonce',
            message: 'Rien n’a été publié pour vous cette année.',
          ),
          builder: (context, data) => ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 90),
            itemCount: data.items.length,
            separatorBuilder: (_, _) => const SizedBox(height: 10),
            itemBuilder: (context, index) => _AnnouncementCard(
              announcement: data.items[index],
              onTap: () => _open(data.items[index]),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _openForm(SessionState session) async {
    final published = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => const _AnnouncementForm(),
    );
    if (published == true && mounted) {
      setState(() => _future = _load(session));
    }
  }
}

class _AnnouncementCard extends StatelessWidget {
  const _AnnouncementCard({required this.announcement, required this.onTap});

  final Announcement announcement;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = priorityColor(announcement.priority);

    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Pastille de non-lu : le repère le plus rapide dans une
                  // liste, avant même le titre.
                  if (!announcement.isRead)
                    Container(
                      margin: const EdgeInsets.only(top: 5, right: 8),
                      height: 8,
                      width: 8,
                      decoration: const BoxDecoration(
                        color: AppColors.primary,
                        shape: BoxShape.circle,
                      ),
                    ),
                  Expanded(
                    child: Text(
                      announcement.title,
                      style: TextStyle(
                        fontWeight: announcement.isRead
                            ? FontWeight.w600
                            : FontWeight.w700,
                        fontSize: 14.5,
                        color: AppColors.navy,
                      ),
                    ),
                  ),
                  if (announcement.priority != 'normale')
                    StatusPill(
                      label: announcement.priorityLabel,
                      color: color,
                      dense: true,
                    ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                announcement.body,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 13, color: AppColors.slate),
              ),
              const SizedBox(height: 8),
              Text(
                [
                  if (announcement.authorName.isNotEmpty) announcement.authorName,
                  formatDate(announcement.publishedAt),
                  announcement.audienceLabel,
                ].where((part) => part.isNotEmpty).join(' · '),
                style: const TextStyle(fontSize: 11.5, color: AppColors.muted),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AnnouncementSheet extends StatelessWidget {
  const _AnnouncementSheet({required this.announcement});

  final Announcement announcement;

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.6,
      maxChildSize: 0.92,
      builder: (context, controller) => ListView(
        controller: controller,
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
        children: [
          if (announcement.priority != 'normale') ...[
            StatusPill(
              label: announcement.priorityLabel,
              color: priorityColor(announcement.priority),
            ),
            const SizedBox(height: 10),
          ],
          Text(
            announcement.title,
            style: const TextStyle(
              fontSize: 19,
              fontWeight: FontWeight.w700,
              color: AppColors.navy,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            [
              if (announcement.authorName.isNotEmpty)
                '${announcement.authorName}'
                    '${announcement.authorRole.isNotEmpty ? ' — ${announcement.authorRole}' : ''}',
              formatDate(announcement.publishedAt),
            ].where((part) => part.isNotEmpty).join(' · '),
            style: const TextStyle(fontSize: 12, color: AppColors.muted),
          ),
          if (announcement.classNames.isNotEmpty) ...[
            const SizedBox(height: 10),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final name in announcement.classNames)
                  StatusPill(label: name, color: AppColors.info, dense: true),
              ],
            ),
          ],
          const SizedBox(height: 16),
          const Divider(),
          const SizedBox(height: 12),
          Text(
            announcement.body,
            style: const TextStyle(
                fontSize: 14.5, height: 1.55, color: AppColors.slate),
          ),
        ],
      ),
    );
  }
}

/// Publication d'une annonce, réservée à la direction.
class _AnnouncementForm extends StatefulWidget {
  const _AnnouncementForm();

  @override
  State<_AnnouncementForm> createState() => _AnnouncementFormState();
}

class _AnnouncementFormState extends State<_AnnouncementForm> {
  final _formKey = GlobalKey<FormState>();
  final _title = TextEditingController();
  final _body = TextEditingController();
  String _audience = 'tous';
  String _priority = 'normale';
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    _title.dispose();
    _body.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    final session = context.read<SessionState>();
    final schoolId = session.school?.id;
    if (schoolId == null) return;

    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await AnnouncementService(session.client).publish(schoolId, {
        'title': _title.text.trim(),
        'body': _body.text.trim(),
        'audience': _audience,
        'priority': _priority,
      });
      if (mounted) Navigator.of(context).pop(true);
    } on ApiException catch (error) {
      if (mounted) {
        setState(() {
          _error = error.message;
          _saving = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Nouvelle annonce',
                style: TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                  color: AppColors.navy,
                ),
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _title,
                decoration: const InputDecoration(labelText: 'Titre'),
                validator: (value) =>
                    (value ?? '').trim().isEmpty ? 'Saisissez un titre.' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _body,
                maxLines: 5,
                decoration: const InputDecoration(
                  labelText: 'Contenu',
                  alignLabelWithHint: true,
                ),
                validator: (value) => (value ?? '').trim().isEmpty
                    ? 'Saisissez le contenu de l’annonce.'
                    : null,
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: _audience,
                decoration: const InputDecoration(labelText: 'Destinataires'),
                items: const [
                  DropdownMenuItem(
                      value: 'tous', child: Text('Tout l’établissement')),
                  DropdownMenuItem(
                      value: 'personnel', child: Text('Le personnel')),
                ],
                onChanged: (value) =>
                    setState(() => _audience = value ?? 'tous'),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: _priority,
                decoration: const InputDecoration(labelText: 'Priorité'),
                items: const [
                  DropdownMenuItem(value: 'normale', child: Text('Normale')),
                  DropdownMenuItem(
                      value: 'importante', child: Text('Importante')),
                  DropdownMenuItem(value: 'urgente', child: Text('Urgente')),
                ],
                onChanged: (value) =>
                    setState(() => _priority = value ?? 'normale'),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                ErrorBanner(message: _error!),
              ],
              const SizedBox(height: 18),
              FilledButton(
                onPressed: _saving ? null : _submit,
                child: _saving
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                            strokeWidth: 2.2, color: Colors.white),
                      )
                    : const Text('Publier'),
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }
}
