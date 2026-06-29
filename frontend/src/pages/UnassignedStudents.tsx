import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { autoAssignEnrollments, AutoAssignResult, Enrollment, listUnassignedEnrollments } from "../api/enrollments";
import { useAuth } from "../hooks/AuthContext";

const ageFromBirthDate = (birthDate: string) => {
  const birth = new Date(birthDate);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  if (today.getMonth() < birth.getMonth() || (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate())) age -= 1;
  return Number.isFinite(age) ? age : null;
};

export default function UnassignedStudents() {
  const { schoolId = "" } = useParams();
  const { activeAcademicYear } = useAuth();
  const [students, setStudents] = useState<Enrollment[]>([]);
  const [result, setResult] = useState<AutoAssignResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    if (!activeAcademicYear) { setStudents([]); return; }
    setLoading(true); setError("");
    try { setStudents(await listUnassignedEnrollments(schoolId)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Chargement impossible."); }
    finally { setLoading(false); }
  };

  useEffect(() => { setResult(null); void load(); }, [schoolId, activeAcademicYear?.id]);

  const assign = async () => {
    if (!window.confirm(`Répartir automatiquement ${students.length} élève(s) dans les classes disponibles ?`)) return;
    setAssigning(true); setError(""); setResult(null);
    try {
      const response = await autoAssignEnrollments(schoolId);
      setResult(response);
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Répartition impossible."); }
    finally { setAssigning(false); }
  };

  return <div className="content-inner unassigned-page">
    <div className="page-header">
      <div><h1 className="page-title">Élèves sans classe</h1><p className="page-context">Année : {activeAcademicYear?.name ?? "Aucune année sélectionnée"} · À répartir : <strong>{students.length}</strong></p></div>
      <button className="btn-primary" disabled={assigning || students.length === 0 || !activeAcademicYear?.is_active || activeAcademicYear?.is_closed} onClick={() => void assign()}>{assigning ? "Répartition en cours…" : "Répartir les élèves"}</button>
    </div>
    <p className="assignment-explanation">La répartition respecte le cycle, le niveau, la série et la capacité des classes. Elle équilibre les effectifs, favorise les meilleures moyennes et les élèves les moins âgés dans les premières classes, tout en réservant jusqu’à trois excellents élèves par classe lorsque cela est possible.</p>
    {error && <div className="form-error">{error}</div>}
    {result && <div className="assignment-result"><strong>{result.message}</strong>{result.warnings.map((warning) => <p key={warning}>{warning}</p>)}</div>}
    {result?.summary.length ? <div className="assignment-summary">{result.summary.map((group) => <div className="assignment-summary-card" key={group.group}><strong>{group.group}</strong><span>{group.assigned} élève(s) réparti(s)</span><ul>{group.classes.map((item) => <li key={item.id}>{item.name} : +{item.added} → {item.total}/{item.capacity}</li>)}</ul></div>)}</div> : null}
    {loading ? <div className="empty-state">Chargement…</div> : students.length === 0 ? <div className="empty-state"><p className="empty-title">Tous les élèves éligibles ont une classe</p><p>Les élèves en abandon ou bacheliers ne sont pas inclus.</p></div> :
      <div className="teachers-table-wrap unassigned-table-wrap"><table className="teachers-table"><thead><tr><th>Matricule</th><th>Nom et prénoms</th><th>Cycle</th><th>Niveau</th><th>Série</th><th>Moyenne précédente</th><th>Âge</th><th>Statut</th></tr></thead>
        <tbody>{students.map((student) => <tr key={student.id}><td><strong>{student.enrollment_number}</strong></td><td>{student.student_name}</td><td>{student.level_stage}</td><td>{student.level_name}</td><td>{student.series || "—"}</td><td><strong>{student.previous_average !== null ? `${student.previous_average}/20` : "Non renseignée"}</strong></td><td>{ageFromBirthDate(student.date_of_birth_display) ?? "—"}</td><td><span className={`student-status-badge student-status-${student.student_status}`}>{student.student_status_label}</span></td></tr>)}</tbody>
      </table></div>}
  </div>;
}
