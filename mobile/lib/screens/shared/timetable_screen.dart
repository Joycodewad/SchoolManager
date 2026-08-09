import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/services.dart';
import '../../core/theme.dart';
import '../../models/school_data.dart';
import '../../state/session_state.dart';
import '../../widgets/common.dart';
import '../../widgets/screen_scaffold.dart';

/// Emploi du temps, en onglets par jour.
///
/// Le même écran sert à tout le monde : `allClasses` demande la vue générale,
/// réservée aux gestionnaires — le serveur retombe de lui-même sur les seuls
/// cours de l'utilisateur s'il n'y a pas droit.
class TimetableScreen extends StatefulWidget {
  const TimetableScreen({super.key, required this.allClasses});

  final bool allClasses;

  @override
  State<TimetableScreen> createState() => _TimetableScreenState();
}

class _TimetableScreenState extends State<TimetableScreen> {
  static const _days = [
    'Lundi',
    'Mardi',
    'Mercredi',
    'Jeudi',
    'Vendredi',
    'Samedi',
  ];

  Future<List<TimetableSlot>>? _future;
  int? _loadedFor;
  late int _day = _todayIndex();

  /// Lundi = 0 côté backend ; le dimanche retombe sur lundi, faute d'onglet.
  int _todayIndex() {
    final index = DateTime.now().weekday - 1;
    return index >= 0 && index < _days.length ? index : 0;
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final session = context.watch<SessionState>();
    final key = Object.hash(session.school?.id, session.year?.id);
    if (_loadedFor != key) {
      _loadedFor = key;
      _future = _load(session);
    }
  }

  Future<List<TimetableSlot>> _load(SessionState session) {
    final schoolId = session.school?.id;
    if (schoolId == null) return Future.value(const []);
    return TimetableService(session.client)
        .slots(schoolId, all: widget.allClasses);
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionState>();

    return ScreenScaffold(
      title: widget.allClasses ? 'Emploi du temps' : 'Mes cours',
      child: Column(
        children: [
          SizedBox(
            height: 46,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              itemCount: _days.length,
              separatorBuilder: (_, _) => const SizedBox(width: 8),
              itemBuilder: (context, index) => ChoiceChip(
                label: Text(_days[index]),
                selected: _day == index,
                onSelected: (_) => setState(() => _day = index),
              ),
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: AsyncView<List<TimetableSlot>>(
              future: _future,
              onRetry: () => setState(() => _future = _load(session)),
              builder: (context, slots) {
                final dayed = slots.where((slot) => slot.day == _day).toList()
                  ..sort((a, b) => a.startTime.compareTo(b.startTime));

                if (dayed.isEmpty) {
                  return EmptyState(
                    icon: Icons.event_available_outlined,
                    title: slots.isEmpty
                        ? 'Aucun emploi du temps'
                        : 'Rien le ${_days[_day].toLowerCase()}',
                    message: slots.isEmpty
                        ? 'L’emploi du temps de cette année n’est pas encore '
                            'publié.'
                        : 'Aucun cours n’est programmé ce jour-là.',
                  );
                }

                return ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: dayed.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 8),
                  itemBuilder: (context, index) =>
                      _SlotCard(slot: dayed[index], showTeacher: widget.allClasses),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _SlotCard extends StatelessWidget {
  const _SlotCard({required this.slot, required this.showTeacher});

  final TimetableSlot slot;
  final bool showTeacher;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Container(
              width: 4,
              height: 42,
              decoration: BoxDecoration(
                color: AppColors.primary,
                borderRadius: BorderRadius.circular(3),
              ),
            ),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  slot.shortStart,
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                    color: AppColors.navy,
                  ),
                ),
                Text(
                  slot.shortEnd,
                  style: const TextStyle(fontSize: 12, color: AppColors.muted),
                ),
              ],
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    slot.subject,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 14.5,
                      color: AppColors.navy,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    [
                      slot.className,
                      if (showTeacher && slot.teacher != null) slot.teacher!,
                    ].join(' · '),
                    style:
                        const TextStyle(fontSize: 12.5, color: AppColors.muted),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
