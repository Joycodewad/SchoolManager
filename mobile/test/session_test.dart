import 'package:ekd_school_mobile/models/school_data.dart';
import 'package:flutter_test/flutter_test.dart';

GradeSession make(String name, String start, String end, bool current,
        {int classes = 0}) =>
    GradeSession(
      id: name.hashCode,
      name: name,
      label: name,
      startDate: start,
      endDate: end,
      isCurrent: current,
      classes: List.generate(
        classes,
        (i) => GradeClass(id: i, name: 'C$i', subjects: const []),
      ),
    );

void main() {
  group('Session à mettre en avant', () {
    test('la session en cours gagne, même si elle n’est pas la première', () {
      final sessions = [
        make('1er Trimestre', '2025-09-22', '2025-12-19', false),
        make('2e Trimestre', '2026-01-05', '2026-03-30', true),
        make('3e Trimestre', '2026-04-06', '2026-06-30', false),
      ];
      expect(defaultSessionIndex(sessions), 1);
      expect(currentSession(sessions)!.name, '2e Trimestre');
    });

    test('hors période, on retombe sur la plus récente commencée', () {
      // Cas réel : en août, aucune session ne couvre la date du jour.
      final sessions = [
        make('1er Trimestre', '2025-09-22', '2025-12-19', false),
        make('1er Semestre', '2025-09-22', '2026-01-16', false),
        make('2e Semestre', '2026-01-20', '2026-06-30', false),
      ];
      expect(currentSession(sessions)!.name, '2e Semestre');
      expect(currentSession(sessions)!.isCurrent, isFalse);
    });

    test('une liste vide ne donne aucune session', () {
      expect(currentSession(const []), isNull);
      // L'index reste valide pour éviter une indexation hors bornes.
      expect(defaultSessionIndex(const []), 0);
    });

    test('sans dates, la première session sert de repli', () {
      final sessions = [make('Unique', '', '', false)];
      expect(defaultSessionIndex(sessions), 0);
    });

    test('les classes comptées sont celles de la session retenue', () {
      // Un enseignant ne reçoit du serveur que ses propres classes : le
      // compte affiché doit être celui-là, pas celui de l'école.
      final sessions = [
        make('1er Trimestre', '2025-09-22', '2025-12-19', false, classes: 3),
        make('2e Trimestre', '2026-01-05', '2026-03-30', true, classes: 7),
      ];
      expect(currentSession(sessions)!.classes.length, 7);
    });
  });
}
