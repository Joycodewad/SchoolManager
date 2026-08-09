import 'package:ekd_school_mobile/core/navigation.dart';
import 'package:ekd_school_mobile/core/roles.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Rôles et capacités', () {
    test('un rôle inconnu ne débloque rien', () {
      // Un rôle que l'application ne connaît pas ne doit surtout pas hériter
      // des droits d'un autre : il retombe sur « personnel », sans capacité.
      expect(AppRole.fromValue('inexistant'), AppRole.staff);
      expect(capabilitiesFor(AppRole.staff), isEmpty);
    });

    test('l’enseignant saisit les notes mais ne touche pas aux finances', () {
      final teacher = capabilitiesFor(AppRole.teacher);
      expect(teacher, contains(Capability.enterGrades));
      expect(teacher, contains(Capability.takeAttendance));
      expect(teacher, isNot(contains(Capability.finance)));
      expect(teacher, isNot(contains(Capability.configureGrades)));
    });

    test('le censeur configure l’écolage sans l’encaisser', () {
      // `ensure_fee_configurator` autorise le censeur, `ensure_finance_manager`
      // ne le liste pas : la matrice doit refléter cette distinction.
      final censeur = capabilitiesFor(AppRole.censeur);
      expect(censeur, contains(Capability.configureFees));
      expect(censeur, isNot(contains(Capability.finance)));
    });

    test('le comptable tient les finances, pas les notes', () {
      final accountant = capabilitiesFor(AppRole.accountant);
      expect(accountant, contains(Capability.finance));
      expect(accountant, contains(Capability.expenses));
      expect(accountant, isNot(contains(Capability.viewGrades)));
      expect(accountant, isNot(contains(Capability.takeAttendance)));
    });

    test('le surveillant surveille sans accéder aux notes', () {
      final surveillant = capabilitiesFor(AppRole.surveillant);
      expect(surveillant, contains(Capability.takeAttendance));
      expect(surveillant, contains(Capability.recordDiscipline));
      expect(surveillant, isNot(contains(Capability.viewGrades)));
      expect(surveillant, isNot(contains(Capability.finance)));
    });

    test('le parent suit ses enfants, lit les annonces et écrit', () {
      expect(capabilitiesFor(AppRole.parent), {
        Capability.children,
        Capability.announcements,
        Capability.messages,
      });
    });

    test('le superutilisateur reçoit tout, quel que soit son rôle affiché', () {
      final capabilities =
          capabilitiesFor(AppRole.parent, isSuperuser: true);
      expect(capabilities, contains(Capability.finance));
      expect(capabilities, contains(Capability.configureGrades));
    });

    test('proviseur et propriétaire partagent le même périmètre', () {
      // Les deux rôles pilotent l'établissement : leurs écrans doivent être
      // les mêmes, sinon l'un des deux perdrait un accès sans raison.
      expect(
        capabilitiesFor(AppRole.proviseur),
        capabilitiesFor(AppRole.owner),
      );
    });
  });

  group('Navigation', () {
    test('chaque rôle garde accueil et profil', () {
      for (final role in AppRole.values) {
        final ids = destinationsFor(capabilitiesFor(role))
            .map((item) => item.id)
            .toList();
        expect(ids, contains('home'), reason: 'accueil manquant pour $role');
        expect(ids, contains('profile'), reason: 'profil manquant pour $role');
      }
    });

    test('les destinations suivent les capacités du rôle', () {
      final teacher = destinationsFor(capabilitiesFor(AppRole.teacher))
          .map((item) => item.id);
      expect(teacher, contains('grades'));
      expect(teacher, contains('attendance'));
      expect(teacher, isNot(contains('finance')));

      final accountant = destinationsFor(capabilitiesFor(AppRole.accountant))
          .map((item) => item.id);
      expect(accountant, contains('finance'));
      expect(accountant, isNot(contains('grades')));
    });

    test('le parent garde un périmètre restreint et sans gestion', () {
      final ids = destinationsFor(capabilitiesFor(AppRole.parent))
          .map((item) => item.id)
          .toList();
      expect(ids, ['home', 'announcements', 'messages', 'children', 'profile']);
      // Rien de la gestion de l'établissement ne doit lui apparaître.
      expect(ids, isNot(contains('grades')));
      expect(ids, isNot(contains('finance')));
      expect(ids, isNot(contains('students')));
    });

    test('aucune destination ne cite une capacité absente de la matrice', () {
      // Une destination dont la capacité n'est attribuée à personne serait un
      // écran inatteignable : autant le savoir tout de suite.
      final granted = <Capability>{
        for (final role in AppRole.values) ...capabilitiesFor(role),
      };
      for (final destination in allDestinations) {
        if (destination.capability == null) continue;
        expect(
          granted,
          contains(destination.capability),
          reason: '${destination.id} est inatteignable',
        );
      }
    });
  });
}
