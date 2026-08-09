import 'package:ekd_school_mobile/core/navigation.dart';
import 'package:ekd_school_mobile/core/roles.dart';
import 'package:flutter_test/flutter_test.dart';

/// Onglets réellement visibles dans la barre du bas, hors menu « Plus ».
///
/// Passe par `splitDestinations`, le même découpage que la coque : un test qui
/// recopierait la règle ne verrait pas une divergence.
List<String> bottomTabs(AppRole role) => splitDestinations(
      destinationsFor(capabilitiesFor(role)),
    ).tabs.map((item) => item.label).toList();

List<String> overflowTabs(AppRole role) => splitDestinations(
      destinationsFor(capabilitiesFor(role)),
    ).overflow.map((item) => item.label).toList();

void main() {
  group('Barre de navigation', () {
    test('l’enseignant a Accueil, Notes, Présence, Annonces, Messages', () {
      // La barre demandée, dans l'ordre exact.
      expect(
        bottomTabs(AppRole.teacher),
        ['Accueil', 'Notes', 'Présence', 'Annonces', 'Messages'],
      );
    });

    test('la discipline reste joignable par le menu « Plus »', () {
      // Sortie de la barre, mais l'enseignant y a droit côté serveur : elle
      // ne doit pas disparaître de l'application pour autant.
      expect(capabilitiesFor(AppRole.teacher),
          contains(Capability.viewDiscipline));
      expect(overflowTabs(AppRole.teacher), contains('Discipline'));
    });

    test('« Appel » a bien été renommé « Présence » partout', () {
      final labels = allDestinations.map((item) => item.label);
      expect(labels, contains('Présence'));
      expect(labels, isNot(contains('Appel')));
    });

    test('tous les rôles du personnel reçoivent annonces et messages', () {
      for (final role in [
        AppRole.teacher,
        AppRole.accountant,
        AppRole.surveillant,
        AppRole.secretary,
        AppRole.censeur,
        AppRole.proviseur,
        AppRole.owner,
      ]) {
        final capabilities = capabilitiesFor(role);
        expect(capabilities, contains(Capability.announcements),
            reason: 'annonces manquantes pour $role');
        expect(capabilities, contains(Capability.messages),
            reason: 'messages manquants pour $role');
      }
    });

    test('seule la direction publie des annonces', () {
      for (final role in [AppRole.owner, AppRole.proviseur, AppRole.censeur,
                          AppRole.admin]) {
        expect(capabilitiesFor(role), contains(Capability.publishAnnouncements),
            reason: '$role devrait pouvoir publier');
      }
      for (final role in [AppRole.teacher, AppRole.accountant,
                          AppRole.surveillant, AppRole.parent]) {
        expect(capabilitiesFor(role),
            isNot(contains(Capability.publishAnnouncements)),
            reason: '$role ne devrait pas publier');
      }
    });

    test('le parent lit les annonces et écrit, sans rien publier', () {
      final parent = capabilitiesFor(AppRole.parent);
      expect(parent, containsAll([
        Capability.children,
        Capability.announcements,
        Capability.messages,
      ]));
      expect(parent, isNot(contains(Capability.publishAnnouncements)));
    });

    test('aucune barre ne dépasse la limite d’onglets', () {
      for (final role in AppRole.values) {
        expect(bottomTabs(role).length, lessThanOrEqualTo(maxBottomTabs),
            reason: 'barre trop chargée pour $role');
      }
    });
  });
}
