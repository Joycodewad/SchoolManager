import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { listParents, Parent, ParentList } from "../api/parents";

export default function Parents() {
  const { schoolId = "" } = useParams();
  const [data, setData] = useState<ParentList | null>(null);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Parent | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    listParents(schoolId)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Chargement impossible."))
      .finally(() => setLoading(false));
  }, [schoolId]);

  const parents = useMemo(() => {
    const term = search.trim().toLowerCase();
    const rows = data?.parents ?? [];
    if (!term) return rows;
    return rows.filter((parent) =>
      `${parent.last_name} ${parent.first_names} ${parent.phone ?? ""}`.toLowerCase().includes(term)
      || parent.children.some((child) => child.name.toLowerCase().includes(term)),
    );
  }, [data, search]);

  const withoutGuardian = (data?.students_total ?? 0) - (data?.students_with_guardian ?? 0);

  return <div className="content-inner parents-page">
    <div className="page-header"><h1 className="page-title">Parents et tuteurs</h1></div>
    {error && <div className="form-error">{error}</div>}

    <div className="parents-stats">
      <article className="parents-stat"><span className="parents-stat-value">{data?.parents.length ?? 0}</span><span className="parents-stat-label">Parents enregistrés</span></article>
      <article className="parents-stat"><span className="parents-stat-value">{data?.students_with_guardian ?? 0}</span><span className="parents-stat-label">Élèves avec tuteur</span></article>
      <article className="parents-stat"><span className="parents-stat-value">{withoutGuardian}</span><span className="parents-stat-label">Élèves sans tuteur</span></article>
    </div>

    <div className="parents-toolbar">
      <input
        className="form-input"
        placeholder="Rechercher un parent, un téléphone ou un élève…"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />
    </div>

    {loading
      ? <p className="parents-empty">Chargement…</p>
      : parents.length === 0
        ? <p className="parents-empty">
            {data?.parents.length === 0
              ? "Aucun parent n’est encore rattaché à un élève. Les tuteurs sont renseignés lors de l’inscription des élèves."
              : "Aucun résultat pour cette recherche."}
          </p>
        : <table className="parents-table">
            <thead><tr><th>Nom</th><th>Prénoms</th><th>Téléphone</th><th>Profession</th><th>Enfants</th><th></th></tr></thead>
            <tbody>{parents.map((parent) => <tr key={parent.id}>
              <td>{parent.last_name}</td>
              <td>{parent.first_names}</td>
              <td>{parent.phone || "—"}</td>
              <td>{parent.profession || "—"}</td>
              <td>{parent.children.length}</td>
              <td><button className="school-edit-btn" type="button" onClick={() => setSelected(parent)}>Détails</button></td>
            </tr>)}</tbody>
          </table>}

    {selected && <div className="teacher-modal-backdrop" onMouseDown={() => setSelected(null)}>
      <div className="teacher-modal" onMouseDown={(event) => event.stopPropagation()}>
        <button type="button" className="modal-close" onClick={() => setSelected(null)}>×</button>
        <h2>{selected.last_name} {selected.first_names}</h2>
        <dl className="parents-details">
          <div><dt>Identifiant</dt><dd>{selected.username}</dd></div>
          <div><dt>Téléphone</dt><dd>{selected.phone || "—"}</dd></div>
          <div><dt>Email</dt><dd>{selected.email || "—"}</dd></div>
          <div><dt>Profession</dt><dd>{selected.profession || "—"}</dd></div>
          <div><dt>Adresse</dt><dd>{selected.address || "—"}</dd></div>
        </dl>
        <h3 className="parents-children-title">Enfants ({selected.children.length})</h3>
        <table className="parents-table">
          <thead><tr><th>Matricule</th><th>Élève</th><th>Classe</th></tr></thead>
          <tbody>{selected.children.map((child) => <tr key={child.enrollment_id}>
            <td>{child.matricule}</td><td>{child.name}</td><td>{child.class_name ?? "—"}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </div>}
  </div>;
}
