/// Rôles et capacités : qui voit quoi.
///
/// La liste des rôles reprend `CustomUser.Role` côté Django, et les capacités
/// reprennent les contrôles d'accès des vues. Cette matrice ne remplace pas
/// ces contrôles — le serveur reste seul juge — elle évite d'afficher un écran
/// qui répondrait « permission refusée ».
library;

enum AppRole {
  superuser('superuser', 'Superutilisateur'),
  admin('admin', 'Administrateur'),
  owner('proprietaire', 'Propriétaire'),
  teacher('enseignant', 'Enseignant'),
  student('eleve', 'Élève'),
  parent('parent', 'Parent'),
  accountant('comptable', 'Comptable'),
  secretary('secretaire', 'Secrétaire'),
  censeur('censeur', 'Censeur'),
  proviseur('proviseur', 'Proviseur'),
  surveillant('surveillant', 'Surveillant'),
  staff('personnel', 'Personnel');

  const AppRole(this.value, this.label);

  final String value;
  final String label;

  static AppRole fromValue(String? value) => AppRole.values.firstWhere(
        (role) => role.value == value,
        orElse: () => AppRole.staff,
      );
}

/// Ce qu'un utilisateur peut faire. Une capacité correspond à un écran ou à
/// une action, pas à un endpoint : plusieurs écrans partagent la même.
enum Capability {
  /// Tableau de bord de pilotage (effectifs, finances, alertes).
  dashboard,

  /// Consulter les notes d'une classe.
  viewGrades,

  /// Saisir des notes.
  enterGrades,

  /// Configurer le barème et les bulletins.
  configureGrades,

  /// Consulter et éditer les bulletins.
  reportCards,

  /// Faire l'appel.
  takeAttendance,

  /// Vue d'ensemble de l'assiduité, toutes classes.
  superviseAttendance,

  /// Consulter la discipline.
  viewDiscipline,

  /// Enregistrer une entrée de discipline.
  recordDiscipline,

  /// Encaisser et consulter les paiements d'écolage.
  finance,

  /// Configurer les grilles d'écolage.
  configureFees,

  /// Saisir les dépenses de l'école.
  expenses,

  /// Liste des élèves de l'école.
  students,

  /// Liste des enseignants.
  teachers,

  /// Emploi du temps de l'école.
  timetable,

  /// Son propre emploi du temps.
  myTimetable,

  /// Suivi de ses enfants (parent).
  children,

  /// Lire les annonces de l'établissement.
  announcements,

  /// Publier une annonce.
  publishAnnouncements,

  /// Messagerie interne.
  messages,
}

/// Capacités par rôle, telles que le backend les autorise aujourd'hui.
///
/// Les recoupements sont voulus : proviseur, censeur et propriétaire partagent
/// l'essentiel du pilotage, l'enseignant et le surveillant partagent l'appel
/// et la discipline. C'est ce qui permet de réutiliser les mêmes écrans.
const Map<AppRole, Set<Capability>> roleCapabilities = {
  AppRole.owner: {
    Capability.announcements,
    Capability.publishAnnouncements,
    Capability.messages,
    Capability.dashboard,
    Capability.viewGrades,
    Capability.enterGrades,
    Capability.configureGrades,
    Capability.reportCards,
    Capability.takeAttendance,
    Capability.superviseAttendance,
    Capability.viewDiscipline,
    Capability.recordDiscipline,
    Capability.finance,
    Capability.configureFees,
    Capability.expenses,
    Capability.students,
    Capability.teachers,
    Capability.timetable,
  },
  AppRole.proviseur: {
    Capability.announcements,
    Capability.publishAnnouncements,
    Capability.messages,
    Capability.dashboard,
    Capability.viewGrades,
    Capability.enterGrades,
    Capability.configureGrades,
    Capability.reportCards,
    Capability.takeAttendance,
    Capability.superviseAttendance,
    Capability.viewDiscipline,
    Capability.recordDiscipline,
    Capability.finance,
    Capability.configureFees,
    Capability.expenses,
    Capability.students,
    Capability.teachers,
    Capability.timetable,
  },
  AppRole.censeur: {
    Capability.announcements,
    Capability.publishAnnouncements,
    Capability.messages,
    Capability.dashboard,
    Capability.viewGrades,
    Capability.enterGrades,
    Capability.configureGrades,
    Capability.reportCards,
    Capability.takeAttendance,
    Capability.superviseAttendance,
    Capability.viewDiscipline,
    Capability.recordDiscipline,
    // Le censeur configure l'écolage mais n'encaisse pas : `ensure_fee_configurator`
    // l'autorise, `ensure_finance_manager` ne le liste pas.
    Capability.configureFees,
    Capability.students,
    Capability.teachers,
    Capability.timetable,
  },
  AppRole.admin: {
    Capability.announcements,
    Capability.publishAnnouncements,
    Capability.messages,
    Capability.dashboard,
    Capability.viewGrades,
    Capability.enterGrades,
    Capability.configureGrades,
    Capability.reportCards,
    Capability.takeAttendance,
    Capability.superviseAttendance,
    Capability.viewDiscipline,
    Capability.recordDiscipline,
    Capability.finance,
    Capability.expenses,
    Capability.students,
    Capability.teachers,
    Capability.timetable,
  },
  AppRole.teacher: {
    Capability.announcements,
    Capability.messages,
    Capability.viewGrades,
    Capability.enterGrades,
    Capability.takeAttendance,
    Capability.viewDiscipline,
    Capability.recordDiscipline,
    Capability.students,
    Capability.myTimetable,
  },
  AppRole.accountant: {
    Capability.announcements,
    Capability.messages,
    Capability.dashboard,
    Capability.finance,
    Capability.expenses,
    Capability.students,
  },
  AppRole.surveillant: {
    Capability.announcements,
    Capability.messages,
    Capability.takeAttendance,
    Capability.superviseAttendance,
    Capability.viewDiscipline,
    Capability.recordDiscipline,
    Capability.students,
    Capability.timetable,
  },
  AppRole.secretary: {
    Capability.announcements,
    Capability.messages,
    Capability.takeAttendance,
    Capability.superviseAttendance,
    Capability.viewDiscipline,
    Capability.recordDiscipline,
    Capability.students,
    Capability.timetable,
  },
  AppRole.parent: {
    Capability.children,
    Capability.announcements,
    Capability.messages,
  },
  AppRole.student: {
    Capability.myTimetable,
  },
  AppRole.staff: {},
  AppRole.superuser: {
    Capability.announcements,
    Capability.publishAnnouncements,
    Capability.messages,
    Capability.dashboard,
    Capability.viewGrades,
    Capability.enterGrades,
    Capability.configureGrades,
    Capability.reportCards,
    Capability.takeAttendance,
    Capability.superviseAttendance,
    Capability.viewDiscipline,
    Capability.recordDiscipline,
    Capability.finance,
    Capability.configureFees,
    Capability.expenses,
    Capability.students,
    Capability.teachers,
    Capability.timetable,
  },
};

Set<Capability> capabilitiesFor(AppRole role, {bool isSuperuser = false}) {
  if (isSuperuser) return roleCapabilities[AppRole.superuser]!;
  return roleCapabilities[role] ?? const {};
}
