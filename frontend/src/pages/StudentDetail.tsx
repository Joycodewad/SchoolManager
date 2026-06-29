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
    <div className="detail-card student-profile-card"><div><h1>{student.student_name}</h1><p>Matricule : <strong>{student.enrollment_number}</strong></p></div>
      <dl className="teacher-details">
        <dt>Nom</dt><dd>{student.student_last_name}</dd>
        <dt>Prénoms</dt><dd>{student.student_first_names}</dd>
        <dt>Nom d’utilisateur</dt><dd>{student.student_username}</dd>
        <dt>Statut de l’élève</dt><dd><span className={`student-status-badge student-status-${student.student_status}`}>{student.student_status_label}</span></dd>
        <dt>Genre</dt><dd>{student.gender_label}</dd>
        <dt>Date de naissance</dt><dd>{student.date_of_birth_display || "—"}</dd>
        <dt>Email</dt><dd>{student.student_email || "—"}</dd>
        <dt>Téléphone</dt><dd>{student.student_phone || "—"}</dd>
        <dt>Allergies et soucis de santé</dt><dd>{student.student_health_information || "Aucune information renseignée"}</dd>
        <dt>Année académique</dt><dd>{student.academic_year_name}</dd>
        <dt>Cycle actuel</dt><dd>{student.level_stage}</dd>
        <dt>Niveau actuel</dt><dd>{student.level_name}</dd>
        <dt>Série</dt><dd>{student.series || "—"}</dd>
        <dt>Classe actuelle</dt><dd>{student.school_class_name || "Non assignée"}</dd>
        <dt>Statut de l’inscription</dt><dd>{student.status === "active" ? "Active" : "Annulée"}</dd>
        <dt>Résultat de fin d’année</dt><dd>{student.student_year_result_label || "Non renseigné"}</dd>
        <dt>Moyenne de l’année écoulée</dt><dd>{student.previous_average !== null ? `${student.previous_average} / 20` : "Non renseignée"}</dd>
        <dt>Tuteur</dt><dd>{student.guardian_name || "Non renseigné"}</dd>
        <dt>Téléphone du tuteur</dt><dd>{student.guardian_phone_display || "—"}</dd>
        <dt>Profession du tuteur</dt><dd>{student.guardian_profession_display || "—"}</dd>
        <dt>Date d’inscription</dt><dd>{new Date(student.enrolled_at).toLocaleString("fr-FR")}</dd>
        <dt>Compte créé le</dt><dd>{new Date(student.student_date_joined).toLocaleString("fr-FR")}</dd>
      </dl>
    </div>
    <div className="school-panel"><h2>Historique scolaire</h2><div className="teachers-table-wrap"><table className="teachers-table"><thead><tr><th>Année académique</th><th>Cycle</th><th>Niveau</th><th>Série</th><th>Classe</th><th>Statut</th><th>Date d’inscription</th></tr></thead>
      <tbody>{student.history.map((item) => <tr key={item.id}><td>{item.academic_year}</td><td>{item.cycle || "—"}</td><td>{item.level || "—"}</td><td>{item.series || "—"}</td><td>{item.school_class || "Non assignée"}</td><td>{item.status}</td><td>{new Date(item.enrolled_at).toLocaleDateString("fr-FR")}</td></tr>)}</tbody></table></div></div>
  </div>;
}
