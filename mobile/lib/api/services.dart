import '../models/finance.dart';
import '../models/school_data.dart';
import '../models/session.dart';
import 'client.dart';

List<Map<String, dynamic>> _rows(dynamic data, [String? key]) {
  final list = key == null
      ? data
      : (data is Map ? data[key] : null);
  if (list is! List) return const [];
  return list.cast<Map<String, dynamic>>();
}

/// Authentification et contexte de session.
class AuthService {
  AuthService(this._client);

  final ApiClient _client;

  Future<Map<String, dynamic>> login(String username, String password) async {
    final data = await _client.post('/auth/login/', body: {
      'username': username.trim(),
      'password': password,
    });
    return (data as Map).cast<String, dynamic>();
  }

  Future<void> logout() async {
    // Un échec ici ne doit pas retenir l'utilisateur : la session locale sera
    // effacée de toute façon.
    try {
      await _client.post('/auth/logout/');
    } on ApiException {
      return;
    }
  }

  Future<List<SchoolSummary>> schools() async {
    final data = await _client.get('/schools/');
    return _rows(data is Map ? data['results'] : data)
        .map(SchoolSummary.fromJson)
        .toList();
  }

  Future<List<AcademicYearSummary>> academicYears(int schoolId) async {
    final data = await _client.get('/schools/$schoolId/academic-years/');
    return _rows(data is Map ? data['results'] : data)
        .map(AcademicYearSummary.fromJson)
        .toList();
  }
}

/// Emploi du temps, personnel ou général.
class TimetableService {
  TimetableService(this._client);

  final ApiClient _client;

  /// `mine` pour ses propres cours, `all` pour la vue générale. Le serveur
  /// retombe sur `mine` si l'utilisateur n'a pas le droit de tout voir.
  Future<List<TimetableSlot>> slots(int schoolId, {bool all = false}) async {
    final data = await _client.get(
      '/schools/$schoolId/timetable/mine/',
      query: all ? {'scope': 'all'} : null,
    );
    return _rows(data, 'slots').map(TimetableSlot.fromJson).toList();
  }
}

/// Notes : contextes, feuille de notes et saisie.
class GradeService {
  GradeService(this._client);

  final ApiClient _client;

  Future<List<GradeSession>> contexts(int schoolId) async {
    final data = await _client.get('/schools/$schoolId/grades/contexts/');
    return _rows(data, 'sessions').map(GradeSession.fromJson).toList();
  }

  Future<GradeSheet> sheet(int schoolId, int sessionId, int classSubjectId) async {
    final data = await _client.get(
      '/schools/$schoolId/grades/sessions/$sessionId/subjects/$classSubjectId/',
    );
    return GradeSheet.fromJson((data as Map).cast<String, dynamic>());
  }

  /// Enregistre les notes saisies. Une note vide est omise plutôt qu'envoyée
  /// à zéro — l'absence de note et un zéro ne veulent pas dire la même chose.
  Future<GradeSheet> save(
    int schoolId,
    int sessionId,
    int classSubjectId,
    List<Map<String, dynamic>> grades,
  ) async {
    final data = await _client.post(
      '/schools/$schoolId/grades/sessions/$sessionId/subjects/$classSubjectId/',
      body: {'grades': grades},
    );
    return GradeSheet.fromJson((data as Map).cast<String, dynamic>());
  }
}

/// Appel et assiduité.
class AttendanceService {
  AttendanceService(this._client);

  final ApiClient _client;

  Future<AttendanceSheet> sheet(
    int schoolId,
    int classId, {
    String? takenOn,
    String? period,
  }) async {
    final data = await _client.get(
      '/schools/$schoolId/attendance/sheet/',
      query: {
        'school_class': classId,
        'taken_on': ?takenOn,
        if (period != null && period.isNotEmpty) 'period': period,
      },
    );
    return AttendanceSheet.fromJson((data as Map).cast<String, dynamic>());
  }

  Future<void> save(
    int schoolId, {
    required int classId,
    required List<AttendanceRow> rows,
    String? takenOn,
    String period = '',
    String note = '',
  }) async {
    await _client.post('/schools/$schoolId/attendance/sessions/', body: {
      'school_class': classId,
      'taken_on': ?takenOn,
      'period': period,
      'note': note,
      'records': rows.map((row) => row.toPayload()).toList(),
    });
  }

  /// Appels déjà enregistrés, les plus récents d'abord.
  Future<List<Map<String, dynamic>>> history(int schoolId, {int? classId}) async {
    final data = await _client.get(
      '/schools/$schoolId/attendance/sessions/',
      query: {'school_class': ?classId},
    );
    return _rows(data, 'sessions');
  }
}

