import 'session.dart';

/// Créneau d'emploi du temps.
class TimetableSlot {
  TimetableSlot({
    required this.id,
    required this.className,
    required this.subject,
    required this.day,
    required this.dayLabel,
    required this.startTime,
    required this.endTime,
    this.teacher,
    this.level = '',
  });

  factory TimetableSlot.fromJson(Map<String, dynamic> json) => TimetableSlot(
        id: asInt(json['id']) ?? 0,
        className: asText(json['class_name']),
        subject: asText(json['subject']),
        day: asInt(json['day']) ?? 0,
        dayLabel: asText(json['day_label']),
        startTime: asText(json['start_time']),
        endTime: asText(json['end_time']),
        teacher: json['teacher'] as String?,
        level: asText(json['level']),
      );

  final int id;
  final String className;
  final String subject;
  final int day;
  final String dayLabel;
  final String startTime;
  final String endTime;
  final String? teacher;
  final String level;

  /// « 08:00 » plutôt que « 08:00:00 » : l'API renvoie des secondes inutiles.
  String get shortStart => startTime.length >= 5 ? startTime.substring(0, 5) : startTime;
  String get shortEnd => endTime.length >= 5 ? endTime.substring(0, 5) : endTime;
}

/// Élève inscrit, tel que les listes le présentent.
class StudentRow {
  StudentRow({
    required this.enrollmentId,
    required this.enrollmentNumber,
    required this.studentName,
    this.className = '',
    this.levelName = '',
  });

  factory StudentRow.fromJson(Map<String, dynamic> json) => StudentRow(
        // Les vues nomment cette clé tantôt `id`, tantôt `enrollment` :
        // discipline et appel ne suivent pas la même convention.
        enrollmentId: asInt(json['enrollment'] ?? json['id']) ?? 0,
        enrollmentNumber: asText(json['enrollment_number']),
        studentName: asText(json['student_name']),
        className: asText(json['class_name']),
        levelName: asText(json['level_name']),
      );

  final int enrollmentId;
  final String enrollmentNumber;
  final String studentName;
  final String className;
  final String levelName;
}

/// Session académique (trimestre ou semestre) et ses classes.
class GradeSession {
  GradeSession({
    required this.id,
    required this.name,
    required this.label,
    required this.classes,
  });

  factory GradeSession.fromJson(Map<String, dynamic> json) => GradeSession(
        id: asInt(json['id']) ?? 0,
        name: asText(json['name']),
        label: asText(json['label']),
        classes: (json['classes'] as List? ?? [])
            .map((item) => GradeClass.fromJson(item as Map<String, dynamic>))
            .toList(),
      );

  final int id;
  final String name;
  final String label;
  final List<GradeClass> classes;
}

class GradeClass {
  GradeClass({required this.id, required this.name, required this.subjects});

  factory GradeClass.fromJson(Map<String, dynamic> json) => GradeClass(
        id: asInt(json['id']) ?? 0,
        name: asText(json['name']),
        subjects: (json['subjects'] as List? ?? [])
            .map((item) => GradeSubject.fromJson(item as Map<String, dynamic>))
            .toList(),
      );

  final int id;
  final String name;
  final List<GradeSubject> subjects;
}

class GradeSubject {
  GradeSubject({required this.id, required this.name});

  factory GradeSubject.fromJson(Map<String, dynamic> json) => GradeSubject(
        id: asInt(json['id']) ?? 0,
        name: asText(json['name']),
      );

  final int id;
  final String name;
}

/// Ligne du barème : une colonne de la feuille de notes.
class GradeLine {
  GradeLine({
    required this.id,
    required this.name,
    required this.maxScore,
  });

  factory GradeLine.fromJson(Map<String, dynamic> json) => GradeLine(
        id: asInt(json['id']) ?? 0,
        name: asText(json['name']),
        maxScore: asDouble(json['max_score']) ?? 20,
      );

  final int id;
  final String name;
  final double maxScore;
}

/// Feuille de notes d'une matière : le barème et une ligne par élève.
class GradeSheet {
  GradeSheet({
    required this.lines,
    required this.students,
    required this.subjectName,
  });

  factory GradeSheet.fromJson(Map<String, dynamic> json) {
    final scheme = json['scheme'] as Map<String, dynamic>? ?? {};
    final subject = json['class_subject'] as Map<String, dynamic>? ?? {};
    return GradeSheet(
      lines: (scheme['lines'] as List? ?? [])
          .map((item) => GradeLine.fromJson(item as Map<String, dynamic>))
          .toList(),
      students: (json['students'] as List? ?? [])
          .map((item) => GradeSheetRow.fromJson(item as Map<String, dynamic>))
          .toList(),
      subjectName: asText(subject['subject']),
    );
  }

