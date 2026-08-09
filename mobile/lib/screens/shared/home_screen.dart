import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/client.dart';
import '../../api/services.dart';
import '../../core/navigation.dart';
import '../../core/roles.dart';
import '../../core/theme.dart';
import '../../models/school_data.dart';
import '../../state/session_state.dart';
import '../../widgets/common.dart';

/// Accueil : ce que l'utilisateur a devant lui aujourd'hui, puis ses accès.
///
/// Le contenu suit le rôle. Un enseignant veut ses cours du jour ; un
/// comptable, ce qui reste à recouvrer ; un proviseur, l'état de son école.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.onOpen});

  final void Function(String destinationId) onOpen;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Future<_HomeData>? _future;
  int? _loadedFor;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final session = context.watch<SessionState>();
    // Recharge quand l'école ou l'année change, pas à chaque reconstruction.
    final key = Object.hash(session.school?.id, session.year?.id);
    if (_loadedFor != key) {
      _loadedFor = key;
      _future = _load(session);
    }
  }

  Future<_HomeData> _load(SessionState session) async {
    final schoolId = session.school?.id;
    if (schoolId == null || session.year == null) return _HomeData();

    final data = _HomeData();
    // Chaque bloc est facultatif : un rôle sans le droit correspondant reçoit
    // une erreur de permission, qui ne doit pas vider tout l'accueil.
    if (session.can(Capability.myTimetable) ||
        session.can(Capability.timetable)) {
      try {
        data.slots = await TimetableService(session.client)
            .slots(schoolId, all: session.can(Capability.timetable));
      } on ApiException {
        data.slots = const [];
      }
    }
    // Les contextes de notes donnent d'un seul appel la session en cours et,
    // pour un enseignant, ses seules classes — le serveur y filtre déjà sur
    // les matières qui lui sont confiées.
    if (session.can(Capability.viewGrades)) {
      try {
        data.sessions = await GradeService(session.client).contexts(schoolId);
      } on ApiException {
        data.sessions = const [];
      }
    }

    // Sans accès aux notes (surveillant, comptable), le comptage retombe sur
    // les classes de l'école : c'est bien leur périmètre à eux.
    if (data.sessions.isEmpty && session.can(Capability.students)) {
      try {
        data.schoolClassCount =
            (await DirectoryService(session.client).classes(schoolId)).length;
      } on ApiException {
        data.schoolClassCount = null;
      }
    }
    return data;
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionState>();
    final user = session.user;
    final destinations = destinationsFor(session.capabilities)
        .where((item) => item.id != 'home' && item.id != 'profile')
        .toList();

    return RefreshIndicator(
      onRefresh: () async {
        setState(() => _future = _load(session));
        await _future;
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        children: [
          _Greeting(
            name: user?.fullName ?? '',
            roleLabel: session.role.label,
            schoolName: session.school?.name ?? '',
            yearName: session.year?.name,
          ),
          const SizedBox(height: 18),
          AsyncView<_HomeData>(
            future: _future,
            onRetry: () => setState(() => _future = _load(session)),
            builder: (context, data) => _TodayBlock(
              data: data,
              session: session,
              onOpen: widget.onOpen,
            ),
          ),
          const SizedBox(height: 20),
          const SectionTitle(title: 'Vos accès'),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisSpacing: 10,
            mainAxisSpacing: 10,
            childAspectRatio: 1.65,
            children: [
              for (final item in destinations)
                _ShortcutCard(
                  label: item.label,
                  icon: item.icon,
                  onTap: () => widget.onOpen(item.id),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HomeData {
  List<TimetableSlot> slots = const [];
  List<GradeSession> sessions = const [];

  /// Nombre de classes de l'école, pour les rôles sans accès aux notes.
  int? schoolClassCount;

  /// Session à mettre en avant, ou `null` hors période.
  GradeSession? get session => currentSession(sessions);

  /// Classes assignées à l'utilisateur sur la session en cours. Un enseignant
  /// ne voit ici que les siennes : `grades/contexts/` les a déjà filtrées.
  int? get assignedClassCount => sessions.isEmpty ? null : session?.classes.length;
}

class _Greeting extends StatelessWidget {
  const _Greeting({
    required this.name,
    required this.roleLabel,
    required this.schoolName,
    this.yearName,
  });

  final String name;
  final String roleLabel;
  final String schoolName;
  final String? yearName;

  @override
  Widget build(BuildContext context) {
    final hour = DateTime.now().hour;
    final greeting = hour < 12
        ? 'Bonjour'
        : hour < 18
            ? 'Bon après-midi'
            : 'Bonsoir';

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppColors.primary, AppColors.navy],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '$greeting,',
            style: const TextStyle(color: Colors.white70, fontSize: 13.5),
          ),
          const SizedBox(height: 3),
          Text(
            name,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: [
              _Badge(text: roleLabel, icon: Icons.badge_outlined),
              if (schoolName.isNotEmpty)
                _Badge(text: schoolName, icon: Icons.school_outlined),
              if (yearName != null)
                _Badge(text: yearName!, icon: Icons.calendar_today_outlined),
            ],
          ),
        ],
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({required this.text, required this.icon});

  final String text;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.18),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 13, color: Colors.white),
          const SizedBox(width: 5),
          Text(
            text,
            style: const TextStyle(color: Colors.white, fontSize: 11.5),
          ),
        ],
      ),
    );
  }
}

/// Bloc « aujourd'hui » : les cours du jour, quand le rôle en a.
class _TodayBlock extends StatelessWidget {
  const _TodayBlock({
    required this.data,
    required this.session,
    required this.onOpen,
  });

