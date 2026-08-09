import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../api/client.dart';
import '../../api/services.dart';
import '../../core/theme.dart';
import '../../models/school_data.dart';
import '../../models/session.dart';
import '../../state/session_state.dart';
import '../../widgets/common.dart';
import '../../widgets/screen_scaffold.dart';

/// Couleur et icône d'un statut de présence.
({Color color, IconData icon}) statusStyle(String status) => switch (status) {
      'present' => (color: AppColors.success, icon: Icons.check_circle),
      'absent' => (color: AppColors.danger, icon: Icons.cancel),
      'retard' => (color: AppColors.warning, icon: Icons.schedule),
      'excuse' => (color: AppColors.info, icon: Icons.assignment_turned_in),
      _ => (color: AppColors.muted, icon: Icons.help_outline),
    };

/// Appel : choix de la classe et de la date, puis relevé élève par élève.
///
/// Tout le monde est présent par défaut — c'est le cas courant, et cocher les
/// quelques absents va bien plus vite que pointer toute la classe.
class AttendanceScreen extends StatefulWidget {
  const AttendanceScreen({super.key});

  @override
  State<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends State<AttendanceScreen> {
  Future<List<Map<String, dynamic>>>? _classes;
  int? _loadedFor;
  int? _classId;
  DateTime _date = DateTime.now();

  AttendanceSheet? _sheet;
  bool _loadingSheet = false;
  bool _saving = false;
  bool _dirty = false;
  String? _error;

  String get _isoDate => DateFormat('yyyy-MM-dd').format(_date);

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final session = context.watch<SessionState>();
    final key = Object.hash(session.school?.id, session.year?.id);
    if (_loadedFor != key) {
      _loadedFor = key;
      _classes = _loadClasses(session);
      _classId = null;
      _sheet = null;
    }
  }

  Future<List<Map<String, dynamic>>> _loadClasses(SessionState session) async {
    final schoolId = session.school?.id;
    if (schoolId == null) return const [];
    return DirectoryService(session.client).classes(schoolId);
  }

  Future<void> _loadSheet() async {
    final session = context.read<SessionState>();
    final schoolId = session.school?.id;
    final classId = _classId;
    if (schoolId == null || classId == null) return;

    setState(() {
      _loadingSheet = true;
      _error = null;
    });
    try {
      final sheet = await AttendanceService(session.client)
          .sheet(schoolId, classId, takenOn: _isoDate);
      if (!mounted) return;
      setState(() {
        _sheet = sheet;
        _dirty = false;
        _loadingSheet = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _loadingSheet = false;
        _sheet = null;
      });
    }
  }

  Future<void> _save() async {
    final sheet = _sheet;
    final session = context.read<SessionState>();
    final schoolId = session.school?.id;
    final classId = _classId;
    if (sheet == null || schoolId == null || classId == null) return;

    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await AttendanceService(session.client).save(
        schoolId,
        classId: classId,
        rows: sheet.students,
        takenOn: _isoDate,
      );
      if (!mounted) return;
      setState(() {
        _saving = false;
        _dirty = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Appel enregistré.')),
      );
      await _loadSheet();
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _saving = false;
      });
    }
  }

  void _setAll(String status) {
    final sheet = _sheet;
    if (sheet == null) return;
    setState(() {
      for (final row in sheet.students) {
        row.status = status;
        if (status != 'retard') row.minutesLate = 0;
      }
      _dirty = true;
    });
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _date,
      // L'appel se fait le jour même ou se rattrape après coup ; il ne se
      // prend pas d'avance, d'où la borne à aujourd'hui.
      firstDate: DateTime.now().subtract(const Duration(days: 365)),
      lastDate: DateTime.now(),
      locale: const Locale('fr'),
    );
    if (picked != null) {
      setState(() => _date = picked);
      await _loadSheet();
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionState>();
    final sheet = _sheet;

    return ScreenScaffold(
      title: 'Appel',
      floatingActionButton: (sheet != null && _dirty)
          ? FloatingActionButton.extended(
              onPressed: _saving ? null : _save,
              icon: _saving
                  ? const SizedBox(
                      height: 16,
                      width: 16,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.save_outlined),
              label: Text(_saving ? 'Envoi…' : 'Enregistrer'),
            )
          : null,
      child: Column(
        children: [
          _Toolbar(
            classes: _classes,
            classId: _classId,
            date: _date,
            onPickDate: _pickDate,
            onClassChanged: (value) {
              setState(() => _classId = value);
              _loadSheet();
            },
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: ErrorBanner(message: _error!, onRetry: _loadSheet),
            ),
          Expanded(
            child: _classId == null
                ? const EmptyState(
                    icon: Icons.checklist_outlined,
                    title: 'Choisissez une classe',
                    message:
                        'Sélectionnez la classe et la date pour faire l’appel.',
                  )
                : _loadingSheet
                    ? const Center(child: CircularProgressIndicator())
                    : sheet == null
                        ? const SizedBox.shrink()
                        : sheet.students.isEmpty
                            ? const EmptyState(
                                icon: Icons.groups_outlined,
                                title: 'Aucun élève',
                                message:
                                    'Cette classe ne compte aucun inscrit actif.',
                              )
                            : _SheetBody(
                                sheet: sheet,
                                onSetAll: _setAll,
                                onChanged: () => setState(() => _dirty = true),
                                canSupervise: session.school != null,
                              ),
          ),
        ],
      ),
    );
  }
}

class _Toolbar extends StatelessWidget {
  const _Toolbar({
    required this.classes,
    required this.classId,
    required this.date,
    required this.onPickDate,
    required this.onClassChanged,
  });

