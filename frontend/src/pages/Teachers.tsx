import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Delete, Edit, Visibility } from "@mui/icons-material";
import {
  deleteTeacher,
  listTeachers,
  Teacher,
  TeacherPayload,
  updateTeacher,
} from "../api/teachers";

const AVATAR_COLORS = ["#dbeafe", "#fce7f3", "#d1fae5", "#fef3c7", "#ede9fe"];
const TEXT_COLORS = ["#1d4ed8", "#be185d", "#065f46", "#92400e", "#5b21b6"];

const fullName = (teacher: Teacher) => `${teacher.last_name} ${teacher.first_names}`.trim();
const initials = (teacher: Teacher) =>
  `${teacher.last_name[0] ?? ""}${teacher.first_names[0] ?? ""}`.toUpperCase();
const subjects = (teacher: Teacher) =>
  [teacher.primary_subject, teacher.secondary_subject, teacher.tertiary_subject]
    .filter(Boolean)
    .join(", ") || "Aucune";

export default function Teachers() {
  const navigate = useNavigate();
  const { schoolId } = useParams();
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [search, setSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Teacher | null>(null);
  const [editing, setEditing] = useState<Teacher | null>(null);
  const [saving, setSaving] = useState(false);
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

  const handleEdit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editing) return;
    const form = new FormData(event.currentTarget);
    const payload: Partial<TeacherPayload> = {
      last_name: String(form.get("last_name") ?? "").trim(),
      first_names: String(form.get("first_names") ?? "").trim(),
      email: String(form.get("email") ?? "").trim(),
      phone: String(form.get("phone") ?? "").trim(),
      gender: String(form.get("gender")) as "M" | "F",
      primary_subject: String(form.get("primary_subject") ?? "").trim(),
      secondary_subject: String(form.get("secondary_subject") ?? "").trim(),
      tertiary_subject: String(form.get("tertiary_subject") ?? "").trim(),
    };
    setSaving(true);
    setError("");
    try {
      const updated = await updateTeacher(editing.id, payload);
      setTeachers((current) => current.map((item) => item.id === updated.id ? updated : item));
      setEditing(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "La modification a échoué.");
    } finally {
      setSaving(false);
    }
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
            <thead><tr><th>Nom</th><th>Rôle</th><th>Matières</th><th>Classe</th><th>Email</th><th>Numéro</th><th>Genre</th><th>Actions</th></tr></thead>
            <tbody>
              {paginated.map((teacher, index) => (
                <tr key={teacher.id} className={index % 2 ? "row-alt" : ""}>
                  <td><div className="teacher-name-cell"><div className="teacher-avatar" style={{ background: AVATAR_COLORS[index % 5], color: TEXT_COLORS[index % 5] }}>{initials(teacher)}</div>{fullName(teacher)}</div></td>
                  <td>{teacher.role_label}</td>
                  <td>{subjects(teacher)}</td>
                  <td><span className="class-unassigned">Non assignée</span></td>
                  <td>{teacher.email || "—"}</td>
                  <td>{teacher.phone || "—"}</td>
                  <td>{teacher.gender_label || "—"}</td>
                  <td><div className="actions-cell">
                    <button className="action-btn view-btn" title="Voir" onClick={() => setSelected(teacher)}><Visibility fontSize="small" /></button>
                    <button className="action-btn edit-btn" title="Modifier" onClick={() => setEditing(teacher)}><Edit fontSize="small" /></button>
                    <button className="btn-assign" title="Assigner une classe" onClick={() => window.alert("La gestion des classes sera disponible prochainement.")}>Assigner</button>
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
        <div className="teacher-modal" onMouseDown={(event) => event.stopPropagation()}>
          <button className="modal-close" onClick={() => setSelected(null)}>×</button>
          <h2>{fullName(selected)}</h2>
          <dl className="teacher-details"><dt>Matières</dt><dd>{subjects(selected)}</dd><dt>Classe</dt><dd>Non assignée</dd><dt>Email</dt><dd>{selected.email || "—"}</dd><dt>Numéro</dt><dd>{selected.phone}</dd><dt>Genre</dt><dd>{selected.gender_label}</dd></dl>
        </div>
      </div>}

      {editing && <div className="teacher-modal-backdrop">
        <form className="teacher-modal teacher-edit-form" onSubmit={handleEdit}>
          <button type="button" className="modal-close" onClick={() => setEditing(null)}>×</button>
          <h2>Modifier l’enseignant</h2>
          <label>Nom<input name="last_name" className="form-input" defaultValue={editing.last_name} required /></label>
          <label>Prénoms<input name="first_names" className="form-input" defaultValue={editing.first_names} required /></label>
          <label>Email<input name="email" type="email" className="form-input" defaultValue={editing.email} /></label>
          <label>Numéro<input name="phone" className="form-input" defaultValue={editing.phone} required /></label>
          <label>Genre<select name="gender" className="form-select" defaultValue={editing.gender}><option value="M">Masculin</option><option value="F">Féminin</option></select></label>
          <label>Matière principale<input name="primary_subject" className="form-input" defaultValue={editing.primary_subject} /></label>
          <label>Matière secondaire<input name="secondary_subject" className="form-input" defaultValue={editing.secondary_subject} /></label>
          <label>Matière tertiaire<input name="tertiary_subject" className="form-input" defaultValue={editing.tertiary_subject} /></label>
          <button className="btn-primary" type="submit" disabled={saving}>{saving ? "Enregistrement…" : "Enregistrer"}</button>
        </form>
      </div>}
    </div>
  );
}
