import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../api/client.dart';
import '../../api/services.dart';
import '../../core/theme.dart';
import '../../models/school_data.dart';
import '../../state/session_state.dart';
import '../../widgets/common.dart';

/// Saisie des notes d'une matière.
///
/// Une note laissée vide n'est pas envoyée : sur un bulletin, « pas encore
/// noté » et « zéro » ne veulent pas dire la même chose, et écrire un zéro à
/// la place fausserait la moyenne.
class GradeSheetScreen extends StatefulWidget {
  const GradeSheetScreen({
    super.key,
    required this.sessionId,
    required this.classSubjectId,
    required this.className,
    required this.subjectName,
    required this.canEdit,
  });

  final int sessionId;
  final int classSubjectId;
  final String className;
  final String subjectName;
  final bool canEdit;

  @override
  State<GradeSheetScreen> createState() => _GradeSheetScreenState();
}

class _GradeSheetScreenState extends State<GradeSheetScreen> {
  GradeSheet? _sheet;
  bool _loading = true;
  bool _saving = false;
  String? _error;

  /// Saisie en cours, indexée par élève puis par ligne du barème.
  final Map<int, Map<int, String>> _edits = {};
  bool _dirty = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final session = context.read<SessionState>();
    final schoolId = session.school?.id;
    if (schoolId == null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final sheet = await GradeService(session.client)
          .sheet(schoolId, widget.sessionId, widget.classSubjectId);
      if (!mounted) return;
      setState(() {
        _sheet = sheet;
        _edits.clear();
        _dirty = false;
        for (final row in sheet.students) {
          _edits[row.enrollment] = {
            for (final line in sheet.lines)
              line.id: row.scores['${line.id}'] ?? '',
          };
        }
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _loading = false;
      });
    }
  }

  Future<void> _save() async {
    final sheet = _sheet;
    if (sheet == null) return;
    final session = context.read<SessionState>();
    final schoolId = session.school?.id;
    if (schoolId == null) return;

    final grades = <Map<String, dynamic>>[];
    for (final entry in _edits.entries) {
      for (final line in entry.value.entries) {
        final raw = line.value.trim().replaceAll(',', '.');
        if (raw.isEmpty) continue;
        final score = double.tryParse(raw);
        if (score == null) {
          setState(() => _error = 'Une note saisie n’est pas un nombre.');
          return;
        }
        grades.add({
          'enrollment': entry.key,
          'line': line.key,
          'score': score,
        });
      }
    }

    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final saved = await GradeService(session.client)
          .save(schoolId, widget.sessionId, widget.classSubjectId, grades);
      if (!mounted) return;
      setState(() {
        _sheet = saved;
        _dirty = false;
        _saving = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Notes enregistrées.')),
      );
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _saving = false;
      });
    }
  }

  /// Prévient avant de perdre une saisie non enregistrée.
  Future<bool> _confirmLeave() async {
    if (!_dirty) return true;
    final leave = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Quitter sans enregistrer ?'),
        content: const Text('Les notes saisies seront perdues.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Rester'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Quitter'),
          ),
        ],
      ),
    );
    return leave ?? false;
  }

  @override
  Widget build(BuildContext context) {
    final sheet = _sheet;

    return PopScope(
      canPop: !_dirty,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        if (await _confirmLeave() && mounted) {
          if (!context.mounted) return;
          Navigator.of(context).pop();
        }
      },
      child: Scaffold(
        appBar: AppBar(
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(widget.subjectName),
              Text(
                widget.className,
                style: const TextStyle(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w500,
                  color: AppColors.muted,
                ),
              ),
            ],
          ),
          actions: [
            if (widget.canEdit && _dirty)
              TextButton(
                onPressed: _saving ? null : _save,
                child: _saving
                    ? const SizedBox(
                        height: 16,
                        width: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Enregistrer'),
              ),
          ],
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : sheet == null
                ? Padding(
                    padding: const EdgeInsets.all(16),
                    child: ErrorBanner(
                      message: _error ?? 'Feuille de notes indisponible.',
                      onRetry: _load,
                    ),
                  )
                : Column(
                    children: [
                      if (_error != null)
                        Padding(
                          padding: const EdgeInsets.all(12),
                          child: ErrorBanner(message: _error!),
                        ),
                      if (sheet.lines.isEmpty)
                        const Expanded(
                          child: EmptyState(
                            icon: Icons.rule_outlined,
                            title: 'Barème non configuré',
                            message:
                                'Le barème de notes de cette session n’a pas '
                                'encore été défini par la direction.',
                          ),
                        )
                      else if (sheet.students.isEmpty)
                        const Expanded(
                          child: EmptyState(
                            icon: Icons.groups_outlined,
                            title: 'Aucun élève',
                            message: 'Cette classe ne compte aucun inscrit actif.',
                          ),
                        )
                      else
                        Expanded(
                          child: ListView.separated(
                            padding: const EdgeInsets.all(16),
                            itemCount: sheet.students.length,
                            separatorBuilder: (_, _) =>
                                const SizedBox(height: 10),
                            itemBuilder: (context, index) {
                              final row = sheet.students[index];
                              return _StudentGradeCard(
                                row: row,
                                lines: sheet.lines,
                                values: _edits[row.enrollment] ?? {},
                                canEdit: widget.canEdit,
                                onChanged: (lineId, value) {
                                  _edits[row.enrollment]![lineId] = value;
                                  if (!_dirty) setState(() => _dirty = true);
                                },
                              );
                            },
                          ),
                        ),
                    ],
                  ),
      ),
    );
  }
}

class _StudentGradeCard extends StatelessWidget {
  const _StudentGradeCard({
    required this.row,
    required this.lines,
    required this.values,
    required this.canEdit,
    required this.onChanged,
  });

  final GradeSheetRow row;
  final List<GradeLine> lines;
  final Map<int, String> values;
  final bool canEdit;
  final void Function(int lineId, String value) onChanged;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        row.studentName,
                        style: const TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 14.5,
                          color: AppColors.navy,
                        ),
                      ),
                      if (row.matricule.isNotEmpty)
                        Text(
                          row.matricule,
                          style: const TextStyle(
                              fontSize: 11.5, color: AppColors.muted),
                        ),
                    ],
                  ),
                ),
                if (row.average != null)
                  StatusPill(
                    label: 'Moy. ${row.average}',
                    // Le seuil de 10/20 est la moyenne de passage usuelle.
                    color: (double.tryParse(row.average!) ?? 0) >= 10
                        ? AppColors.success
                        : AppColors.danger,
                    dense: true,
                  ),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                for (final line in lines)
                  SizedBox(
                    width: 104,
                    child: TextFormField(
                      initialValue: values[line.id] ?? '',
                      enabled: canEdit,
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                      inputFormatters: [
                        FilteringTextInputFormatter.allow(
                            RegExp(r'^\d{0,3}([.,]\d{0,2})?')),
                      ],
                      textAlign: TextAlign.center,
                      decoration: InputDecoration(
                        labelText: line.name,
                        // Le maximum de la ligne évite d'avoir à deviner si
                        // la note est sur 20, sur 10 ou sur 40.
                        helperText: '/ ${line.maxScore.toStringAsFixed(0)}',
                        helperStyle: const TextStyle(fontSize: 10),
                        labelStyle: const TextStyle(fontSize: 11),
                        isDense: true,
                        contentPadding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 12),
                      ),
                      onChanged: (value) => onChanged(line.id, value),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
