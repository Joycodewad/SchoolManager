import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { createSubject, deleteSubject, listSubjects, Subject, updateSubject } from "../api/subjects";

export default function Subjects() {
  const { schoolId = "" } = useParams();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Subject | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = async () => {
    setError("");
    try { setSubjects(await listSubjects(schoolId)); }
    catch (e) { setError(e instanceof Error ? e.message : "Chargement impossible."); }
  };

  useEffect(() => { void load(); }, [schoolId]);

  const filtered = useMemo(() => {
    const query = search.toLowerCase();
    return subjects.filter((subject) => subject.name.toLowerCase().includes(query) || subject.code.includes(query));
  }, [subjects, search]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(""); setMessage("");
    const form = new FormData(event.currentTarget);
    const payload = { name: String(form.get("name")).trim(), code: String(form.get("code")).trim(), description: String(form.get("description")).trim() };
    try {
      if (editing) {
        const updated = await updateSubject(schoolId, editing.id, payload);
        setSubjects((current) => current.map((item) => item.id === updated.id ? updated : item));
        setMessage("Matière modifiée avec succès.");
      } else {
        const created = await createSubject(schoolId, payload);
        setSubjects((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name)));
        setMessage("Matière créée avec succès.");
      }
      setEditing(null); setShowForm(false);
    } catch (e) { setError(e instanceof Error ? e.message : "Enregistrement impossible."); }
  };

  const remove = async (subject: Subject) => {
    if (!window.confirm(`Supprimer la matière ${subject.name} ?`)) return;
    try { await deleteSubject(schoolId, subject.id); setSubjects((current) => current.filter((item) => item.id !== subject.id)); }
    catch (e) { setError(e instanceof Error ? e.message : "Suppression impossible."); }
  };

  return <div className="content-inner">
    <div className="page-header"><h1 className="page-title">Matières</h1>
      <button className="btn-primary" onClick={() => { setEditing(null); setShowForm(true); }}>Ajouter une matière</button>
    </div>
    {error && <div className="form-error">{error}</div>}{message && <div className="form-success">{message}</div>}
    <div className="toolbar"><div className="search-box"><span>⌕</span><input className="search-input" value={search}
      onChange={(event) => setSearch(event.target.value)} placeholder="Rechercher une matière" /></div></div>
    {filtered.length === 0 ? <div className="empty-state"><p className="empty-title">Aucune matière pour le moment</p></div> :
      <div className="teachers-table-wrap"><table className="teachers-table"><thead><tr><th>Nom</th><th>Code</th><th>Description</th><th>Actions</th></tr></thead>
        <tbody>{filtered.map((subject) => <tr key={subject.id}><td><strong>{subject.name}</strong></td><td>{subject.code}</td><td>{subject.description || "—"}</td>
          <td><div className="actions-cell"><button className="subject-edit-btn" onClick={() => { setEditing(subject); setShowForm(true); }}>Modifier</button>
            <button className="subject-delete-btn" onClick={() => void remove(subject)}>Supprimer</button></div></td></tr>)}</tbody></table></div>}

    {showForm && <div className="teacher-modal-backdrop" onMouseDown={() => setShowForm(false)}><form className="teacher-modal subject-form" onSubmit={submit} onMouseDown={(event) => event.stopPropagation()}>
      <button type="button" className="modal-close" onClick={() => setShowForm(false)}>×</button><h2>{editing ? "Modifier la matière" : "Ajouter une matière"}</h2>
      <label>Nom *<input className="form-input" name="name" defaultValue={editing?.name} required /></label>
      <label>Code *<input className="form-input" name="code" defaultValue={editing?.code} placeholder="ex: mathematiques" required /></label>
      <label>Description<textarea className="form-input subject-description" name="description" defaultValue={editing?.description} /></label>
      <button className="btn-primary" type="submit">Enregistrer</button>
    </form></div>}
  </div>;
}