  final Future<List<Map<String, dynamic>>>? classes;
  final int? classId;
  final DateTime date;
  final VoidCallback onPickDate;
  final ValueChanged<int?> onClassChanged;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 10),
      child: Row(
        children: [
          Expanded(
            child: FutureBuilder<List<Map<String, dynamic>>>(
              future: classes,
              builder: (context, snapshot) {
                final items = snapshot.data ?? const [];
                return DropdownButtonFormField<int>(
                  initialValue: classId,
                  isExpanded: true,
                  decoration: const InputDecoration(
                    labelText: 'Classe',
                    isDense: true,
                  ),
                  items: [
                    for (final klass in items)
                      DropdownMenuItem(
                        value: asInt(klass['id']),
                        child: Text(
                          asText(klass['group']),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                  ],
                  onChanged: onClassChanged,
                );
              },
            ),
          ),
          const SizedBox(width: 10),
          OutlinedButton.icon(
            onPressed: onPickDate,
            icon: const Icon(Icons.calendar_today_outlined, size: 16),
            label: Text(DateFormat('d MMM', 'fr_FR').format(date)),
            style: OutlinedButton.styleFrom(
              minimumSize: const Size(0, 48),
              side: const BorderSide(color: AppColors.border),
              foregroundColor: AppColors.navy,
            ),
          ),
        ],
      ),
    );
  }
}

class _SheetBody extends StatelessWidget {
  const _SheetBody({
    required this.sheet,
    required this.onSetAll,
    required this.onChanged,
    required this.canSupervise,
  });

  final AttendanceSheet sheet;
  final void Function(String status) onSetAll;
  final VoidCallback onChanged;
  final bool canSupervise;

  @override
  Widget build(BuildContext context) {
    final counts = <String, int>{};
    for (final row in sheet.students) {
      counts[row.status] = (counts[row.status] ?? 0) + 1;
    }

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: [
              if (sheet.isTaken)
                const StatusPill(
                  label: 'Appel déjà fait',
                  color: AppColors.info,
                  dense: true,
                )
              else
                const StatusPill(
                  label: 'Appel non fait',
                  color: AppColors.warning,
                  dense: true,
                ),
              const Spacer(),
              TextButton.icon(
                onPressed: () => onSetAll('present'),
                icon: const Icon(Icons.done_all, size: 16),
                label: const Text('Tous présents'),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 10),
          child: Row(
            children: [
              for (final status in sheet.statuses)
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: StatusPill(
                    label: '${status.label} ${counts[status.value] ?? 0}',
                    color: statusStyle(status.value).color,
                    dense: true,
                  ),
                ),
            ],
          ),
        ),
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 90),
            itemCount: sheet.students.length,
            separatorBuilder: (_, _) => const SizedBox(height: 8),
            itemBuilder: (context, index) => _AttendanceCard(
              row: sheet.students[index],
              statuses: sheet.statuses,
              onChanged: onChanged,
            ),
          ),
        ),
      ],
    );
  }
}

class _AttendanceCard extends StatefulWidget {
  const _AttendanceCard({
    required this.row,
    required this.statuses,
    required this.onChanged,
  });

  final AttendanceRow row;
  final List<LabeledValue> statuses;
  final VoidCallback onChanged;

  @override
  State<_AttendanceCard> createState() => _AttendanceCardState();
}

class _AttendanceCardState extends State<_AttendanceCard> {
  @override
  Widget build(BuildContext context) {
    final row = widget.row;
    final style = statusStyle(row.status);

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        child: Column(
          children: [
            Row(
              children: [
                Icon(style.icon, color: style.color, size: 22),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        row.studentName,
                        style: const TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 14,
                          color: AppColors.navy,
                        ),
                      ),
                      if (row.enrollmentNumber.isNotEmpty)
                        Text(
                          row.enrollmentNumber,
                          style: const TextStyle(
                              fontSize: 11, color: AppColors.muted),
                        ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            SegmentedButton<String>(
              showSelectedIcon: false,
              style: SegmentedButton.styleFrom(
                visualDensity: VisualDensity.compact,
                textStyle: const TextStyle(fontSize: 11.5),
              ),
              segments: [
                for (final status in widget.statuses)
                  ButtonSegment(
                    value: status.value,
                    label: Text(_short(status.label)),
                  ),
              ],
              selected: {row.status},
              onSelectionChanged: (values) {
                setState(() {
                  row.status = values.first;
                  if (row.status != 'retard') row.minutesLate = 0;
                });
                widget.onChanged();
              },
            ),
            // Le nombre de minutes n'a de sens que pour un retard ; l'afficher
            // toujours encombrerait chaque carte pour un cas minoritaire.
            if (row.status == 'retard') ...[
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(Icons.timer_outlined,
                      size: 16, color: AppColors.muted),
                  const SizedBox(width: 8),
                  SizedBox(
                    width: 90,
                    child: TextFormField(
                      initialValue: '${row.minutesLate}',
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        isDense: true,
                        suffixText: 'min',
                        contentPadding: EdgeInsets.symmetric(
                            horizontal: 8, vertical: 10),
                      ),
                      onChanged: (value) {
                        row.minutesLate = int.tryParse(value) ?? 0;
                        widget.onChanged();
                      },
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// Les libellés du serveur sont longs pour un bouton segmenté sur mobile.
  String _short(String label) => switch (label) {
        'Absence justifiée' => 'Justifié',
        'En retard' => 'Retard',
        _ => label,
      };
}
