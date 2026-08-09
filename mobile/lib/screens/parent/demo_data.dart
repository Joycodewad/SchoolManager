/// Données de démonstration de l'espace parent.
///
/// Provisoire : le backend n'expose pas encore d'accès parent. La forme
/// choisie ici est celle que les endpoints devront rendre, pour que le
/// branchement se réduise à remplacer `demoChildren` par un appel de service.
///
/// Ce qui manque côté Django, pour mémoire :
///   * `accessible_schools()` doit reconnaître le tuteur via
///     `StudentEnrollment.guardian` ;
///   * un endpoint « mes enfants » listant les inscriptions dont l'utilisateur
///     est tuteur ;
///   * la lecture, pour ces seules inscriptions, du bulletin, de l'écolage et
///     de la discipline.
library;

class DemoSubject {
  const DemoSubject(this.name, this.average, this.coefficient);

  final String name;
  final double average;
  final int coefficient;
}

class DemoEvent {
  const DemoEvent(this.label, this.date);

  final String label;
  final String date;
}

class DemoChild {
  const DemoChild({
    required this.name,
    required this.className,
    required this.matricule,
    required this.average,
    required this.rank,
    required this.absences,
    required this.paid,
    required this.balance,
    required this.subjects,
    required this.events,
  });

  final String name;
  final String className;
  final String matricule;
  final double average;
  final int rank;
  final int absences;
  final double paid;
  final double balance;
  final List<DemoSubject> subjects;
  final List<DemoEvent> events;
}

const demoChildren = <DemoChild>[
  DemoChild(
    name: 'Akossiwa ADJO',
    className: '4ème A',
    matricule: 'MAT-2024-0142',
    average: 13.42,
    rank: 7,
    absences: 2,
    paid: 85000,
    balance: 35000,
    subjects: [
      DemoSubject('Français', 14.5, 3),
      DemoSubject('Mathématiques', 12.0, 4),
      DemoSubject('Anglais', 15.25, 2),
      DemoSubject('SVT', 13.0, 2),
      DemoSubject('Histoire-Géographie', 11.75, 2),
      DemoSubject('EPS', 16.0, 1),
    ],
    events: [
      DemoEvent('Retard — 1 heure', '2026-01-12'),
      DemoEvent('Absence justifiée', '2025-11-28'),
    ],
  ),
  DemoChild(
    name: 'Kodjo ADJO',
    className: 'CM2',
    matricule: 'MAT-2024-0311',
    average: 9.18,
    rank: 24,
    absences: 5,
    paid: 60000,
    balance: 0,
    subjects: [
      DemoSubject('Français', 8.5, 3),
      DemoSubject('Calcul', 9.75, 3),
      DemoSubject('Éveil scientifique', 10.5, 2),
      DemoSubject('Lecture', 8.0, 2),
    ],
    events: [],
  ),
];