/// Discipline : retards, absences et incidents.
class DisciplineService {
  DisciplineService(this._client);

  final ApiClient _client;

  Future<({List<StudentRow> students, List<DisciplineRecord> records, Map<String, dynamic> summary})>
      load(int schoolId, {int? enrollmentId}) async {
    final data = await _client.get(
      '/schools/$schoolId/discipline/records/',
      query: {'enrollment': ?enrollmentId},
    );
    final map = (data as Map).cast<String, dynamic>();
    return (
      students: _rows(map['students']).map(StudentRow.fromJson).toList(),
      records: _rows(map['records']).map(DisciplineRecord.fromJson).toList(),
      summary: (map['summary'] as Map? ?? {}).cast<String, dynamic>(),
    );
  }

  Future<void> record(int schoolId, Map<String, dynamic> payload) =>
      _client.post('/schools/$schoolId/discipline/records/', body: payload);
}

/// Écolage, encaissements et dépenses.
class FinanceService {
  FinanceService(this._client);

  final ApiClient _client;

  Future<List<FeePlanSummary>> plans(int schoolId) async {
    final data = await _client.get('/schools/$schoolId/finance/tuition-plans/');
    return _rows(data is Map ? data['results'] : data)
        .map(FeePlanSummary.fromJson)
        .toList();
  }

  Future<List<FeePayment>> payments(int schoolId, {int? enrollmentId}) async {
    final data = await _client.get(
      '/schools/$schoolId/finance/payments/',
      query: {'enrollment': ?enrollmentId},
    );
    return _rows(data is Map ? data['results'] : data)
        .map(FeePayment.fromJson)
        .toList();
  }

  Future<ComplianceReport> compliance(
    int schoolId,
    int classId,
    String target,
  ) async {
    final data = await _client.get(
      '/schools/$schoolId/finance/compliance/',
      query: {'class_id': classId, 'target': target},
    );
    return ComplianceReport.fromJson((data as Map).cast<String, dynamic>());
  }

  Future<List<SchoolExpense>> expenses(int schoolId) async {
    final data = await _client.get('/schools/$schoolId/finance/expenses/');
    return _rows(data is Map ? data['results'] : data)
        .map(SchoolExpense.fromJson)
        .toList();
  }

  Future<List<LabeledValue>> expenseCategories(int schoolId) async {
    final data = await _client.get('/schools/$schoolId/finance/expense-categories/');
    return _rows(data is Map ? data['results'] : data)
        .map((row) => LabeledValue(
              value: '${row['id']}',
              label: asText(row['name']),
            ))
        .toList();
  }

  Future<void> createExpense(int schoolId, Map<String, dynamic> payload) =>
      _client.post('/schools/$schoolId/finance/expenses/', body: payload);

  Future<void> createPayment(int schoolId, Map<String, dynamic> payload) =>
      _client.post('/schools/$schoolId/finance/payments/', body: payload);
}

/// Classes, élèves et enseignants.
class DirectoryService {
  DirectoryService(this._client);

  final ApiClient _client;

  Future<List<Map<String, dynamic>>> classes(int schoolId) async {
    final data = await _client.get('/schools/$schoolId/classes/');
    return _rows(data is Map ? data['results'] : data);
  }

  Future<List<Map<String, dynamic>>> enrollments(int schoolId, {int? classId}) async {
    final data = await _client.get(
      '/schools/$schoolId/enrollments/',
      query: {'school_class': ?classId},
    );
    return _rows(data is Map ? data['results'] : data);
  }

  Future<List<Map<String, dynamic>>> teachers(int schoolId) async {
    final data = await _client.get('/schools/$schoolId/teachers/');
    return _rows(data is Map ? data['results'] : data);
  }
}

/// Bulletins.
class ReportCardService {
  ReportCardService(this._client);

  final ApiClient _client;

  Future<Map<String, dynamic>> cards(
    int schoolId,
    int sessionId,
    int classId,
  ) async {
    final data = await _client.get(
      '/schools/$schoolId/report-cards/sessions/$sessionId/classes/$classId/',
    );
    return (data as Map).cast<String, dynamic>();
  }

  Future<Map<String, dynamic>> status(int schoolId, int sessionId) async {
    final data = await _client.get(
      '/schools/$schoolId/report-cards/sessions/$sessionId/generate/',
    );
    return (data as Map).cast<String, dynamic>();
  }

  Future<void> generate(
    int schoolId,
    int sessionId,
    Map<String, dynamic> payload,
  ) =>
      _client.post(
        '/schools/$schoolId/report-cards/sessions/$sessionId/generate/',
        body: payload,
      );
}
