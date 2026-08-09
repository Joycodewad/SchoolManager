import 'session.dart';

/// Annonce de l'établissement.
class Announcement {
  Announcement({
    required this.id,
    required this.title,
    required this.body,
    required this.audienceLabel,
    required this.priority,
    required this.priorityLabel,
    required this.publishedAt,
    required this.isRead,
    this.authorName = '',
    this.authorRole = '',
    this.classNames = const [],
  });

  factory Announcement.fromJson(Map<String, dynamic> json) => Announcement(
        id: asInt(json['id']) ?? 0,
        title: asText(json['title']),
        body: asText(json['body']),
        audienceLabel: asText(json['audience_label']),
        priority: asText(json['priority']),
        priorityLabel: asText(json['priority_label']),
        publishedAt: asText(json['published_at']),
        isRead: json['is_read'] == true,
        authorName: asText(json['author_name']),
        authorRole: asText(json['author_role']),
        classNames: (json['class_names'] as List? ?? [])
            .map((item) => '$item')
            .toList(),
      );

  final int id;
  final String title;
  final String body;
  final String audienceLabel;
  final String priority;
  final String priorityLabel;
  final String publishedAt;
  final String authorName;
  final String authorRole;
  final List<String> classNames;
  bool isRead;
}

/// Fil de discussion, tel que la liste le présente.
class Conversation {
  Conversation({
    required this.id,
    required this.subject,
    required this.participants,
    required this.unreadCount,
    required this.lastMessageAt,
    this.lastMessage,
    this.lastSender = '',
  });

  factory Conversation.fromJson(Map<String, dynamic> json) {
    final last = json['last_message'] as Map<String, dynamic>?;
    return Conversation(
      id: asInt(json['id']) ?? 0,
      subject: asText(json['subject']),
      participants: (json['participants_detail'] as List? ?? [])
          .map((item) => Correspondent.fromJson(item as Map<String, dynamic>))
          .toList(),
      unreadCount: asInt(json['unread_count']) ?? 0,
      lastMessageAt: asText(json['last_message_at']),
      lastMessage: last == null ? null : asText(last['body']),
      lastSender: last == null ? '' : asText(last['sender_name']),
    );
  }

  final int id;
  final String subject;
  final List<Correspondent> participants;
  final int unreadCount;
  final String lastMessageAt;
  final String? lastMessage;
  final String lastSender;

  /// Nom du fil : son objet, sinon les correspondants.
  String get title {
    if (subject.isNotEmpty) return subject;
    if (participants.isEmpty) return 'Conversation';
    return participants.map((person) => person.name).join(', ');
  }
}

/// Personne joignable par message.
class Correspondent {
  Correspondent({required this.id, required this.name, required this.role});

  factory Correspondent.fromJson(Map<String, dynamic> json) => Correspondent(
        id: asInt(json['id']) ?? 0,
        name: asText(json['name']),
        role: asText(json['role']),
      );

  final int id;
  final String name;
  final String role;
}

/// Famille d'une pièce jointe, telle que le serveur la classe.
enum AttachmentKind { image, video, audio, document }

AttachmentKind attachmentKindFrom(String value) => switch (value) {
      'image' => AttachmentKind.image,
      'video' => AttachmentKind.video,
      'audio' => AttachmentKind.audio,
      _ => AttachmentKind.document,
    };

/// Fichier joint à un message.
class Attachment {
  Attachment({
    required this.id,
    required this.url,
    required this.kind,
    required this.name,
    required this.size,
    this.durationSeconds,
  });

  factory Attachment.fromJson(Map<String, dynamic> json) => Attachment(
        id: asInt(json['id']) ?? 0,
        url: asText(json['url']),
        kind: attachmentKindFrom(asText(json['kind'])),
        name: asText(json['original_name']),
        size: asInt(json['size']) ?? 0,
        durationSeconds: asInt(json['duration_seconds']),
      );

  final int id;
  final String url;
  final AttachmentKind kind;
  final String name;
  final int size;
  final int? durationSeconds;

  /// Taille lisible : « 240 Ko », « 1,8 Mo ».
  String get readableSize {
    if (size < 1024) return '$size o';
    if (size < 1024 * 1024) return '${(size / 1024).round()} Ko';
    return '${(size / (1024 * 1024)).toStringAsFixed(1).replaceAll('.', ',')} Mo';
  }

  /// Durée « 0:27 », pour les vocaux et les vidéos.
  String get readableDuration {
    final seconds = durationSeconds;
    if (seconds == null || seconds <= 0) return '';
    final minutes = seconds ~/ 60;
    return '$minutes:${(seconds % 60).toString().padLeft(2, '0')}';
  }
}

/// Message d'un fil.
class ChatMessage {
  ChatMessage({
    required this.id,
    required this.body,
    required this.sentAt,
    required this.senderId,
    required this.senderName,
    this.attachments = const [],
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) => ChatMessage(
        id: asInt(json['id']) ?? 0,
        body: asText(json['body']),
        sentAt: asText(json['sent_at']),
        senderId: asInt(json['sender_id']) ?? 0,
        senderName: asText(json['sender_name']),
        attachments: (json['attachments'] as List? ?? [])
            .map((item) => Attachment.fromJson(item as Map<String, dynamic>))
            .toList(),
      );

  final int id;
  final String body;
  final String sentAt;
  final int senderId;
  final String senderName;
  final List<Attachment> attachments;
}

/// Contenu d'un fil ouvert.
class ConversationThread {
  ConversationThread({
    required this.id,
    required this.subject,
    required this.participants,
    required this.messages,
  });

  factory ConversationThread.fromJson(Map<String, dynamic> json) =>
      ConversationThread(
        id: asInt(json['id']) ?? 0,
        subject: asText(json['subject']),
        participants: (json['participants'] as List? ?? [])
            .map((item) => Correspondent.fromJson(item as Map<String, dynamic>))
            .toList(),
        messages: (json['messages'] as List? ?? [])
            .map((item) => ChatMessage.fromJson(item as Map<String, dynamic>))
            .toList(),
      );

  final int id;
  final String subject;
  final List<Correspondent> participants;
  final List<ChatMessage> messages;
}
