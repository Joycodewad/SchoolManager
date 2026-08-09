import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../api/client.dart';
import '../../api/services.dart';
import '../../core/theme.dart';
import '../../models/communication.dart';
import '../../state/session_state.dart';
import '../../widgets/common.dart';
import '../../widgets/attachments.dart';
import '../../widgets/message_composer.dart';
import '../../widgets/screen_scaffold.dart';

/// Heure d'un message : l'heure seule aujourd'hui, la date au-delà.
String messageStamp(String iso) {
  final parsed = DateTime.tryParse(iso)?.toLocal();
  if (parsed == null) return '';
  final now = DateTime.now();
  final sameDay = parsed.year == now.year &&
      parsed.month == now.month &&
      parsed.day == now.day;
  return sameDay
      ? DateFormat('HH:mm').format(parsed)
      : DateFormat('d MMM', 'fr_FR').format(parsed);
}

/// Messagerie : liste des fils, puis conversation.
class MessagesScreen extends StatefulWidget {
  const MessagesScreen({super.key});

  @override
  State<MessagesScreen> createState() => _MessagesScreenState();
}

class _MessagesScreenState extends State<MessagesScreen> {
  Future<({List<Conversation> items, int unread})>? _future;
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

  Future<({List<Conversation> items, int unread})> _load(SessionState session) {
    final schoolId = session.school?.id;
    if (schoolId == null) {
      return Future.value((items: <Conversation>[], unread: 0));
    }
    return MessageService(session.client).conversations(schoolId);
  }

  void _reload() {
    final session = context.read<SessionState>();
    setState(() => _future = _load(session));
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionState>();

    return ScreenScaffold(
      title: 'Messages',
      // La messagerie ne dépend pas de l'année : les fils traversent l'année
      // scolaire, et un parent n'a de toute façon pas d'année sélectionnée.
      requiresYear: false,
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _compose,
        icon: const Icon(Icons.edit_outlined),
        label: const Text('Écrire'),
      ),
      child: RefreshIndicator(
        onRefresh: () async {
          _reload();
          await _future;
        },
        child: AsyncView<({List<Conversation> items, int unread})>(
          future: _future,
          onRetry: _reload,
          emptyCheck: (data) => data.items.isEmpty,
          empty: const EmptyState(
            icon: Icons.forum_outlined,
            title: 'Aucun message',
            message: 'Vos conversations apparaîtront ici.',
          ),
          builder: (context, data) => ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 90),
            itemCount: data.items.length,
            separatorBuilder: (_, _) => const SizedBox(height: 8),
            itemBuilder: (context, index) => _ConversationCard(
              conversation: data.items[index],
              onTap: () => _openThread(data.items[index], session),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _openThread(
      Conversation conversation, SessionState session) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => ThreadScreen(
          conversationId: conversation.id,
          title: conversation.title,
        ),
      ),
    );
    // Le fil a marqué ses messages comme lus : la liste doit s'en apercevoir.
    if (mounted) _reload();
  }

  Future<void> _compose() async {
    final sent = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(builder: (_) => const _ComposeScreen()),
    );
    if (sent == true && mounted) _reload();
  }
}

class _ConversationCard extends StatelessWidget {
  const _ConversationCard({required this.conversation, required this.onTap});

  final Conversation conversation;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final unread = conversation.unreadCount > 0;
    final people = conversation.participants;