  final _HomeData data;
  final SessionState session;
  final void Function(String) onOpen;

  @override
  Widget build(BuildContext context) {
    // `DateTime.weekday` va de 1 (lundi) à 7 ; le backend numérote les jours
    // à partir de 0 pour lundi.
    final today = DateTime.now().weekday - 1;
    final todaySlots = data.slots.where((slot) => slot.day == today).toList()
      ..sort((a, b) => a.startTime.compareTo(b.startTime));

    final showsTimetable = session.can(Capability.myTimetable) ||
        session.can(Capability.timetable);

    // Un enseignant compte ses classes assignées, pas celles de l'école : les
    // 23 classes de l'établissement ne lui disent rien de sa charge.
    final assigned = data.assignedClassCount;
    final classCount = assigned ?? data.schoolClassCount;
    final classLabel = assigned != null ? 'Classes assignées' : 'Classes';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (data.sessions.isNotEmpty) ...[
          _SessionBanner(session: data.session),
          const SizedBox(height: 12),
        ],
        if (classCount != null)
          Row(
            children: [
              Expanded(
                child: StatTile(
                  label: classLabel,
                  value: '$classCount',
                  icon: Icons.meeting_room_outlined,
                ),
              ),
              if (showsTimetable) ...[
                const SizedBox(width: 10),
                Expanded(
                  child: StatTile(
                    label: 'Cours aujourd’hui',
                    value: '${todaySlots.length}',
                    icon: Icons.schedule_outlined,
                    color: AppColors.info,
                  ),
                ),
              ],
            ],
          ),
        if (showsTimetable) ...[
          const SizedBox(height: 18),
          SectionTitle(
            title: 'Aujourd’hui',
            trailing: TextButton(
              onPressed: () => onOpen(
                session.can(Capability.timetable) ? 'timetable' : 'myTimetable',
              ),
              child: const Text('Tout voir'),
            ),
          ),
          if (todaySlots.isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    const Icon(Icons.free_breakfast_outlined,
                        color: AppColors.muted, size: 20),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        data.slots.isEmpty
                            ? 'Aucun emploi du temps publié pour le moment.'
                            : 'Aucun cours prévu aujourd’hui.',
                        style: const TextStyle(
                            fontSize: 13.5, color: AppColors.slate),
                      ),
                    ),
                  ],
                ),
              ),
            )
          else
            Card(
              child: Column(
                children: [
                  for (var i = 0; i < todaySlots.length; i++) ...[
                    if (i > 0) const Divider(height: 1),
                    _SlotRow(slot: todaySlots[i]),
                  ],
                ],
              ),
            ),
        ],
      ],
    );
  }
}

/// Session académique en cours.
///
/// Hors période — vacances, ou année pas encore ouverte — aucune session ne
/// couvre la date du jour. On affiche alors la dernière session travaillée en
/// le disant, plutôt que de la présenter à tort comme « en cours ».
class _SessionBanner extends StatelessWidget {
  const _SessionBanner({required this.session});

  final GradeSession? session;

  @override
  Widget build(BuildContext context) {
    final current = session;
    if (current == null) return const SizedBox.shrink();

    final live = current.isCurrent;
    final color = live ? AppColors.success : AppColors.muted;

    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(7),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                live ? Icons.play_circle_outline : Icons.history,
                size: 17,
                color: color,
              ),
            ),
            const SizedBox(width: 11),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    live ? 'Session en cours' : 'Dernière session',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: color,
                    ),
                  ),
                  const SizedBox(height: 1),
                  Text(
                    current.name,
                    style: const TextStyle(
                      fontSize: 14.5,
                      fontWeight: FontWeight.w700,
                      color: AppColors.navy,
                    ),
                  ),
                  if (current.startDate.isNotEmpty &&
                      current.endDate.isNotEmpty) ...[
                    const SizedBox(height: 2),
                    Text(
                      'Du ${formatDate(current.startDate)} '
                      'au ${formatDate(current.endDate)}',
                      style: const TextStyle(
                          fontSize: 11.5, color: AppColors.muted),
                    ),
                  ],
                ],
              ),
            ),
            if (!live)
              const StatusPill(
                label: 'Hors période',
                color: AppColors.warning,
                dense: true,
              ),
          ],
        ),
      ),
    );
  }
}

class _SlotRow extends StatelessWidget {
  const _SlotRow({required this.slot});

  final TimetableSlot slot;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      dense: true,
      leading: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            slot.shortStart,
            style: const TextStyle(
              fontWeight: FontWeight.w700,
              fontSize: 13,
              color: AppColors.navy,
            ),
          ),
          Text(
            slot.shortEnd,
            style: const TextStyle(fontSize: 11, color: AppColors.muted),
          ),
        ],
      ),
      title: Text(
        slot.subject,
        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
      ),
      subtitle: Text(
        [slot.className, if (slot.teacher != null) slot.teacher!].join(' · '),
        style: const TextStyle(fontSize: 12),
      ),
    );
  }
}

class _ShortcutCard extends StatelessWidget {
  const _ShortcutCard({
    required this.label,
    required this.icon,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.tint,
                  borderRadius: BorderRadius.circular(9),
                ),
                child: Icon(icon, size: 19, color: AppColors.primaryDark),
              ),
              Text(
                label,
                style: const TextStyle(
                  fontWeight: FontWeight.w600,
                  fontSize: 13.5,
                  color: AppColors.navy,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
