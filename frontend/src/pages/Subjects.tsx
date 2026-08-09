import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  createSubject, createSubjectCategory, deleteSubject, deleteSubjectCategory,
  listSubjectCategories, listSubjects, Subject, SubjectCategory, updateSubject,
  updateSubjectCategory,
} from "../api/subjects";

export default function Subjects() {
  const { schoolId = "" } = useParams();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [categories, setCategories] = useState<SubjectCategory[]>([]);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [editing, setEditing] = useState<Subject | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showCategories, setShowCategories] = useState(false);
  const [showNewCategory, setShowNewCategory] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [newCategoryError, setNewCategoryError] = useState("");
  const [newCategoryName, setNewCategoryName] = useState("");
  const [editingCategory, setEditingCategory] = useState<SubjectCategory | null>(null);
  const [editCategoryName, setEditCategoryName] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = async () => {
    setError("");
    try {
      const [rows, types] = await Promise.all([listSubjects(schoolId), listSubjectCategories(schoolId)]);
      setSubjects(rows);
      setCategories(types);
    } catch (e) { setError(e instanceof Error ? e.message : "Chargement impossible."); }
  };

  useEffect(() => { void load(); }, [schoolId]);

  const filtered = useMemo(() => {
    const query = search.toLowerCase();
    return subjects.filter((subject) =>
      (subject.name.toLowerCase().includes(query) || subject.code.includes(query))
      && (categoryFilter === ""
        || (categoryFilter === "none" ? subject.category === null : subject.category === Number(categoryFilter))));
  }, [subjects, search, categoryFilter]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(""); setMessage("");
    const form = new FormData(event.currentTarget);
    const payload = {
      name: String(form.get("name")).trim(),
      code: String(form.get("code")).trim(),
      category: selectedCategory === "" ? null : Number(selectedCategory),
      description: String(form.get("description")).trim(),
    };
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
      setCategories(await listSubjectCategories(schoolId));
    } catch (e) { setError(e instanceof Error ? e.message : "Enregistrement impossible."); }
  };

  const remove = async (subject: Subject) => {
    if (!window.confirm(`Supprimer la matière ${subject.name} ?`)) return;
    try { await deleteSubject(schoolId, subject.id); setSubjects((current) => current.filter((item) => item.id !== subject.id)); }
    catch (e) { setError(e instanceof Error ? e.message : "Suppression impossible."); }
  };

  const closeNewCategory = () => {
    setShowNewCategory(false);
    setNewCategoryError("");
    setNewCategoryName("");
  };

  // Création depuis le formulaire de matière : le nouveau type est sélectionné
  // aussitôt, pour que la saisie en cours puisse continuer sans détour.
  const createCategoryInline = async () => {
    const name = newCategoryName.trim();
    if (name.length < 2) {
      setNewCategoryError("Saisissez un nom d’au moins 2 caractères.");
      return;
    }
    setNewCategoryError("");
    try {
      const created = await createSubjectCategory(schoolId, {
        name,
      });
      setCategories((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name)));
      setSelectedCategory(String(created.id));
      closeNewCategory();
      setMessage(`Type « ${created.name} » créé et sélectionné.`);
    } catch (e) {
      setNewCategoryError(e instanceof Error ? e.message : "Création impossible.");
    }
  };

  const saveCategory = async () => {
    if (!editingCategory) return;
    const name = editCategoryName.trim();
    if (name.length < 2) {
      setError("Le nom du type doit contenir au moins 2 caractères.");
      return;
    }
    setError(""); setMessage("");
    try {
      const updated = await updateSubjectCategory(schoolId, editingCategory.id, {
        name,
      });
      setCategories((current) => current
        .map((item) => item.id === updated.id ? updated : item)
        .sort((a, b) => a.name.localeCompare(b.name)));
      // Le nom affiché dans la colonne « Type » suit le renommage.
      setSubjects((current) => current.map((item) =>
        item.category === updated.id ? { ...item, category_name: updated.name } : item));
      setEditingCategory(null);
      setMessage("Type de matière modifié.");
    } catch (e) { setError(e instanceof Error ? e.message : "Modification impossible."); }
  };

  const removeCategory = async (category: SubjectCategory) => {
    const warning = category.subject_count > 0
      ? `Supprimer le type « ${category.name} » ? Les ${category.subject_count} matière(s) classées ici ne seront pas supprimées, elles perdront simplement leur type.`
      : `Supprimer le type « ${category.name} » ?`;
    if (!window.confirm(warning)) return;
    try {
      await deleteSubjectCategory(schoolId, category.id);
      setCategories((current) => current.filter((item) => item.id !== category.id));
      setSubjects((current) => current.map((item) =>
        item.category === category.id ? { ...item, category: null, category_name: null } : item));
      if (selectedCategory === String(category.id)) setSelectedCategory("");
      setMessage("Type supprimé.");
    } catch (e) { setError(e instanceof Error ? e.message : "Suppression impossible."); }
  };

  return <div className="content-inner">
    <div className="page-header"><h1 className="page-title">Matières</h1>
      <div className="actions-cell">
        <button className="subject-edit-btn" onClick={() => setShowCategories(true)}>Gérer les types</button>
        <button className="btn-primary" onClick={() => { setEditing(null); setSelectedCategory(""); setShowForm(true); }}>Ajouter une matière</button>
      </div>
    </div>
    {error && <div className="form-error">{error}</div>}{message && <div className="form-success">{message}</div>}

    <div className="toolbar">
      <div className="search-box"><span>⌕</span><input className="search-input" value={search}
        onChange={(event) => setSearch(event.target.value)} placeholder="Rechercher une matière" /></div>
      <select className="form-select subject-filter" value={categoryFilter}
        onChange={(event) => setCategoryFilter(event.target.value)}>
        <option value="">Tous les types</option>
        {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
        <option value="none">Sans type</option>
      </select>
    </div>

    {filtered.length === 0 ? <div className="empty-state"><p className="empty-title">Aucune matière pour le moment</p></div> :
      <div className="teachers-table-wrap"><table className="teachers-table">
        <thead><tr><th>Nom</th><th>Code</th><th>Type</th><th>Description</th><th>Actions</th></tr></thead>
        <tbody>{filtered.map((subject) => <tr key={subject.id}>
          <td><strong>{subject.name}</strong></td>
          <td>{subject.code}</td>
          <td>{subject.category_name || "—"}</td>
          <td>{subject.description || "—"}</td>
          <td><div className="actions-cell">
            <button className="subject-edit-btn" onClick={() => { setEditing(subject); setSelectedCategory(String(subject.category ?? "")); setShowForm(true); }}>Modifier</button>
            <button className="subject-delete-btn" onClick={() => void remove(subject)}>Supprimer</button>
          </div></td></tr>)}</tbody></table></div>}

    {showForm && <div className="teacher-modal-backdrop" onMouseDown={() => setShowForm(false)}>
      <form className="teacher-modal subject-form" onSubmit={submit} onMouseDown={(event) => event.stopPropagation()}>
        <button type="button" className="modal-close" onClick={() => setShowForm(false)}>×</button>
        <h2>{editing ? "Modifier la matière" : "Ajouter une matière"}</h2>
        <label>Nom *<input className="form-input" name="name" defaultValue={editing?.name} required /></label>
        <label>Code *<input className="form-input" name="code" defaultValue={editing?.code} placeholder="ex: mathematiques" required /></label>
        <label>Type de matière
          <div className="subject-category-row">
            <select
              className="form-select" name="category" value={selectedCategory}
              onChange={(event) => setSelectedCategory(event.target.value)}
            >
              <option value="">Aucun</option>
              {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
            </select>
            <button type="button" className="subject-edit-btn" onClick={() => setShowNewCategory(true)}>
              + Nouveau type
            </button>
          </div>
        </label>
        <label>Description<textarea className="form-input subject-description" name="description" defaultValue={editing?.description} /></label>
        <button className="btn-primary" type="submit">Enregistrer</button>
      </form></div>}

    {showNewCategory && <div className="teacher-modal-backdrop subject-modal-stacked" onMouseDown={closeNewCategory}>
      <div className="teacher-modal subject-category-modal" onMouseDown={(event) => event.stopPropagation()}>
        <button type="button" className="modal-close" onClick={closeNewCategory}>×</button>
        <h2>Nouveau type de matière</h2>
        {newCategoryError && <div className="form-error">{newCategoryError}</div>}
        <label>Nom du type *<input
          className="form-input" value={newCategoryName} placeholder="ex: Matière scientifique"
          onChange={(event) => setNewCategoryName(event.target.value)}
          onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void createCategoryInline(); } }}
          autoFocus
        /></label>
        <div className="actions-cell">
          <button type="button" className="subject-edit-btn" onClick={closeNewCategory}>Annuler</button>
          <button type="button" className="btn-primary" onClick={() => void createCategoryInline()}>Créer le type</button>
        </div>
      </div></div>}

    {showCategories && <div className="teacher-modal-backdrop" onMouseDown={() => setShowCategories(false)}>
      <div className="teacher-modal" onMouseDown={(event) => event.stopPropagation()}>
        <button type="button" className="modal-close" onClick={() => setShowCategories(false)}>×</button>
        <h2>Types de matières</h2>
        <p className="parents-empty">
          Créez vos propres catégories : matière facultative, littéraire, scientifique… Elles servent à classer
          et filtrer les matières. Leur ordre sur le bulletin se règle dans le paramétrage des bulletins.
        </p>
        {categories.length === 0
          ? <p className="parents-empty">Aucun type pour le moment.</p>
          : <table className="owners-table">
              <thead><tr><th>Nom</th><th>Matières</th><th></th></tr></thead>
              <tbody>{categories.map((category) => editingCategory?.id === category.id
                ? <tr key={category.id}>
                    <td><input
                      className="form-input" value={editCategoryName} autoFocus
                      onChange={(event) => setEditCategoryName(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") { event.preventDefault(); void saveCategory(); }
                        if (event.key === "Escape") setEditingCategory(null);
                      }}
                    /></td>
                    <td>{category.subject_count}</td>
                    <td><div className="actions-cell">
                      <button className="btn-primary" onClick={() => void saveCategory()}>Enregistrer</button>
                      <button className="subject-edit-btn" onClick={() => setEditingCategory(null)}>Annuler</button>
                    </div></td>
                  </tr>
                : <tr key={category.id}>
                    <td>{category.name}</td>
                    <td>{category.subject_count}</td>
                    <td><div className="actions-cell">
                      <button className="subject-edit-btn" onClick={() => {
                        setEditingCategory(category);
                        setEditCategoryName(category.name);
                      }}>Modifier</button>
                      <button className="subject-delete-btn" onClick={() => void removeCategory(category)}>Supprimer</button>
                    </div></td>
                  </tr>)}</tbody>
            </table>}
        <div className="actions-cell subject-category-footer">
          <button type="button" className="btn-primary" onClick={() => setShowNewCategory(true)}>
            + Nouveau type
          </button>
        </div>
      </div></div>}
  </div>;
}
