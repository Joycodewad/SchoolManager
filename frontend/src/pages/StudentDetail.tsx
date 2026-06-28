import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Enrollment, getEnrollment } from "../api/enrollments";

export default function StudentDetail() {
  const { schoolId = "", id = "" } = useParams();
  const navigate = useNavigate();
  const [student, setStudent] = useState<Enrollment | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { void getEnrollment(schoolId, Number(id)).then(setStudent).catch((reason) => setError(reason instanceof Error ? reason.message : "Chargement impossible.")); }, [schoolId, id]);
  if (error) return <div className="content-inner"><div className="form-error">{error}</div></div>;
  if (!student) return <div className="content-inner"><div className="empty-state">Chargement…</div></div>;
  return <div className="content-inner student-detail-page">
    <button className="btn-back" onClick={() => navigate(`/schools/${schoolId}/students`)}>← Retour aux élèves</button>
    <div className="detail-card student-profile-card"><div><h1>{student.student_name}</h1><p>{student.enrollment_number} · {student.student_username}</p></div>
      <dl className="teacher-details"><dt>Genre</dt><dd>{student.gender_label}</dd><dt>Date de naissance</dt><dd>{student.date_of_birth_display}</dd><dt>Adresse</dt><dd>{student.student_address || "—"}</dd><dt>Niveau actuel</dt><dd>{student.level_name}</dd><dt>Classe actuelle</dt><dd>{student.school_class_name || "Non assignée"}</dd></dl>
    </div>
    <div className="school-panel"><h2>Historique scolaire</h2><div className="teachers-table-wrap"><table className="teachers-table"><thead><tr><th>Année académique</th><th>Niveau</th><th>Classe</th><th>Statut</th><th>Date d’inscription</th></tr></thead>
      <tbody>{student.history.map((item) => <tr key={item.id}><td>{item.academic_year}</td><td>{item.level || "—"}</td><td>{item.school_class || "Non assignée"}</td><td>{item.status}</td><td>{new Date(item.enrolled_at).toLocaleDateString("fr-FR")}</td></tr>)}</tbody></table></div></div>
  </div>;
}
