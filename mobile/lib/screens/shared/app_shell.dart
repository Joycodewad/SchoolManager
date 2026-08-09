import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/navigation.dart';
import '../../core/theme.dart';
import '../../state/session_state.dart';
import '../direction/report_cards_screen.dart';
import '../discipline/attendance_screen.dart';
import '../discipline/discipline_screen.dart';
import '../finance/expenses_screen.dart';
import '../finance/finance_screen.dart';
import '../parent/children_screen.dart';
import '../teacher/grades_screen.dart';
import 'announcements_screen.dart';
import 'home_screen.dart';
import 'messages_screen.dart';
import 'profile_screen.dart';
import 'school_picker.dart';
import 'students_screen.dart';
import 'timetable_screen.dart';

/// Coque de l'application connectée : barre du bas composée à partir des
/// capacités du rôle, et écran correspondant.
class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  String _current = 'home';

  Widget _screenFor(String id) {
    switch (id) {
      case 'grades':
        return const GradesScreen();
      case 'attendance':
        return const AttendanceScreen();
      case 'announcements':
        return const AnnouncementsScreen();
      case 'messages':
        return const MessagesScreen();
      case 'discipline':
        return const DisciplineScreen();
      case 'finance':
        return const FinanceScreen();
      case 'expenses':
        return const ExpensesScreen();
      case 'reportCards':
        return const ReportCardsScreen();
      case 'students':
        return const StudentsScreen();
      case 'timetable':
        return const TimetableScreen(allClasses: true);
      case 'myTimetable':
        return const TimetableScreen(allClasses: false);
      case 'children':
        return const ChildrenScreen();
      case 'profile':
        return const ProfileScreen();
      default:
        return HomeScreen(onOpen: _open);
    }
  }

  void _open(String id) => setState(() => _current = id);

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionState>();
    final destinations = destinationsFor(session.capabilities);

    // Le rôle a pu changer d'école en changeant de capacités : un onglet
    // devenu inaccessible ramène à l'accueil plutôt qu'à un écran interdit.
    if (!destinations.any((item) => item.id == _current)) {
      _current = 'home';
    }

    // Sans école sélectionnée, aucun écran n'a de contexte : on demande d'abord
    // laquelle, sinon chaque appel échouerait sur « Sélectionnez une école ».
    if (session.school == null && session.schools.length != 1) {
      return const SchoolPickerScreen();
    }

    final split = splitDestinations(destinations);
    final tabs = split.tabs;
    final overflow = split.overflow;

    final selectedIndex = tabs.indexWhere((item) => item.id == _current);

    return Scaffold(
      body: SafeArea(child: _screenFor(_current)),
      bottomNavigationBar: destinations.length < 2
          ? null
          : NavigationBar(
              selectedIndex: selectedIndex >= 0 ? selectedIndex : tabs.length,
              onDestinationSelected: (index) {
                if (index < tabs.length) {
                  _open(tabs[index].id);
                } else {
                  _showMore(context, overflow);
                }
              },
              destinations: [
                for (final item in tabs)
                  NavigationDestination(
                    icon: Icon(item.icon),
                    selectedIcon: Icon(item.selectedIcon),
                    label: item.label,
                  ),
                if (overflow.isNotEmpty)
                  NavigationDestination(
                    // L'onglet « Plus » se signale actif quand l'écran affiché
                    // vient de son menu, sinon on ne saurait plus où l'on est.
                    icon: Icon(
                      Icons.more_horiz,
                      color: overflow.any((item) => item.id == _current)
                          ? AppColors.primaryDark
                          : null,
                    ),
                    label: 'Plus',
                  ),
              ],
            ),
    );
  }

  void _showMore(BuildContext context, List<AppDestination> items) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (final item in items)
              ListTile(
                leading: Icon(
                  item.id == _current ? item.selectedIcon : item.icon,
                  color: item.id == _current ? AppColors.primary : AppColors.slate,
                ),
                title: Text(item.label),
                selected: item.id == _current,
                onTap: () {
                  Navigator.of(sheetContext).pop();
                  _open(item.id);
                },
              ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }
}