  final List<GradeLine> lines;
  final List<GradeSheetRow> students;
  final String subjectName;
}

class GradeSheetRow {
  GradeSheetRow({
    required this.enrollment,
    required this.matricule,
    required this.studentName,
    required this.scores,
    this.average,
  });

  factory GradeSheetRow.fromJson(Map<String, dynamic> json) => GradeSheetRow(
        enrollment: asInt(json['enrollment']) ?? 0,
        matricule: asText(json['matricule']),
        studentName: asText(json['student_name']),
        // Les clés du dictionnaire de notes sont les identifiants de ligne,
        // sérialisés en chaînes par Django.
        scores: (json['scores'] as Map? ?? {}).map(
          (key, value) => MapEntry('$key', asText(value)),
        ),
        average: json['average'] as String?,
      );

  final int enrollment;
  final String matricule;
  final String studentName;
  final Map<String, String> scores;
  final String? average;
}

/// Entrée de discipline.
class DisciplineRecord {
  DisciplineRecord({
    required this.id,
    required this.studentName,
    required this.entryType,
    required this.entryTypeLabel,
    required this.occurredOn,
    required this.lateHours,
    required this.incidentType,
    required this.severityLabel,
    required this.description,
    this.className,
  });

  factory DisciplineRecord.fromJson(Map<String, dynamic> json) =>
      DisciplineRecord(
        id: asInt(json['id']) ?? 0,
        studentName: asText(json['student_name']),
        entryType: asText(json['entry_type']),
        entryTypeLabel: asText(json['entry_type_label']),
        occurredOn: asText(json['occurred_on']),
        lateHours: asText(json['late_hours']),
        incidentType: asText(json['incident_type']),
        severityLabel: asText(json['severity_label']),
        description: asText(json['description']),
        className: json['class_name'] as String?,
      );

  final int id;
  final String studentName;
  final String entryType;
  final String entryTypeLabel;
  final String occurredOn;
  final String lateHours;
  final String incidentType;
  final String severityLabel;
  final String description;
  final String? className;
}

/// Ligne de la feuille d'appel.
class AttendanceRow {
  AttendanceRow({
    required this.enrollment,
    required this.enrollmentNumber,
    required this.studentName,
    required this.status,
    required this.minutesLate,
    required this.comment,
  });

  factory AttendanceRow.fromJson(Map<String, dynamic> json) => AttendanceRow(
        enrollment: asInt(json['enrollment']) ?? 0,
        enrollmentNumber: asText(json['enrollment_number']),
        studentName: asText(json['student_name']),
        status: asText(json['status']),
        minutesLate: asInt(json['minutes_late']) ?? 0,
        comment: asText(json['comment']),
      );

  final int enrollment;
  final String enrollmentNumber;
  final String studentName;
  String status;
  int minutesLate;
  String comment;

  Map<String, dynamic> toPayload() => {
        'enrollment': enrollment,
        'status': status,
        'minutes_late': minutesLate,
        'comment': comment,
      };
}

/// Feuille d'appel d'une classe pour une date.
class AttendanceSheet {
  AttendanceSheet({
    required this.className,
    required this.takenOn,
    required this.isTaken,
    required this.students,
    required this.statuses,
  });

  factory AttendanceSheet.fromJson(Map<String, dynamic> json) {
    final klass = json['school_class'] as Map<String, dynamic>? ?? {};
    return AttendanceSheet(
      className: asText(klass['name']),
      takenOn: asText(json['taken_on']),
      isTaken: json['is_taken'] == true,
      students: (json['students'] as List? ?? [])
          .map((item) => AttendanceRow.fromJson(item as Map<String, dynamic>))
          .toList(),
      statuses: (json['statuses'] as List? ?? [])
          .map((item) => LabeledValue.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }

  final String className;
  final String takenOn;
  final bool isTaken;
  final List<AttendanceRow> students;
  final List<LabeledValue> statuses;
}

/// Couple valeur/libellé, tel que les vues les renvoient pour les listes
/// déroulantes (statuts, méthodes de paiement, types d'entrée…).
class LabeledValue {
  LabeledValue({required this.value, required this.label});

  factory LabeledValue.fromJson(Map<String, dynamic> json) => LabeledValue(
        value: asText(json['value']),
        label: asText(json['label']),
      );

  final String value;
  final String label;
}
