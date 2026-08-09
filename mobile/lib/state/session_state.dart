import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/client.dart';
import '../api/services.dart';
import '../core/roles.dart';
import '../models/session.dart';

/// Phase de démarrage : décide de l'écran affiché avant toute interaction.
enum SessionStatus { loading, signedOut, signedIn }

/// Session de l'utilisateur : jeton, école et année en cours.
///
/// Tout ce qui conditionne un appel API vit ici, parce que le backend attend
/// l'école dans l'URL et l'année dans l'en-tête `X-Academic-Year-ID`.
class SessionState extends ChangeNotifier {
  SessionState({ApiClient? client}) : client = client ?? ApiClient() {
    this.client.onUnauthorized = _onTokenRejected;
    auth = AuthService(this.client);
  }

  final ApiClient client;
  late final AuthService auth;

  static const _tokenKey = 'auth_token';
  static const _userKey = 'auth_user';
  static const _schoolKey = 'active_school';
  static const _yearKey = 'active_year';

  SessionStatus status = SessionStatus.loading;
  String? token;
  AuthUser? user;
  List<SchoolSummary> schools = const [];
  SchoolSummary? school;
  List<AcademicYearSummary> years = const [];
  AcademicYearSummary? year;

  /// Renseigné quand la session s'est fermée toute seule (jeton expiré) :
  /// l'écran de connexion l'affiche au lieu de laisser l'utilisateur perplexe.
  String? notice;

  bool get isSignedIn => status == SessionStatus.signedIn;

  /// Rôle tenu dans l'école sélectionnée.
  ///
  /// C'est le rôle de l'appartenance qui compte, pas le rôle global : la même
  /// personne peut être enseignante ici et censeur ailleurs. Sans école
  /// choisie, on retombe sur le rôle du compte.
  AppRole get role {
    if (school != null && school!.userRole.isNotEmpty) return school!.role;
    return AppRole.fromValue(user?.role);
  }

  Set<Capability> get capabilities =>
      capabilitiesFor(role, isSuperuser: user?.isSuperuser ?? false);

  bool can(Capability capability) => capabilities.contains(capability);

  /// Prête pour les appels qui exigent une année : sans elle, la plupart des
  /// vues répondent « Sélectionnez une année académique ».
  bool get hasContext => school != null && year != null;

  /// Restaure la session enregistrée au lancement.
  Future<void> restore() async {
    final store = await SharedPreferences.getInstance();
    final saved = store.getString(_tokenKey);
    if (saved == null || saved.isEmpty) {
      status = SessionStatus.signedOut;
      notifyListeners();
      return;
    }

    token = saved;
    final rawUser = store.getString(_userKey);
    if (rawUser != null) {
      user = AuthUser.fromJson(jsonDecode(rawUser) as Map<String, dynamic>);
    }
    final rawSchool = store.getString(_schoolKey);
    if (rawSchool != null) {
      school = SchoolSummary.fromJson(jsonDecode(rawSchool) as Map<String, dynamic>);
    }
    final rawYear = store.getString(_yearKey);
    if (rawYear != null) {
      year = AcademicYearSummary.fromJson(jsonDecode(rawYear) as Map<String, dynamic>);
    }
    client.configure(token: token, yearId: year?.id);
    status = SessionStatus.signedIn;
    notifyListeners();

    // Rafraîchit en arrière-plan : la liste des écoles a pu changer, et un
    // jeton révoqué doit fermer la session plutôt que d'échouer écran par écran.
    unawaited(_refreshContext());
  }

  Future<void> signIn(String username, String password) async {
    final data = await auth.login(username, password);
    token = data['token'] as String;
    user = AuthUser.fromJson((data['user'] as Map).cast<String, dynamic>());
    schools = (data['schools'] as List? ?? [])
        .map((item) => SchoolSummary.fromJson((item as Map).cast<String, dynamic>()))
        .toList();
    notice = null;
    client.configure(token: token);

    // Une seule école : la choisir d'office évite un écran de sélection à
    // une ligne, que l'immense majorité des comptes traverserait à chaque fois.
    if (schools.length == 1) {
      await selectSchool(schools.first, persist: false);
    }

    status = SessionStatus.signedIn;
    await _persist();
    notifyListeners();
  }

  Future<void> selectSchool(SchoolSummary next, {bool persist = true}) async {
    school = next;
    year = null;
    years = const [];
    client.configure(token: token);
    notifyListeners();

    try {
      years = await auth.academicYears(next.id);
      // L'année active de l'école est le choix par défaut ; sinon la plus
      // récente, pour ne pas ouvrir l'application sur une année close.
      year = years.where((item) => item.isActive && !item.isClosed).firstOrNull ??
          years.firstOrNull;
    } on ApiException {
      // Un rôle sans accès aux années (parent) n'en a pas besoin pour autant :
      // ses écrans ne dépendent pas de l'en-tête d'année.
      years = const [];
    }
    client.configure(token: token, yearId: year?.id);
    if (persist) await _persist();
    notifyListeners();
  }

  Future<void> selectYear(AcademicYearSummary next) async {
    year = next;
    client.configure(token: token, yearId: next.id);
    await _persist();
    notifyListeners();
  }

  Future<void> signOut({String? because}) async {
    if (token != null) await auth.logout();
    await _clear(notice: because);
  }

  /// Le serveur a refusé le jeton : on ferme la session sans le rappeler au
  /// serveur, qui vient précisément de dire qu'il ne le connaît plus.
  void _onTokenRejected() {
    if (status != SessionStatus.signedIn) return;
    unawaited(_clear(notice: 'Votre session a expiré. Reconnectez-vous.'));
  }

  Future<void> _clear({String? notice}) async {
    final store = await SharedPreferences.getInstance();
    await store.remove(_tokenKey);
    await store.remove(_userKey);
    await store.remove(_schoolKey);
    await store.remove(_yearKey);
    token = null;
    user = null;
    school = null;
    year = null;
    schools = const [];
    years = const [];
    this.notice = notice;
    status = SessionStatus.signedOut;
    client.clear();
    notifyListeners();
  }

  Future<void> _refreshContext() async {
    try {
      schools = await auth.schools();
      // L'école mémorisée peut avoir été retirée à l'utilisateur : on reprend
      // sa version fraîche, qui porte le rôle à jour.
      if (school != null) {
        final current = schools.where((item) => item.id == school!.id).firstOrNull;
        if (current == null) {
          school = null;
          year = null;
        } else {
          school = current;
        }
      }
      if (school != null && year == null) {
        await selectSchool(school!);
      } else {
        await _persist();
      }
      notifyListeners();
    } on ApiException {
      // Hors ligne au lancement : on garde la session mémorisée telle quelle.
    }
  }

  Future<void> _persist() async {
    final store = await SharedPreferences.getInstance();
    if (token != null) await store.setString(_tokenKey, token!);
    if (user != null) await store.setString(_userKey, jsonEncode(user!.toJson()));
    if (school != null) {
      await store.setString(_schoolKey, jsonEncode(school!.toJson()));
    } else {
      await store.remove(_schoolKey);
    }
    if (year != null) {
      await store.setString(_yearKey, jsonEncode(year!.toJson()));
    } else {
      await store.remove(_yearKey);
    }
  }

  @override
  void dispose() {
    client.dispose();
    super.dispose();
  }
}