    return Card(
      child: ListTile(
        onTap: onTap,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        leading: CircleAvatar(
          backgroundColor: unread ? AppColors.primary : AppColors.tint,
          child: Text(
            people.isEmpty ? '?' : people.first.name.characters.first.toUpperCase(),
            style: TextStyle(
              color: unread ? Colors.white : AppColors.primaryDark,
              fontWeight: FontWeight.w700,
              fontSize: 15,
            ),
          ),
        ),
        title: Row(
          children: [
            Expanded(
              child: Text(
                conversation.title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontWeight: unread ? FontWeight.w700 : FontWeight.w600,
                  fontSize: 14.5,
                  color: AppColors.navy,
                ),
              ),
            ),
            Text(
              messageStamp(conversation.lastMessageAt),
              style: const TextStyle(fontSize: 11, color: AppColors.muted),
            ),
          ],
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 3),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  conversation.lastMessage ?? 'Aucun message',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 12.5,
                    color: unread ? AppColors.slate : AppColors.muted,
                    fontWeight: unread ? FontWeight.w600 : FontWeight.w400,
                  ),
                ),
              ),
              if (unread) ...[
                const SizedBox(width: 8),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    '${conversation.unreadCount}',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 10.5,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Un fil ouvert : ses messages et le champ de réponse.
class ThreadScreen extends StatefulWidget {
  const ThreadScreen({
    super.key,
    required this.conversationId,
    required this.title,
  });

  final int conversationId;
  final String title;

  @override
  State<ThreadScreen> createState() => _ThreadScreenState();
}

class _ThreadScreenState extends State<ThreadScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();
  ConversationThread? _thread;
  bool _loading = true;
  bool _sending = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final session = context.read<SessionState>();
    final schoolId = session.school?.id;
    if (schoolId == null) return;
    try {
      final thread = await MessageService(session.client)
          .thread(schoolId, widget.conversationId);
      if (!mounted) return;
      setState(() {
        _thread = thread;
        _loading = false;
      });
      _scrollToEnd();
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _loading = false;
      });
    }
  }

  /// Le dernier message doit être visible à l'ouverture, comme dans toute
  /// messagerie : la liste s'affiche du plus ancien au plus récent.
  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      _scroll.jumpTo(_scroll.position.maxScrollExtent);
    });
  }

  Future<void> _send(String body, List<PendingAttachment> files) async {
    if (body.isEmpty && files.isEmpty) return;
    final session = context.read<SessionState>();
    final schoolId = session.school?.id;
    if (schoolId == null) return;

    setState(() {
      _sending = true;
      _error = null;
    });
    try {
      await MessageService(session.client).reply(
        schoolId,
        widget.conversationId,
        body,
        files: files.map((item) => item.toUpload()).toList(),
        // La durée n'accompagne qu'un vocal envoyé seul : au-delà, le serveur
        // ne saurait pas à quelle pièce jointe la rattacher.
        durationSeconds: files.length == 1 && files.first.isAudio
            ? files.first.durationSeconds
            : null,
      );
      _input.clear();
      await _load();
      if (mounted) setState(() => _sending = false);
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _sending = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionState>();
    final me = session.user?.id ?? 0;
    final thread = _thread;

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.title, maxLines: 1, overflow: TextOverflow.ellipsis),
            if (thread != null && thread.participants.length > 1)
              Text(
                thread.participants
                    .where((person) => person.id != me)
                    .map((person) => person.role)
                    .join(' · '),
                style: const TextStyle(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w500,
                  color: AppColors.muted,
                ),
              ),
          ],
        ),
      ),
      body: Column(
        children: [
          if (_error != null)
            Padding(
              padding: const EdgeInsets.all(12),
              child: ErrorBanner(message: _error!, onRetry: _load),
            ),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : thread == null
                    ? const SizedBox.shrink()
                    : thread.messages.isEmpty
                        ? const EmptyState(
                            icon: Icons.chat_bubble_outline,
                            title: 'Aucun message',
                            message: 'Écrivez le premier message de ce fil.',
                          )
                        : ListView.builder(
                            controller: _scroll,
                            padding: const EdgeInsets.all(16),
                            itemCount: thread.messages.length,
                            itemBuilder: (context, index) => _Bubble(
                              message: thread.messages[index],
                              isMine: thread.messages[index].senderId == me,
                              // Le nom n'est utile qu'en discussion à
                              // plusieurs, et seulement au changement d'auteur.
                              showSender: thread.participants.length > 2 &&
                                  (index == 0 ||
                                      thread.messages[index - 1].senderId !=
                                          thread.messages[index].senderId),
                            ),
                          ),
          ),
          MessageComposer(
            controller: _input,
            sending: _sending,
            onSend: _send,
          ),
        ],
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({
    required this.message,
    required this.isMine,
    required this.showSender,
  });

  final ChatMessage message;
  final bool isMine;
  final bool showSender;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment:
            isMine ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          if (showSender && !isMine)
            Padding(
              padding: const EdgeInsets.only(left: 6, bottom: 3),
              child: Text(
                message.senderName,
                style: const TextStyle(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w600,
                  color: AppColors.muted,
                ),
              ),
            ),
          Container(
            constraints: BoxConstraints(
              maxWidth: MediaQuery.of(context).size.width * 0.76,
            ),
            padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 9),
            decoration: BoxDecoration(
              color: isMine ? AppColors.primary : Colors.white,
              border: isMine ? null : Border.all(color: AppColors.border),
              borderRadius: BorderRadius.only(
                topLeft: const Radius.circular(14),
                topRight: const Radius.circular(14),
                bottomLeft: Radius.circular(isMine ? 14 : 4),
                bottomRight: Radius.circular(isMine ? 4 : 14),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Les pièces jointes viennent avant le texte : c'est le
                // contenu principal quand elles sont là, la légende suit.
                for (final attachment in message.attachments)
                  Padding(
                    padding: EdgeInsets.only(
                      bottom: message.body.isEmpty &&
                              attachment == message.attachments.last
                          ? 3
                          : 6,
                    ),
                    child: AttachmentView(
                      attachment: attachment,
                      isMine: isMine,
                    ),
                  ),
                if (message.body.isNotEmpty)
                  Text(
                    message.body,
                    style: TextStyle(
                      fontSize: 14,
                      height: 1.4,
                      color: isMine ? Colors.white : AppColors.slate,
                    ),
                  ),
                const SizedBox(height: 3),
                Text(
                  messageStamp(message.sentAt),
                  style: TextStyle(
                    fontSize: 10,
                    color: isMine ? Colors.white70 : AppColors.muted,
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

/// Nouveau fil : choix des destinataires puis premier message.
class _ComposeScreen extends StatefulWidget {
  const _ComposeScreen();

  @override
  State<_ComposeScreen> createState() => _ComposeScreenState();
}

class _ComposeScreenState extends State<_ComposeScreen> {
  Future<List<Correspondent>>? _recipients;
  final _search = TextEditingController();
  final _subject = TextEditingController();
  final _body = TextEditingController();
  final Set<int> _selected = {};
  bool _sending = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final session = context.read<SessionState>();
    final schoolId = session.school?.id;
    if (schoolId != null) {
      _recipients = MessageService(session.client).recipients(schoolId);
    }
  }

  @override
  void dispose() {
    _search.dispose();
    _subject.dispose();
    _body.dispose();
    super.dispose();
  }

  Future<void> _send(String body, List<PendingAttachment> files) async {
    if (_selected.isEmpty) {
      setState(() => _error = 'Choisissez au moins un destinataire.');
      return;
    }
    if (body.isEmpty && files.isEmpty) {
      setState(() => _error = 'Écrivez votre message ou joignez un fichier.');
      return;
    }
    final session = context.read<SessionState>();
    final schoolId = session.school?.id;
    if (schoolId == null) return;

    setState(() {
      _sending = true;
      _error = null;
    });
    try {
      await MessageService(session.client).start(
        schoolId,
        participants: _selected.toList(),
        body: body,
        subject: _subject.text.trim(),
        files: files.map((item) => item.toUpload()).toList(),
      );
      if (mounted) Navigator.of(context).pop(true);
    } on ApiException catch (error) {
      if (mounted) {
        setState(() {
          _error = error.message;
          _sending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final query = _search.text.trim().toLowerCase();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Nouveau message'),
        actions: const [],
      ),
      body: AsyncView<List<Correspondent>>(
        future: _recipients,
        builder: (context, people) {
          final filtered = query.isEmpty
              ? people
              : people
                  .where((person) =>
                      person.name.toLowerCase().contains(query) ||
                      person.role.toLowerCase().contains(query))
                  .toList();

          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 6),
                child: TextField(
                  controller: _search,
                  onChanged: (_) => setState(() {}),
                  decoration: const InputDecoration(
                    hintText: 'Rechercher un destinataire',
                    prefixIcon: Icon(Icons.search, size: 20),
                    isDense: true,
                  ),
                ),
              ),
              if (_selected.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      '${_selected.length} destinataire'
                      '${_selected.length > 1 ? 's' : ''}',
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.primary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
              Expanded(
                child: filtered.isEmpty
                    ? const EmptyState(
                        icon: Icons.person_search_outlined,
                        title: 'Aucun destinataire',
                        message: 'Personne ne correspond à cette recherche.',
                      )
                    : ListView.builder(
                        itemCount: filtered.length,
                        itemBuilder: (context, index) {
                          final person = filtered[index];
                          return CheckboxListTile(
                            dense: true,
                            value: _selected.contains(person.id),
                            title: Text(person.name,
                                style: const TextStyle(fontSize: 14)),
                            subtitle: Text(person.role,
                                style: const TextStyle(fontSize: 12)),
                            onChanged: (checked) => setState(() {
                              if (checked == true) {
                                _selected.add(person.id);
                              } else {
                                _selected.remove(person.id);
                              }
                            }),
                          );
                        },
                      ),
              ),
              const Divider(height: 1),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
                child: Column(
                  children: [
                    TextField(
                      controller: _subject,
                      decoration: const InputDecoration(
                        labelText: 'Objet (facultatif)',
                        isDense: true,
                      ),
                    ),
                    if (_error != null) ...[
                      const SizedBox(height: 10),
                      ErrorBanner(message: _error!),
                    ],
                  ],
                ),
              ),
              // Même barre que dans un fil : pièces jointes et vocal compris.
              MessageComposer(
                controller: _body,
                sending: _sending,
                onSend: _send,
              ),
            ],
          );
        },
      ),
    );
  }
}
