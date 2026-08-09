import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../api/client.dart';
import '../../api/services.dart';
import '../../core/roles.dart';
import '../../core/theme.dart';
import '../../models/school_data.dart';
import '../../state/session_state.dart';
import '../../widgets/common.dart';
import '../../widgets/screen_scaffold.dart';

/// Discipline : retards, absences et incidents.
class DisciplineScreen extends StatefulWidget {
  const DisciplineScreen({super.key});

  @override
  State<DisciplineScreen> createState() => _DisciplineScreenState();
}

class _DisciplineScreenState extends State<DisciplineScreen> {
  Future<({List<StudentRow> students, List<DisciplineRecord> records, Map<String, dynamic> summary})>?
      _future;
  int? _loadedFor;
  String _filter = 'tous';

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

  Future<({List<StudentRow> students, List<DisciplineRecord> records, Map<String, dynamic> summary})>
      _load(SessionState session) {
    final schoolId = session.school?.id;
    if (schoolId == null) {
      return Future.value(
          (students: <StudentRow>[], records: <DisciplineRecord>[], summary: <String, dynamic>{}));
    }
    return DisciplineService(session.client).load(schoolId);
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionState>();

    return ScreenScaffold(
      title: 'Discipline',
      floatingActionButton: session.can(Capability.recordDiscipline)
          ? FloatingActionButton.extended(
              onPressed: () => _openForm(context, session),
              icon: const Icon(Icons.add),
              label: const Text('Signaler'),
            )
          : null,
      child: AsyncView<({List<StudentRow> students, List<DisciplineRecord> records, Map<String, dynamic> summary})>(
        future: _future,
        onRetry: () => setState(() => _future = _load(session)),
        builder: (context, data) {
          final records = _filter == 'tous'
              ? data.records
              : data.records.where((row) => row.entryType == _filter).toList();

          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 6),
                child: Row(
                  children: [
                    Expanded(
                      child: StatTile(
                        label: 'Absences',
                        value: '${data.summary['absence_count'] ?? 0}',
                        icon: Icons.event_busy_outlined,
                        color: AppColors.danger,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: StatTile(
                        label: 'Incidents',
                        value: '${data.summary['incident_count'] ?? 0}',
                        icon: Icons.report_outlined,
                        color: AppColors.warning,
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(
                height: 46,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                  children: [
                    for (final entry in const [
                      ('tous', 'Tout'),
                      ('retard', 'Retards'),
                      ('absence', 'Absences'),
                      ('incident', 'Incidents'),
                    ])
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ChoiceChip(
                          label: Text(entry.$2),
                          selected: _filter == entry.$1,
                          onSelected: (_) => setState(() => _filter = entry.$1),
                        ),
                      ),
                  ],
                ),
              ),
              Expanded(
                child: records.isEmpty
                    ? EmptyState(
                        icon: Icons.verified_outlined,
                        title: data.records.isEmpty
                            ? 'Aucun signalement'
                            : 'Rien dans cette catégorie',
                        message: data.records.isEmpty
                            ? 'Aucune entrée de discipline pour cette année.'
                            : 'Changez de filtre pour voir les autres entrées.',
                      )
                    : ListView.separated(
                        padding: const EdgeInsets.fromLTRB(16, 4, 16, 90),
                        itemCount: records.length,
                        separatorBuilder: (_, _) => const SizedBox(height: 8),
                        itemBuilder: (context, index) =>
                            _RecordCard(record: records[index]),
                      ),
              ),
            ],
          );
        },
      ),
    );
  }

  Future<void> _openForm(BuildContext context, SessionState session) async {
    final data = await _future;
    if (data == null || !context.mounted) return;
    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => _DisciplineForm(students: data.students),
    );
    if (saved == true && mounted) {
      setState(() => _future = _load(session));
    }
  }
}

class _RecordCard extends StatelessWidget {
  const _RecordCard({required this.record});

  final DisciplineRecord record;

