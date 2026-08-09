import 'package:flutter/material.dart';

import 'roles.dart';

/// Une entrée de navigation : l'écran, son libellé, et la capacité qui la
/// débloque.
class AppDestination {
  const AppDestination({
    required this.id,
    required this.label,
    required this.icon,
    required this.selectedIcon,
    required this.capability,
  });

  final String id;
  final String label;
  final IconData icon;
  final IconData selectedIcon;

  /// `null` : visible par tout le monde (accueil, profil).
  final Capability? capability;
}

/// Toutes les destinations, dans l'ordre où elles apparaissent.
///
/// Les rôles ne se voient pas attribuer des écrans un par un : chacun reçoit
/// les destinations que ses capacités débloquent. C'est ce qui fait que
/// proviseur, censeur et propriétaire partagent naturellement le même
/// pilotage, et qu'enseignant et surveillant partagent l'appel.
const List<AppDestination> allDestinations = [
  AppDestination(
    id: 'home',
    label: 'Accueil',
    icon: Icons.home_outlined,
    selectedIcon: Icons.home,
    capability: null,
  ),
  AppDestination(
    id: 'grades',
    label: 'Notes',
    icon: Icons.grading_outlined,
    selectedIcon: Icons.grading,
    capability: Capability.viewGrades,
  ),
  AppDestination(
    id: 'attendance',
    label: 'Présence',
    icon: Icons.how_to_reg_outlined,
    selectedIcon: Icons.how_to_reg,
    capability: Capability.takeAttendance,
  ),
  // Annonces et Messages passent avant Discipline : ce sont les écrans
  // consultés tous les jours, et seuls les premiers tiennent dans la barre.
  AppDestination(
    id: 'announcements',
    label: 'Annonces',
    icon: Icons.campaign_outlined,
    selectedIcon: Icons.campaign,
    capability: Capability.announcements,
  ),
  AppDestination(
    id: 'messages',
    label: 'Messages',
    icon: Icons.forum_outlined,
    selectedIcon: Icons.forum,
    capability: Capability.messages,
  ),
  AppDestination(
    id: 'discipline',
    label: 'Discipline',
    icon: Icons.gavel_outlined,
    selectedIcon: Icons.gavel,
    capability: Capability.viewDiscipline,
  ),
  AppDestination(
    id: 'finance',
    label: 'Écolage',
    icon: Icons.payments_outlined,
    selectedIcon: Icons.payments,
    capability: Capability.finance,
  ),
  AppDestination(
    id: 'expenses',
    label: 'Dépenses',
    icon: Icons.receipt_long_outlined,
    selectedIcon: Icons.receipt_long,
    capability: Capability.expenses,
  ),
  AppDestination(
    id: 'reportCards',
    label: 'Bulletins',
    icon: Icons.description_outlined,
    selectedIcon: Icons.description,
    capability: Capability.reportCards,
  ),
  AppDestination(
    id: 'students',
    label: 'Élèves',
    icon: Icons.groups_outlined,
    selectedIcon: Icons.groups,
    capability: Capability.students,
  ),
  AppDestination(
    id: 'timetable',
    label: 'Emploi du temps',
    icon: Icons.calendar_month_outlined,
    selectedIcon: Icons.calendar_month,
    capability: Capability.timetable,
  ),
  AppDestination(
    id: 'myTimetable',
    label: 'Mes cours',
    icon: Icons.event_note_outlined,
    selectedIcon: Icons.event_note,
    capability: Capability.myTimetable,
  ),
  AppDestination(
    id: 'children',
    label: 'Mes enfants',
    icon: Icons.family_restroom_outlined,
    selectedIcon: Icons.family_restroom,
    capability: Capability.children,
  ),
  // Le profil ferme la liste : réglages plutôt qu'écran de travail, il passe
  // volontiers dans « Plus » quand la barre est pleine.
  AppDestination(
    id: 'profile',
    label: 'Profil',
    icon: Icons.person_outline,
    selectedIcon: Icons.person,
    capability: null,
  ),
];

/// Destinations ouvertes à ces capacités.
List<AppDestination> destinationsFor(Set<Capability> capabilities) =>
    allDestinations
        .where((item) =>
            item.capability == null || capabilities.contains(item.capability))
        .toList();

/// Nombre de destinations nommées dans la barre du bas.
///
/// Cinq écrans plus l'onglet « Plus », soit six emplacements : c'est ce que
/// tient un téléphone étroit sans que les libellés se tronquent.
const int maxBottomTabs = 5;

/// Découpe les destinations entre la barre et le menu « Plus ».
///
/// La barre garde toujours ses cinq premières destinations ; « Plus » vient
/// s'ajouter à côté, sans en évincer une. Les écrans de travail sont donc
/// en tête de `allDestinations`, et le profil — simple réglage — ferme la
/// liste, ce qui l'envoie dans le menu dès que la barre est pleine.
({List<AppDestination> tabs, List<AppDestination> overflow}) splitDestinations(
  List<AppDestination> destinations,
) {
  if (destinations.length <= maxBottomTabs) {
    return (tabs: destinations, overflow: const []);
  }
  return (
    tabs: destinations.take(maxBottomTabs).toList(),
    overflow: destinations.skip(maxBottomTabs).toList(),
  );
}
