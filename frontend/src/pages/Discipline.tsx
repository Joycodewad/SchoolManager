import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { DisciplineRecord, DisciplineResponse, DisciplineStudent, listDisciplineRecords } from "../api/discipline";

const emptySummary = { total_late_hours: "0", total_absence_hours: "0", absence_count: 0, incident_count: 0, record_count: 0 };
const hours = (value: string | number) => `${Number(value || 0).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} h`;

export default function Discipline() {
  const { schoolId = "" } = useParams();
  const [data, setData] = useState<DisciplineResponse>({ students: [], records: [], summary: emptySummary });
  const [selectedEnrollment, setSelectedEnrollment] = useState(0);
  const [studentSearch, setStudentSearch] = useState("");
  const [studentPickerOpen, setStudentPickerOpen] = useState(false);
  const [entryFilter, setEntryFilter] = useState("");
  const [error, setError] = useState("");

  const load = async (enrollment = selectedEnrollment, type = entryFilter) => {
    try { setData(await listDisciplineRecords(schoolId, enrollment || undefined, type || undefined)); }
    catch (e) { setError(e instanceof Error ? e.message : "Chargement impossible."); }
  };

  useEffect(() => { void load(0, ""); }, [schoolId]);
  useEffect(() => { void load(selectedEnrollment, entryFilter); }, [selectedEnrollment, entryFilter]);

  const selectedStudent = data.students.find((student) => student.id === selectedEnrollment) ?? null;
  const filteredStudents = useMemo(() => {
    const query = studentSearch.trim().toLocaleLowerCase("fr");
    return data.students.filter((student) => !query || `${student.student_name} ${student.enrollment_number} ${student.class_name}`.toLocaleLowerCase("fr").includes(query)).slice(0, 40);
  }, [data.students, studentSearch]);

  const selectStudent = (student: DisciplineStudent | null) => {
    setSelectedEnrollment(student?.id ?? 0);
    setStudentSearch(student ? `${student.student_name} — ${student.enrollment_number}` : "");
    setStudentPickerOpen(false);
  };

  const recordTitle = (record: DisciplineRecord) => {
    if (record.entry_type === "retard") return `Retard de ${hours(record.late_hours)}`;
    if (record.entry_type === "absence") return `Absence de ${hours(record.late_hours)}`;
    return `${record.incident_type} · ${record.severity_label}`;
  };

  return <div className="discipline-page">
    <div className="fc-page-head"><div><h1>Discipline</h1><p>Consultez le dossier disciplinaire d’un élève : retards, absences et incidents.</p></div></div>
    {error && <div className="form-error">{error}</div>}

    <section className="discipline-filters">
      <label>Élève
        <div className={`discipline-student-select${studentPickerOpen ? " open" : ""}`}>
          <input className="form-input" value={studentSearch} onFocus={() => setStudentPickerOpen(true)} onBlur={() => window.setTimeout(() => setStudentPickerOpen(false), 150)} onChange={(e) => { setStudentSearch(e.target.value); setStudentPickerOpen(true); setSelectedEnrollment(0); }} placeholder="Rechercher par nom, matricule ou classe…" />
          {studentPickerOpen && <div className="discipline-student-options">
            <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => selectStudent(null)}>Tous les élèves</button>
            {filteredStudents.map((student) => <button type="button" key={student.id} onMouseDown={(e) => e.preventDefault()} onClick={() => selectStudent(student)}><b>{student.student_name}</b><small>{student.enrollment_number} · {student.class_name}</small></button>)}
            {!filteredStudents.length && <span>Aucun élève trouvé</span>}
          </div>}
        </div>
      </label>
      <label>Type<select className="form-select" value={entryFilter} onChange={(e) => setEntryFilter(e.target.value)}><option value="">Tout</option><option value="retard">Retards</option><option value="absence">Absences</option><option value="incident">Incidents</option></select></label>
    </section>

    <div className="fc-summary">
      <div><span>Heures de retard</span><strong>{hours(data.summary.total_late_hours)}</strong></div>
      <div><span>Absences</span><strong>{data.summary.absence_count}</strong><small>{hours(data.summary.total_absence_hours)}</small></div>
      <div><span>Incidents</span><strong>{data.summary.incident_count}</strong></div>
      <div><span>Entrées</span><strong>{data.summary.record_count}</strong></div>
    </div>

    {selectedStudent ? <div className="discipline-student-card"><strong>{selectedStudent.student_name}</strong><span>{selectedStudent.enrollment_number}</span><span>{selectedStudent.class_name}</span></div> : <div className="discipline-hint">Sélectionnez un élève pour consulter uniquement son dossier. Sans sélection, l’historique affiche toute l’année académique.</div>}

    <section className="discipline-history">
      <div className="fc-table-header"><span className="fc-chart-title">Historique disciplinaire</span></div>
      <div className="discipline-records">{data.records.map((record) => <article key={record.id} className={`discipline-record ${record.entry_type}`}>
        <div><span className="discipline-date">{record.occurred_on}</span><strong>{recordTitle(record)}</strong><small>{record.student_name} · {record.enrollment_number} · {record.class_name || "Sans classe"}</small></div>
        {(record.description || record.action_taken) && <p>{record.description}{record.action_taken && <><br /><b>Mesure :</b> {record.action_taken}</>}</p>}
        <footer>Enregistré par {record.recorded_by_name || "—"}</footer>
      </article>)}{!data.records.length && <p className="fc-empty">Aucune entrée de discipline trouvée.</p>}</div>
    </section>
  </div>;
}
