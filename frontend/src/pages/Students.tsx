import { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Enrollment, listEnrollments, listSchoolLevels, SchoolLevel, updateEnrollment } from "../api/enrollments";
import { listClasses, SchoolClass } from "../api/classes";
import { useAuth } from "../hooks/AuthContext";

const ITEMS_PER_PAGE = 10;

export default function Students() {
  const { schoolId = "" } = useParams();
  const navigate = useNavigate();
  const { activeAcademicYear } = useAuth();
  const [students, setStudents] = useState<Enrollment[]>([]);
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [levels, setLevels] = useState<SchoolLevel[]>([]);
  const [search, setSearch] = useState("");
  const [classFilter, setClassFilter] = useState("all");
  const [levelFilter, setLevelFilter] = useState("all");
  const [seriesFilter, setSeriesFilter] = useState("all");
  const [genderFilter, setGenderFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [editing, setEditing] = useState<Enrollment | null>(null);
  const [assigning, setAssigning] = useState<Enrollment | null>(null);
  const [editLevel, setEditLevel] = useState<number | "">("");
  const [editCycle, setEditCycle] = useState<SchoolLevel["stage"] | "">("");
  const [editSeries, setEditSeries] = useState("");
  const editLevelData = levels.find((level) => level.id === Number(editLevel));
  const editAvailableSeries = editLevelData?.name === "Seconde" ? ["CD", "A4", "G1", "G2", "G3", "F1", "F2", "F3", "F4", "E", "Ti"]
    : editLevelData?.name === "Première" || editLevelData?.name === "Terminale" ? ["D", "A4", "C4", "G1", "G2", "G3", "F1", "F2", "F3", "F4", "E", "Ti"] : [];

  const load = async () => {
    if (!activeAcademicYear) { setStudents([]); return; }
    setLoading(true);
    try { setStudents(await listEnrollments(schoolId)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Chargement impossible."); }
    finally { setLoading(false); }
  };
  const loadClasses = async () => {
    if (!activeAcademicYear) { setClasses([]); return []; }
    const classList = await listClasses(schoolId);
    setClasses(classList);
    return classList;
  };
  useEffect(() => {
    setCurrentPage(1); setError(""); void load();
    if (activeAcademicYear) {
      void loadClasses().catch((reason) => setError(reason instanceof Error ? reason.message : "Chargement des classes impossible."));
    } else {
      setClasses([]);
    }
    void listSchoolLevels(schoolId).then(setLevels).catch((reason) => setError(reason instanceof Error ? reason.message : "Chargement des niveaux impossible."));
  }, [schoolId, activeAcademicYear?.id]);

  const filtered = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("fr");
    return students.filter((student) => {
      const matchesSearch = !query || [student.student_name, student.student_username, student.enrollment_number].some((field) => field.toLocaleLowerCase("fr").includes(query));
      const matchesClass = classFilter === "all" || (classFilter === "unassigned" ? !student.school_class : student.school_class === Number(classFilter));
      return matchesSearch && matchesClass
        && (levelFilter === "all" || student.level === Number(levelFilter))
        && (seriesFilter === "all" || student.series === seriesFilter)
        && (genderFilter === "all" || student.student_gender === genderFilter)
        && (statusFilter === "all" || student.student_status === statusFilter);
    });
  }, [students, search, classFilter, levelFilter, seriesFilter, genderFilter, statusFilter]);
  const totalPages = Math.max(1, Math.ceil(filtered.length / ITEMS_PER_PAGE));
  const page = Math.min(currentPage, totalPages);
  const visibleStudents = filtered.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);

  const submitEdit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!editing) return; setError("");
    const form = new FormData(event.currentTarget);
    try {
      await updateEnrollment(schoolId, editing.id, {
        enrollment_number: String(form.get("enrollment_number")), last_name: String(form.get("last_name")), first_names: String(form.get("first_names")),
        gender: String(form.get("gender")) as "M" | "F", date_of_birth: String(form.get("date_of_birth")), health_information: String(form.get("health_information") ?? ""),
        student_status: String(form.get("student_status")) as "nouveau" | "redoublant" | "abandon" | "bachelier",
        previous_average: form.get("previous_average") === "" ? null : Number(form.get("previous_average")),
        level: Number(form.get("level")), series: editSeries, school_class: form.get("school_class") ? Number(form.get("school_class")) : null,
      });
      setEditing(null); setMessage("Élève mis à jour."); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Modification impossible."); }
  };
  const submitAssignment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!assigning) return;
    const schoolClass = classes.find((item) => item.id === Number(new FormData(event.currentTarget).get("school_class")));
    if (!schoolClass) return;
    try { await updateEnrollment(schoolId, assigning.id, { level: schoolClass.level, series: schoolClass.series, school_class: schoolClass.id }); setAssigning(null); setMessage("Élève assigné à la classe."); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Assignation impossible."); }
  };
  const openAssignment = async (student: Enrollment) => {
    setError("");
    try {
      await loadClasses();
      setAssigning(student);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Chargement des classes impossible.");
    }
  };

  return <div className="content-inner students-page">
    <div className="page-header"><div><h1 className="page-title">Élèves</h1><p className="page-context">Année : {activeAcademicYear?.name ?? "Aucune année sélectionnée"} · Effectif total : <strong>{students.length}</strong> · Résultat des filtres : <strong>{filtered.length}</strong></p></div>
      <button className="btn-primary" disabled={!activeAcademicYear?.is_active || activeAcademicYear?.is_closed} onClick={() => navigate(`/schools/${schoolId}/enrollments`)}>Inscrire des élèves</button></div>
    {error && <div className="form-error">{error}</div>}{message && <div className="form-success">{message}</div>}
    <div className="student-filters">
      <input className="form-input" type="search" placeholder="Nom, matricule ou identifiant" value={search} onChange={(event) => { setSearch(event.target.value); setCurrentPage(1); }}/>
      <select className="form-select" value={classFilter} onChange={(event) => setClassFilter(event.target.value)}><option value="all">Toutes les classes</option><option value="unassigned">Élèves sans classe</option>{classes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
      <select className="form-select" value={levelFilter} onChange={(event) => setLevelFilter(event.target.value)}><option value="all">Tous les niveaux</option>{levels.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
      <select className="form-select" value={seriesFilter} onChange={(event) => setSeriesFilter(event.target.value)}><option value="all">Toutes les séries</option>{[...new Set(classes.map((item) => item.series).filter(Boolean))].map((series) => <option key={series}>{series}</option>)}</select>
      <select className="form-select" value={genderFilter} onChange={(event) => setGenderFilter(event.target.value)}><option value="all">Tous les genres</option><option value="M">Masculin</option><option value="F">Féminin</option></select>
      <select className="form-select" value={statusFilter} onChange={(event) => { setStatusFilter(event.target.value); setCurrentPage(1); }}><option value="all">Tous les statuts</option><option value="nouveau">Nouveau</option><option value="redoublant">Redoublant</option><option value="abandon">Abandon</option><option value="bachelier">Bachelier</option></select>
    </div>
    {loading ? <div className="empty-state">Chargement…</div> : filtered.length === 0 ? <div className="empty-state"><p className="empty-title">Aucun élève trouvé</p></div> : <div className="teachers-table-wrap"><table className="teachers-table">
      <thead><tr><th>Matricule</th><th>Nom et prénoms</th><th>Statut</th><th>Cycle</th><th>Niveau</th><th>Série</th><th>Classe</th><th>Naissance</th><th>Genre</th><th>Actions</th></tr></thead>
      <tbody>{visibleStudents.map((student) => <tr key={student.id}><td><strong>{student.enrollment_number}</strong></td><td>{student.student_name}</td><td><span className={`student-status-badge student-status-${student.student_status}`}>{student.student_status_label}</span></td><td>{student.level_stage}</td><td><span className="level-badge">{student.level_name}</span></td><td>{student.series || "—"}</td><td>{student.school_class_name || <span className="class-unassigned">Non assignée</span>}</td><td>{student.date_of_birth_display}</td><td>{student.gender_label}</td>
        <td><div className="actions-cell"><button className="action-btn view-btn" onClick={() => navigate(`/schools/${schoolId}/students/${student.id}`)}>Détails</button><button className="subject-edit-btn" onClick={() => { setEditing(student); setEditLevel(student.level); setEditCycle(levels.find((level) => level.id === student.level)?.stage ?? ""); setEditSeries(student.series); }}>Modifier</button><button className="btn-assign" onClick={() => void openAssignment(student)}>Assigner</button></div></td></tr>)}</tbody>
    </table></div>}
    {filtered.length > ITEMS_PER_PAGE && <div className="pagination"><button className="pagination-btn" disabled={page === 1} onClick={() => setCurrentPage(page - 1)}>← Précédent</button><span>Page {page} sur {totalPages}</span><button className="pagination-btn" disabled={page === totalPages} onClick={() => setCurrentPage(page + 1)}>Suivant →</button></div>}

    {editing && <div className="teacher-modal-backdrop" onMouseDown={() => setEditing(null)}><form className="teacher-modal enrollment-form" onSubmit={submitEdit} onMouseDown={(event) => event.stopPropagation()}><button type="button" className="modal-close" onClick={() => setEditing(null)}>×</button><h2>Modifier l’élève</h2>
      <label>Nom *<input className="form-input" name="last_name" defaultValue={editing.student_last_name} required /></label><label>Prénoms *<input className="form-input" name="first_names" defaultValue={editing.student_first_names} required /></label>
      <label>Matricule *<input className="form-input" name="enrollment_number" defaultValue={editing.enrollment_number} required /></label><label>Genre *<select className="form-select" name="gender" defaultValue={editing.student_gender}><option value="M">Masculin</option><option value="F">Féminin</option></select></label>
      <label>Statut *<select className="form-select" name="student_status" defaultValue={editing.student_status}><option value="nouveau">Nouveau</option><option value="redoublant">Redoublant</option><option value="abandon">Abandon</option><option value="bachelier">Bachelier</option></select></label>
      <label>Moyenne précédente /20<input className="form-input" name="previous_average" type="number" min="0" max="20" step="0.01" defaultValue={editing.previous_average ?? ""} /></label>
      <label>Cycle *<select className="form-select" value={editCycle} onChange={(event) => { setEditCycle(event.target.value as SchoolLevel["stage"]); setEditLevel(""); setEditSeries(""); }}><option value="primaire">Primaire</option><option value="college">Collège</option><option value="lycee">Lycée</option></select></label>
      <label>Niveau *<select className="form-select" name="level" value={editLevel} onChange={(event) => { setEditLevel(Number(event.target.value)); setEditSeries(""); }}><option value="">Choisir</option>{levels.filter((item) => item.stage === editCycle).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      {editCycle === "lycee" && <label>Série *<select className="form-select" value={editSeries} onChange={(event) => setEditSeries(event.target.value)} required><option value="">Choisir</option>{editAvailableSeries.map((series) => <option key={series}>{series}</option>)}</select></label>}
      <label>Classe<select className="form-select" name="school_class" defaultValue={editing.school_class ?? ""}><option value="">Non assignée</option>{classes.filter((item) => item.level === Number(editLevel) && (editCycle !== "lycee" || item.series.toLowerCase() === editSeries.toLowerCase())).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      <label>Date de naissance *<input className="form-input" name="date_of_birth" type="date" defaultValue={editing.date_of_birth_display} required /></label><label className="enrollment-address">Allergies et soucis de santé<textarea className="form-input" name="health_information" defaultValue={editing.student_health_information}/></label><button className="btn-primary">Mettre à jour</button>
    </form></div>}
    {assigning && <div className="teacher-modal-backdrop" onMouseDown={() => setAssigning(null)}><form className="teacher-modal" onSubmit={submitAssignment} onMouseDown={(event) => event.stopPropagation()}><button type="button" className="modal-close" onClick={() => setAssigning(null)}>×</button><h2>Assigner {assigning.student_name}</h2>
      <label>Classe *<select className="form-select" name="school_class" defaultValue={assigning.school_class ?? ""} required><option value="">Choisir une classe</option>{classes.map((item) => <option key={item.id} value={item.id}>{item.name} — {item.level_name}{item.series ? ` — Série ${item.series}` : ""}</option>)}</select></label>
      {classes.length === 0 && <span className="field-error">Aucune classe n’est disponible pour cette année académique.</span>}<button className="btn-primary" disabled={classes.length === 0}>Assigner à la classe</button>
    </form></div>}
  </div>;
}
