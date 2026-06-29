import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Delete, Edit, Visibility } from "@mui/icons-material";
import {
  deleteTeacher,
  getTeacherAssignments,
  getTeacherUnavailability,
  listTeachers,
  saveTeacherAssignments,
  saveTeacherUnavailability,
  Teacher,
  TeacherUnavailability,
  TeacherAssignments,
} from "../api/teachers";
import { listClasses, SchoolClass } from "../api/classes";

const DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"];

const AVATAR_COLORS = ["#dbeafe", "#fce7f3", "#d1fae5", "#fef3c7", "#ede9fe"];
const TEXT_COLORS = ["#1d4ed8", "#be185d", "#065f46", "#92400e", "#5b21b6"];

const fullName = (teacher: Teacher) => `${teacher.last_name} ${teacher.first_names}`.trim();
const initials = (teacher: Teacher) =>
  `${teacher.last_name[0] ?? ""}${teacher.first_names[0] ?? ""}`.toUpperCase();
const subjects = (teacher: Teacher) =>
  teacher.subject_names.map((name) => name === teacher.primary_subject_name ? `${name} (principale)` : name).join(", ") || "Aucune";

export default function Teachers() {
  const navigate = useNavigate();
  const { schoolId } = useParams();
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [search, setSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Teacher | null>(null);
  const [assignmentTeacher, setAssignmentTeacher] = useState<Teacher | null>(null);
  const [unavailabilityTeacher, setUnavailabilityTeacher] = useState<Teacher | null>(null);
  const [schoolClasses, setSchoolClasses] = useState<SchoolClass[]>([]);
  const [classAssignments, setClassAssignments] = useState<Record<number, number[]>>({});
  const [unavailableSubjects, setUnavailableSubjects] = useState<TeacherAssignments["unavailable_subjects"]>([]);
  const [slots, setSlots] = useState<TeacherUnavailability[]>([]);
  const itemsPerPage = 5;

  const loadTeachers = async () => {
    setLoading(true);
    setError("");
    try {
      setTeachers(await listTeachers());
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Impossible de charger les enseignants.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const reload = () => void loadTeachers();
    reload();
    window.addEventListener("school-changed", reload);
    return () => window.removeEventListener("school-changed", reload);
  }, []);

  const filtered = useMemo(() => {
    const query = search.toLowerCase().trim();
    return teachers.filter((teacher) =>
      fullName(teacher).toLowerCase().includes(query) ||
      (teacher.email ?? "").toLowerCase().includes(query) ||
      (teacher.phone ?? "").includes(query),
    );
  }, [teachers, search]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / itemsPerPage));
  const paginated = filtered.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const handleDelete = async (teacher: Teacher) => {
    if (!window.confirm(`Supprimer ${fullName(teacher)} du personnel ?`)) return;
    try {
      await deleteTeacher(teacher.id);
      setTeachers((current) => current.filter((item) => item.id !== teacher.id));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "La suppression a échoué.");
    }
  };
  const openAssignments = async (teacher: Teacher) => {
    setError("");
    try {
      const [classes, data] = await Promise.all([listClasses(schoolId ?? ""), getTeacherAssignments(teacher.id)]);
      setSchoolClasses(classes);
      const teacherSubjectIds = teacher.subjects ?? [];
      setClassAssignments(Object.fromEntries(data.assignments.map((item) => [
        item.class_id, item.subject_ids.filter((subjectId) => teacherSubjectIds.includes(subjectId)),
      ])));
      setUnavailableSubjects(data.unavailable_subjects); setAssignmentTeacher(teacher);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Chargement des classes impossible."); }
  };
  const saveAssignments = async () => {
    if (!assignmentTeacher) return;
    const assignments = Object.entries(classAssignments).map(([classId, subjectIds]) => ({ class_id: Number(classId), subject_ids: subjectIds }));
    try { await saveTeacherAssignments(assignmentTeacher.id, assignments); setAssignmentTeacher(null); await loadTeachers(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Assignation impossible."); }
  };
  const toggleAssignedClass = (classId: number) => setClassAssignments((current) => {
    if (current[classId]) { const next = { ...current }; delete next[classId]; return next; }
    return { ...current, [classId]: [] };
  });
  const toggleAssignedSubject = (classId: number, subjectId: number) => setClassAssignments((current) => ({
    ...current,
    [classId]: current[classId].includes(subjectId) ? current[classId].filter((id) => id !== subjectId) : [...current[classId], subjectId],
  }));
  const assignedWeeklyHours = schoolClasses.reduce((total, schoolClass) => total + schoolClass.subjects
    .filter((config) => classAssignments[schoolClass.id]?.includes(config.subject))
    .reduce((subtotal, config) => subtotal + config.weekly_hours, 0), 0);
  const openUnavailability = async (teacher: Teacher) => {
    setError("");
    try { setSlots(await getTeacherUnavailability(teacher.id)); setUnavailabilityTeacher(teacher); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Chargement des indisponibilités impossible."); }
  };
  const addSlot = () => setSlots((current) => [...current, { day: 0, all_day: false, start_time: "08:00", end_time: "09:00" }]);
  const updateSlot = (index: number, changes: Partial<TeacherUnavailability>) => setSlots((current) => current.map((slot, slotIndex) => slotIndex === index ? { ...slot, ...changes } : slot));
  const saveUnavailability = async () => {
    if (!unavailabilityTeacher) return;
    try { await saveTeacherUnavailability(unavailabilityTeacher.id, slots); setUnavailabilityTeacher(null); await loadTeachers(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Enregistrement impossible."); }
  };

  const exportCsv = () => {
    const rows = [["Nom", "Matières", "Classe", "Email", "Numéro", "Genre"], ...filtered.map((teacher) => [
      fullName(teacher), subjects(teacher), "Non assignée", teacher.email || "", teacher.phone, teacher.gender_label,
    ])];
    const csv = rows.map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(",")).join("\n");
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    link.download = "enseignants.csv";
    link.click();
    URL.revokeObjectURL(link.href);
  };

  return (
    <div className="content-inner">
      <div className="page-header">
        <h1 className="page-title">Personnels</h1>
        <div className="page-header-actions">
          <button className="btn-export" onClick={exportCsv}>Exporter en CSV</button>
          <button className="btn-primary" onClick={() => navigate(`/schools/${schoolId}/teachers/add`)}>Ajouter du personnel</button>
        </div>
      </div>

      {error && <div className="form-error" role="alert">{error}</div>}

      <div className="toolbar">
        <div className="search-box">
          <span aria-hidden="true">⌕</span>
          <input className="search-input" placeholder="Rechercher par nom, courriel ou numéro" value={search}
            onChange={(event) => { setSearch(event.target.value); setCurrentPage(1); }} />
        </div>
      </div>

      {loading ? (
        <div className="empty-state"><p className="empty-title">Chargement du personnel…</p></div>
      ) : filtered.length === 0 ? (
        <div className="empty-state"><p className="empty-title">Aucun personnel pour le moment</p></div>
      ) : (
        <div className="teachers-table-wrap">
          <table className="teachers-table">
            <thead><tr><th>Nom</th><th>Rôle</th><th>Matières</th><th>Classes</th><th>Heures</th><th>Numéro</th><th>Actions</th></tr></thead>
            <tbody>
              {paginated.map((teacher, index) => (
                <tr key={teacher.id} className={index % 2 ? "row-alt" : ""}>
                  <td><div className="teacher-name-cell"><div className="teacher-avatar" style={{ background: AVATAR_COLORS[index % 5], color: TEXT_COLORS[index % 5] }}>{initials(teacher)}</div>{fullName(teacher)}</div></td>
                  <td>{teacher.role_label}</td>
                  <td>{subjects(teacher)}</td>
                  <td>{teacher.assigned_classes?.length ? teacher.assigned_classes.map((item) => item.name).join(", ") : <span className="class-unassigned">Non assignée</span>}</td>
                  <td><strong>{teacher.assigned_classes?.reduce((total, item) => total + item.weekly_hours, 0) ?? 0} h</strong></td>
                  <td>{teacher.phone || "—"}</td>
                  <td><div className="actions-cell">
                    <button className="action-btn view-btn" title="Voir" onClick={() => setSelected(teacher)}><Visibility fontSize="small" /></button>
                    <button className="action-btn edit-btn" title="Modifier" onClick={() => navigate(`/schools/${schoolId}/teachers/${teacher.id}/edit`)}><Edit fontSize="small" /></button>
                    {teacher.role === "enseignant" && <button className="btn-assign" title="Assigner des classes" onClick={() => void openAssignments(teacher)}>Assigner</button>}
                    {teacher.role === "enseignant" && <button className="subject-edit-btn" title="Définir les indisponibilités" onClick={() => void openUnavailability(teacher)}>Indisponibilités</button>}
                    <button className="action-btn delete-btn" title="Supprimer" onClick={() => void handleDelete(teacher)}><Delete fontSize="small" /></button>
                  </div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {filtered.length > itemsPerPage && <div className="pagination">
        <button className="pagination-btn" disabled={currentPage === 1} onClick={() => setCurrentPage((page) => page - 1)}>← Précédent</button>
        <span>Page {currentPage} sur {totalPages}</span>
        <button className="pagination-btn" disabled={currentPage === totalPages} onClick={() => setCurrentPage((page) => page + 1)}>Suivant →</button>
      </div>}

      {selected && <div className="teacher-modal-backdrop" onMouseDown={() => setSelected(null)}>
        <div className="teacher-modal teacher-full-details" onMouseDown={(event) => event.stopPropagation()}>
          <button className="modal-close" onClick={() => setSelected(null)}>×</button>
          <h2>{fullName(selected)}</h2>
          <div className="teacher-detail-summary">
            <div><span>Rôle</span><strong>{selected.role_label}</strong></div>
            <div><span>Identifiant</span><strong>{selected.username}</strong></div>
            <div><span>Téléphone</span><strong>{selected.phone || "—"}</strong></div>
            <div><span>Courriel</span><strong>{selected.email || "—"}</strong></div>
            <div><span>Genre</span><strong>{selected.gender_label || "—"}</strong></div>
            <div><span>Date de naissance</span><strong>{selected.date_of_birth || "—"}</strong></div>
            <div><span>Adresse</span><strong>{selected.address || "—"}</strong></div>
            <div><span>Volume hebdomadaire</span><strong>{selected.assigned_classes.reduce((total, item) => total + item.weekly_hours, 0)} h</strong></div>
          </div>
          <section className="teacher-detail-section"><h3>Matières déclarées</h3><p>{subjects(selected)}</p></section>
          <section className="teacher-detail-section"><h3>Classes et matières affectées</h3>
            {selected.assigned_classes.length ? <div className="teacher-assigned-class-list">{selected.assigned_classes.map((item) => <div key={item.id} className="teacher-assigned-class"><strong>{item.name}</strong><span>{item.subjects.join(", ") || "Aucune matière"}</span><b>{item.weekly_hours} h/semaine</b></div>)}</div> : <p>Aucune classe affectée.</p>}
          </section>
          <section className="teacher-detail-section"><h3>Enseignant titulaire</h3><p>{selected.homeroom_classes.length ? selected.homeroom_classes.map((item) => item.name).join(", ") : "Aucune classe."}</p></section>
          <section className="teacher-detail-section"><h3>Indisponibilités</h3>
            {selected.unavailability_schedule.length ? <ul>{selected.unavailability_schedule.map((slot, index) => <li key={`${slot.day}-${index}`}><strong>{slot.day_label}</strong> : {slot.all_day ? "Toute la journée" : `${slot.start_time} à ${slot.end_time}`}</li>)}</ul> : <p>Aucune indisponibilité.</p>}
          </section>
        </div>
      </div>}

      {assignmentTeacher && <div className="teacher-modal-backdrop" onMouseDown={() => setAssignmentTeacher(null)}><div className="teacher-modal teacher-assignment-modal" onMouseDown={(event) => event.stopPropagation()}>
        <button className="modal-close" onClick={() => setAssignmentTeacher(null)}>×</button><h2>Classes — {fullName(assignmentTeacher)}</h2>
        <p className="assignment-hours">Volume sélectionné : <strong>{assignedWeeklyHours} h/semaine</strong></p>
        <div className="teacher-class-assignment-list">{schoolClasses.map((schoolClass) => {
          const selected = Boolean(classAssignments[schoolClass.id]);
          const teacherSubjectIds = assignmentTeacher.subjects ?? [];
          const teachableSubjects = schoolClass.subjects.filter((config) => teacherSubjectIds.includes(config.subject));
          return <div className="teacher-class-assignment" key={schoolClass.id}>
            <label className="teacher-school-option"><input type="checkbox" checked={selected} onChange={() => toggleAssignedClass(schoolClass.id)}/><strong>{schoolClass.name}</strong></label>
            {selected && <div className="assignment-subjects">{teachableSubjects.map((config) => {
              const conflict = unavailableSubjects.find((item) => item.class_id === schoolClass.id && item.subject_id === config.subject);
              return <label className={`assignment-subject ${conflict ? "disabled" : ""}`} key={config.subject}>
                <input type="checkbox" disabled={Boolean(conflict)} checked={classAssignments[schoolClass.id]?.includes(config.subject)} onChange={() => toggleAssignedSubject(schoolClass.id, config.subject)}/>
                <span>{config.subject_name} — {config.weekly_hours} h/semaine{conflict ? ` (déjà assignée à ${conflict.teacher_name})` : ""}</span>
              </label>;
            })}{teachableSubjects.length === 0 && <span className="field-error">Aucune des matières de cet enseignant n’est paramétrée dans cette classe.</span>}</div>}
          </div>;
        })}</div>
        {schoolClasses.length === 0 && <p className="form-hint">Aucune classe créée pour cette année.</p>}
        <button className="btn-primary" onClick={() => void saveAssignments()}>Enregistrer les classes</button>
      </div></div>}

      {unavailabilityTeacher && <div className="teacher-modal-backdrop" onMouseDown={() => setUnavailabilityTeacher(null)}><div className="teacher-modal teacher-unavailability-modal" onMouseDown={(event) => event.stopPropagation()}>
        <button className="modal-close" onClick={() => setUnavailabilityTeacher(null)}>×</button><h2>Indisponibilités — {fullName(unavailabilityTeacher)}</h2>
        {slots.map((slot, index) => <div className="unavailability-row" key={index}>
          <select className="form-select" value={slot.day} onChange={(event) => updateSlot(index, { day: Number(event.target.value) })}>{DAYS.map((day, dayIndex) => <option key={day} value={dayIndex}>{day}</option>)}</select>
          <label className="class-option"><input type="checkbox" checked={slot.all_day} onChange={(event) => updateSlot(index, { all_day: event.target.checked, start_time: event.target.checked ? null : "08:00", end_time: event.target.checked ? null : "09:00" })}/> Toute la journée</label>
          {!slot.all_day && <><input className="form-input" type="time" value={slot.start_time ?? ""} onChange={(event) => updateSlot(index, { start_time: event.target.value })}/><span>à</span><input className="form-input" type="time" value={slot.end_time ?? ""} onChange={(event) => updateSlot(index, { end_time: event.target.value })}/></>}
          <button className="subject-delete-btn" onClick={() => setSlots((current) => current.filter((_, slotIndex) => slotIndex !== index))}>Retirer</button>
        </div>)}
        <button className="btn-add-another" onClick={addSlot}>+ Ajouter une indisponibilité</button>
        <button className="btn-primary" onClick={() => void saveUnavailability()}>Enregistrer</button>
      </div></div>}

    </div>
  );
}