  @override
  Widget build(BuildContext context) {
    final color = switch (record.entryType) {
      'retard' => AppColors.warning,
      'absence' => AppColors.danger,
      _ => AppColors.info,
    };

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    record.studentName,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 14.5,
                      color: AppColors.navy,
                    ),
                  ),
                ),
                StatusPill(
                    label: record.entryTypeLabel, color: color, dense: true),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              [
                if (record.className != null && record.className!.isNotEmpty)
                  record.className!,
                formatDate(record.occurredOn),
              ].join(' · '),
              style: const TextStyle(fontSize: 12, color: AppColors.muted),
            ),
            if (record.entryType != 'incident' &&
                (double.tryParse(record.lateHours) ?? 0) > 0) ...[
              const SizedBox(height: 6),
              Text(
                '${record.lateHours} heure(s)',
                style: const TextStyle(fontSize: 12.5, color: AppColors.slate),
              ),
            ],
            if (record.incidentType.isNotEmpty) ...[
              const SizedBox(height: 6),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      record.incidentType,
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppColors.slate,
                      ),
                    ),
                  ),
                  if (record.severityLabel.isNotEmpty)
                    Text(
                      record.severityLabel,
                      style: const TextStyle(
                          fontSize: 11.5, color: AppColors.muted),
                    ),
                ],
              ),
            ],
            if (record.description.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                record.description,
                style: const TextStyle(fontSize: 12.5, color: AppColors.slate),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Formulaire de signalement.
class _DisciplineForm extends StatefulWidget {
  const _DisciplineForm({required this.students});

  final List<StudentRow> students;

  @override
  State<_DisciplineForm> createState() => _DisciplineFormState();
}

class _DisciplineFormState extends State<_DisciplineForm> {
  final _formKey = GlobalKey<FormState>();
  int? _enrollment;
  String _type = 'retard';
  String _severity = 'moyen';
  DateTime _date = DateTime.now();
  final _hours = TextEditingController(text: '1');
  final _incident = TextEditingController();
  final _description = TextEditingController();
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    _hours.dispose();
    _incident.dispose();
    _description.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_enrollment == null) {
      setState(() => _error = 'Choisissez un élève.');
      return;
    }
    final session = context.read<SessionState>();
    final schoolId = session.school?.id;
    if (schoolId == null) return;

    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await DisciplineService(session.client).record(schoolId, {
        'enrollment': _enrollment,
        'entry_type': _type,
        'occurred_on': DateFormat('yyyy-MM-dd').format(_date),
        if (_type != 'incident')
          'late_hours': double.tryParse(_hours.text.replaceAll(',', '.')) ?? 1,
        if (_type == 'incident') 'incident_type': _incident.text.trim(),
        if (_type == 'incident') 'severity': _severity,
        'description': _description.text.trim(),
      });
      if (mounted) Navigator.of(context).pop(true);
    } on ApiException catch (error) {
      if (mounted) {
        setState(() {
          _error = error.message;
          _saving = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Nouveau signalement',
                style: TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                  color: AppColors.navy,
                ),
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<int>(
                initialValue: _enrollment,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Élève'),
                items: [
                  for (final student in widget.students)
                    DropdownMenuItem(
                      value: student.enrollmentId,
                      child: Text(
                        '${student.studentName} — ${student.className}',
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                ],
                onChanged: (value) => setState(() => _enrollment = value),
              ),
              const SizedBox(height: 12),
              SegmentedButton<String>(
                showSelectedIcon: false,
                segments: const [
                  ButtonSegment(value: 'retard', label: Text('Retard')),
                  ButtonSegment(value: 'absence', label: Text('Absence')),
                  ButtonSegment(value: 'incident', label: Text('Incident')),
                ],
                selected: {_type},
                onSelectionChanged: (values) =>
                    setState(() => _type = values.first),
              ),
              const SizedBox(height: 12),
              InkWell(
                onTap: () async {
                  final picked = await showDatePicker(
                    context: context,
                    initialDate: _date,
                    firstDate:
                        DateTime.now().subtract(const Duration(days: 365)),
                    lastDate: DateTime.now(),
                    locale: const Locale('fr'),
                  );
                  if (picked != null) setState(() => _date = picked);
                },
                child: InputDecorator(
                  decoration: const InputDecoration(labelText: 'Date'),
                  child: Text(DateFormat('d MMMM yyyy', 'fr_FR').format(_date)),
                ),
              ),
              const SizedBox(height: 12),
              if (_type == 'incident') ...[
                TextFormField(
                  controller: _incident,
                  decoration: const InputDecoration(
                    labelText: 'Type d’incident',
                    hintText: 'ex : bagarre, insolence',
                  ),
                  validator: (value) => (value ?? '').trim().isEmpty
                      ? 'Précisez le type d’incident.'
                      : null,
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: _severity,
                  decoration: const InputDecoration(labelText: 'Gravité'),
                  items: const [
                    DropdownMenuItem(value: 'leger', child: Text('Léger')),
                    DropdownMenuItem(value: 'moyen', child: Text('Moyen')),
                    DropdownMenuItem(value: 'grave', child: Text('Grave')),
                  ],
                  onChanged: (value) =>
                      setState(() => _severity = value ?? 'moyen'),
                ),
              ] else
                TextFormField(
                  controller: _hours,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(
                    labelText: 'Nombre d’heures',
                    helperText: 'Doit être supérieur à 0.',
                  ),
                  validator: (value) {
                    final hours =
                        double.tryParse((value ?? '').replaceAll(',', '.'));
                    if (hours == null || hours <= 0) {
                      return 'Saisissez un nombre d’heures supérieur à 0.';
                    }
                    return null;
                  },
                ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _description,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: 'Description (facultatif)',
                  alignLabelWithHint: true,
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                ErrorBanner(message: _error!),
              ],
              const SizedBox(height: 18),
              FilledButton(
                onPressed: _saving ? null : _submit,
                child: _saving
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                            strokeWidth: 2.2, color: Colors.white),
                      )
                    : const Text('Enregistrer'),
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }
}
