import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { createClass, deleteClass, listClasses, SchoolClass, updateClass } from "../api/classes";
import { listSchoolLevels, SchoolLevel } from "../api/enrollments";
import { useAuth } from "../hooks/AuthContext";
import { listSubjects, Subject } from "../api/subjects";
import { listTeachers, Teacher } from "../api/teachers";

interface SubjectFormConfig { weeklyHours: string; coefficient: string; afterBreak: boolean; afternoon: boolean; }

export default function Classes() {
  const { schoolId = "" } = useParams();
  const { activeAcademicYear } = useAuth();
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [levels, setLevels] = useState<SchoolLevel[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<SchoolClass | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [selectedCycle, setSelectedCycle] = useState<SchoolLevel["stage"] | "">("");
  const [selectedLevel, setSelectedLevel] = useState<number | "">("");
  const [selectedSeries, setSelectedSeries] = useState("");
  const [selectedTeacher, setSelectedTeacher] = useState<number | "">("");
  const [subjectConfigs, setSubjectConfigs] = useState<Record<number, SubjectFormConfig>>({});
  const [teacherClass, setTeacherClass] = useState<SchoolClass | null>(null);
  const [subjectsClass, setSubjectsClass] = useState<SchoolClass | null>(null);
  const selectedLevelData = levels.find((level) => level.id === selectedLevel);
  const availableSeries = selectedLevelData?.name === "Seconde" ? ["CD", "A4"]
    : selectedLevelData?.name === "Première" || selectedLevelData?.name === "Terminale" ? ["D", "A4", "C4"] : [];

  const load = async () => {
    if (!activeAcademicYear) { setClasses([]); return; }
    try { setClasses(await listClasses(schoolId)); } catch (reason) { setError(reason instanceof Error ? reason.message : "Chargement impossible."); }
  };
  useEffect(() => {
    setError(""); void load();
    void listSchoolLevels(schoolId).then(setLevels).catch((reason) => setError(reason instanceof Error ? reason.message : "Chargement des niveaux impossible."));
    void listSubjects(schoolId).then(setSubjects).catch((reason) => setError(reason instanceof Error ? reason.message : "Chargement des matières impossible."));
    void listTeachers().then((items) => setTeachers(items.filter((person) => person.role === "enseignant"))).catch((reason) => setError(reason instanceof Error ? reason.message : "Chargement des enseignants impossible."));
  }, [schoolId, activeAcademicYear?.id]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(""); setMessage("");
    const form = new FormData(event.currentTarget);
    const payload = {
      level: Number(form.get("level")), series: String(form.get("series") ?? "").trim(), group: String(form.get("group") ?? "").trim(),
    };
    try {
      if (editing) await updateClass(schoolId, editing.id, payload); else await createClass(schoolId, payload);
      setMessage(editing ? "Classe mise à jour." : "Classe créée avec succès.");
      setShowForm(false); setEditing(null); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Enregistrement impossible."); }
  };
  const remove = async (item: SchoolClass) => {
    if (!window.confirm(`Supprimer la classe ${item.name} ?`)) return;
    try { await deleteClass(schoolId, item.id); setClasses((current) => current.filter((row) => row.id !== item.id)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Suppression impossible."); }
  };
  const openCreateForm = () => {
    setEditing(null); setSelectedCycle(""); setSelectedLevel(""); setSelectedSeries(""); setShowForm(true);
  };
  const openEditForm = (item: SchoolClass) => {
    setEditing(item); setSelectedCycle(item.cycle); setSelectedLevel(item.level); setSelectedSeries(item.series); setShowForm(true);
  };
  const openTeacherAssignment = (item: SchoolClass) => {
    setTeacherClass(item); setSelectedTeacher(item.homeroom_teacher ?? "");
  };
  const openSubjectSettings = (item: SchoolClass) => {
    setSubjectsClass(item);
    setSubjectConfigs(Object.fromEntries(item.subjects.map((config) => [config.subject, {
      weeklyHours: String(config.weekly_hours), coefficient: String(config.coefficient),
      afterBreak: config.can_schedule_after_break, afternoon: config.can_schedule_afternoon,
    }])));
  };
  const toggleSubject = (subjectId: number) => setSubjectConfigs((current) => {
    if (current[subjectId]) { const next = { ...current }; delete next[subjectId]; return next; }
    return { ...current, [subjectId]: { weeklyHours: "1", coefficient: "1", afterBreak: true, afternoon: true } };
  });
  const updateSubjectConfig = (subjectId: number, changes: Partial<SubjectFormConfig>) =>
    setSubjectConfigs((current) => ({ ...current, [subjectId]: { ...current[subjectId], ...changes } }));
  const saveTeacherAssignment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!teacherClass) return; setError("");
    try {
      await updateClass(schoolId, teacherClass.id, { homeroom_teacher: selectedTeacher === "" ? null : selectedTeacher });
      setTeacherClass(null); setMessage("Enseignant titulaire mis à jour."); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Assignation impossible."); }
  };
  const saveSubjectSettings = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!subjectsClass) return; setError("");
    const configuredSubjects = Object.entries(subjectConfigs).map(([subjectId, config]) => ({
      subject: Number(subjectId), weekly_hours: Number(config.weeklyHours), coefficient: Number(config.coefficient),
      can_schedule_after_break: config.afterBreak, can_schedule_afternoon: config.afternoon,
    }));
    try {
      await updateClass(schoolId, subjectsClass.id, { subjects: configuredSubjects });
      setSubjectsClass(null); setMessage("Matières appliquées à toutes les classes du même niveau et de la même série."); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Configuration impossible."); }
  };

  return <div className="content-inner classes-page">
    <div className="page-header"><div><h1 className="page-title">Classes</h1><p className="page-context">Année : {activeAcademicYear?.name ?? "Aucune année sélectionnée"}</p></div>
      <button className="btn-primary" disabled={!activeAcademicYear?.is_active || activeAcademicYear?.is_closed} onClick={openCreateForm}>Créer une classe</button></div>
    {error && <div className="form-error" role="alert">{error}</div>}{message && <div className="form-success">{message}</div>}
    {!activeAcademicYear ? <div className="empty-state"><p className="empty-title">Sélectionnez une année académique</p></div>
      : classes.length === 0 ? <div className="empty-state"><p className="empty-title">Aucune classe créée pour cette année</p></div>
      : <div className="teachers-table-wrap"><table className="teachers-table"><thead><tr><th>Nom de la classe</th><th>Cycle</th><th>Niveau</th><th>Série</th><th>Effectif</th><th>Titulaire</th><th>Matières</th><th>Actions</th></tr></thead>
        <tbody>{classes.map((item) => <tr key={item.id}><td className="class-name-cell"><strong>{item.group}</strong></td><td>{item.cycle_label}</td><td>{item.level_name}</td><td>{item.series || "—"}</td><td><strong className={item.effectif > 50 ? "class-size-over" : "class-size-ok"}>{item.effectif}</strong></td><td>{item.homeroom_teacher_name || "—"}</td><td>{item.subjects.length}</td>
          <td><div className="actions-cell"><button className="btn-assign" onClick={() => openTeacherAssignment(item)}>Titulaire</button><button className="subject-edit-btn" onClick={() => openSubjectSettings(item)}>Paramétrer matières</button><button className="subject-edit-btn" onClick={() => openEditForm(item)}>Modifier</button><button className="subject-delete-btn" onClick={() => void remove(item)}>Supprimer</button></div></td></tr>)}</tbody></table></div>}

    {showForm && <div className="teacher-modal-backdrop" onMouseDown={() => setShowForm(false)}><form className="teacher-modal class-modal" onSubmit={submit} onMouseDown={(event) => event.stopPropagation()}>
      <button type="button" className="modal-close" onClick={() => setShowForm(false)}>×</button><h2>{editing ? "Modifier la classe" : "Créer une classe"}</h2>
      <label>Cycle *<select className="form-select" value={selectedCycle} onChange={(event) => { setSelectedCycle(event.target.value as SchoolLevel["stage"]); setSelectedLevel(""); setSelectedSeries(""); }} required>
        <option value="">Choisir un cycle</option><option value="primaire">Primaire</option><option value="college">Collège</option><option value="lycee">Lycée</option>
      </select></label>
      <label>Niveau *<select className="form-select" name="level" value={selectedLevel} disabled={!selectedCycle}
        onChange={(event) => { setSelectedLevel(event.target.value ? Number(event.target.value) : ""); setSelectedSeries(""); }} required>
        <option value="">{selectedCycle ? "Choisir un niveau" : "Choisissez d’abord le cycle"}</option>
        {levels.filter((level) => level.stage === selectedCycle).map((level) => <option key={level.id} value={level.id}>{level.name}</option>)}
      </select></label>
      {selectedCycle === "lycee" && <label>Série (optionnelle)<select className="form-select" name="series" value={selectedSeries} onChange={(event) => setSelectedSeries(event.target.value)} disabled={!selectedLevel}>
        <option value="">{selectedLevel ? "Aucune série" : "Choisissez d’abord le niveau"}</option>
        {availableSeries.map((series) => <option key={series} value={series}>{series}</option>)}
      </select></label>}
      <label>Nom de la classe *<input className="form-input" name="group" defaultValue={editing?.group ?? ""} placeholder="Ex. 6ÈME A, 2NDE A4-1" required /></label>
      <p className="form-hint">Saisissez le nom complet à afficher, par exemple 6ÈME A ou 2NDE A4-1.</p>
      <button className="btn-primary" type="submit">{editing ? "Mettre à jour" : "Créer la classe"}</button>
    </form></div>}

    {teacherClass && <div className="teacher-modal-backdrop" onMouseDown={() => setTeacherClass(null)}><form className="teacher-modal" onSubmit={saveTeacherAssignment} onMouseDown={(event) => event.stopPropagation()}>
      <button type="button" className="modal-close" onClick={() => setTeacherClass(null)}>×</button><h2>Titulaire — {teacherClass.name}</h2>
      <label>Enseignant titulaire<select className="form-select" value={selectedTeacher} onChange={(event) => setSelectedTeacher(event.target.value ? Number(event.target.value) : "")}>
        <option value="">Aucun titulaire</option>{teachers.map((teacher) => <option key={teacher.id} value={teacher.id}>{teacher.last_name} {teacher.first_names}</option>)}
      </select></label>
      <button className="btn-primary" type="submit">Enregistrer le titulaire</button>
    </form></div>}

    {subjectsClass && <div className="teacher-modal-backdrop" onMouseDown={() => setSubjectsClass(null)}><form className="teacher-modal class-modal" onSubmit={saveSubjectSettings} onMouseDown={(event) => event.stopPropagation()}>
      <button type="button" className="modal-close" onClick={() => setSubjectsClass(null)}>×</button><h2>Matières — {subjectsClass.name}</h2>
      <fieldset className="class-subjects"><legend>Matières de la classe</legend>
        {subjects.length === 0 ? <p className="form-hint">Créez d’abord les matières de cette école.</p> : subjects.map((subject) => {
          const config = subjectConfigs[subject.id];
          return <div className="class-subject-row" key={subject.id}>
            <label className="class-subject-check"><input type="checkbox" checked={Boolean(config)} onChange={() => toggleSubject(subject.id)} /> {subject.name}</label>
            {config && <div className="class-subject-settings">
              <label>Heures/semaine<input className="form-input" type="number" min="1" max="60" value={config.weeklyHours} onChange={(event) => updateSubjectConfig(subject.id, { weeklyHours: event.target.value })} required /></label>
              <label>Coefficient<input className="form-input" type="number" min="0.01" step="0.01" value={config.coefficient} onChange={(event) => updateSubjectConfig(subject.id, { coefficient: event.target.value })} required /></label>
              <label className="class-option"><input type="checkbox" checked={config.afterBreak} onChange={(event) => updateSubjectConfig(subject.id, { afterBreak: event.target.checked })} /> Après la récréation</label>
              <label className="class-option"><input type="checkbox" checked={config.afternoon} onChange={(event) => updateSubjectConfig(subject.id, { afternoon: event.target.checked })} /> L’après-midi</label>
            </div>}
          </div>;
        })}
      </fieldset>
      <button className="btn-primary" type="submit">Enregistrer les matières</button>
    </form></div>}
  </div>;
}
