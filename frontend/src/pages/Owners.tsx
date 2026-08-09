import { FormEvent, useEffect, useState } from "react";
import { AuthUser } from "../api/auth";
import { archiveOwner, createOwner, createSchool, listOwners, updateOwner } from "../api/schools";
import { useAuth } from "../hooks/AuthContext";

export default function Owners() {
  const { user, addSchool } = useAuth();
  const [owners, setOwners] = useState<AuthUser[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [editingOwner, setEditingOwner] = useState<AuthUser | null>(null);

  const loadOwners = () => listOwners().then(setOwners).catch((e) => setError(e.message));

  useEffect(() => {
    if (user?.is_superuser) void loadOwners();
  }, [user]);

  if (user && !user.is_superuser) {
    return <div className="content-inner"><div className="form-error">Cette page est réservée aux superutilisateurs.</div></div>;
  }

  const submitOwner = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(""); setMessage("");
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const username = String(form.get("username")).trim();
    try {
      const owner = await createOwner({
        username,
        last_name: String(form.get("last_name")).trim(),
        first_names: String(form.get("first_names")).trim(),
        phone: String(form.get("phone")),
        email: String(form.get("email")),
      });
      setOwners((current) => [...current, owner]);
      formElement.reset();
      setMessage(`Propriétaire créé. Identifiant : ${username} — mot de passe initial : ${username}@`);
    } catch (e) { setError(e instanceof Error ? e.message : "Création impossible."); }
  };

  const submitEditOwner = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editingOwner) return;
    setError(""); setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      const owner = await updateOwner(editingOwner.id, {
        last_name: String(form.get("last_name")).trim(),
        first_names: String(form.get("first_names")).trim(),
        phone: String(form.get("phone")),
        email: String(form.get("email")),
      });
      setOwners((current) => current.map((item) => (item.id === owner.id ? owner : item)));
      setEditingOwner(null);
      setMessage("Propriétaire modifié avec succès.");
    } catch (e) { setError(e instanceof Error ? e.message : "Modification impossible."); }
  };

  const removeOwner = async (owner: AuthUser) => {
    if (!window.confirm(`Archiver ${owner.last_name} ${owner.first_names} ? Ce propriétaire ne pourra plus se connecter.`)) return;
    setError(""); setMessage("");
    try {
      await archiveOwner(owner.id);
      setOwners((current) => current.filter((item) => item.id !== owner.id));
      setMessage("Propriétaire archivé.");
    } catch (e) { setError(e instanceof Error ? e.message : "Archivage impossible."); }
  };

  const submitSchool = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(""); setMessage("");
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      const school = await createSchool({
        name: String(form.get("name")).trim(),
        code: String(form.get("code")).trim(),
        owner: Number(form.get("owner")),
        ...(form.get("logo") instanceof File && (form.get("logo") as File).size > 0
          ? { logo: form.get("logo") as File } : {}),
      });
      addSchool(school); formElement.reset(); setMessage("Établissement créé avec succès.");
    } catch (e) { setError(e instanceof Error ? e.message : "Création impossible."); }
  };

  return <div className="content-inner owners-page">
    <div className="page-header"><h1 className="page-title">Gestion des propriétaires</h1></div>
    {error && <div className="form-error">{error}</div>}{message && <div className="form-success">{message}</div>}

    <section className="school-panel">
      <h2>Propriétaires enregistrés</h2>
      {owners.length === 0
        ? <p className="owners-empty">Aucun propriétaire enregistré pour le moment.</p>
        : <table className="owners-table">
            <thead><tr><th>Nom</th><th>Prénoms</th><th>Identifiant</th><th>Téléphone</th><th>Actions</th></tr></thead>
            <tbody>{owners.map((owner) => <tr key={owner.id}>
              <td>{owner.last_name}</td>
              <td>{owner.first_names}</td>
              <td>{owner.username}</td>
              <td>{owner.phone || "—"}</td>
              <td className="owners-actions">
                <button className="school-edit-btn" type="button" onClick={() => setEditingOwner(owner)}>Modifier</button>
                <button className="owner-archive-btn" type="button" onClick={() => removeOwner(owner)}>Archiver</button>
              </td>
            </tr>)}</tbody>
          </table>}
    </section>

    <section className="school-panel"><h2>Créer un propriétaire</h2><form className="school-form" onSubmit={submitOwner}>
      <label>Nom d’utilisateur<input className="form-input" name="username" pattern="\S+" title="Aucun espace n’est autorisé" required /></label>
      <label>Nom<input className="form-input" name="last_name" required /></label>
      <label>Prénoms<input className="form-input" name="first_names" required /></label>
      <label>Téléphone<input className="form-input" name="phone" defaultValue="+228" required /></label>
      <label>Email<input className="form-input" name="email" type="email" /></label>
      <button className="btn-primary" type="submit">Créer le propriétaire</button>
    </form></section>

    <section className="school-panel"><h2>Créer un établissement</h2><form className="school-form" onSubmit={submitSchool}>
      <label>Nom de l’école<input className="form-input" name="name" required /></label>
      <label>Code unique<input className="form-input" name="code" placeholder="ex: ekd-lome" required /></label>
      <label>Logo de l’école<input className="form-input school-logo-input" name="logo" type="file" accept="image/png,image/jpeg,image/webp" /></label>
      <label>Propriétaire<select className="form-select" name="owner" required><option value="">Choisir</option>
        {owners.map((owner) => <option key={owner.id} value={owner.id}>{owner.last_name} {owner.first_names}</option>)}</select></label>
      <button className="btn-primary" type="submit">Créer l’établissement</button>
    </form></section>

    {editingOwner && <div className="teacher-modal-backdrop" onMouseDown={() => setEditingOwner(null)}>
      <form className="teacher-modal school-edit-modal" onSubmit={submitEditOwner} onMouseDown={(event) => event.stopPropagation()}>
        <button type="button" className="modal-close" onClick={() => setEditingOwner(null)}>×</button>
        <h2>Modifier le propriétaire</h2>
        <label>Nom<input className="form-input" name="last_name" defaultValue={editingOwner.last_name} required /></label>
        <label>Prénoms<input className="form-input" name="first_names" defaultValue={editingOwner.first_names} required /></label>
        <label>Téléphone<input className="form-input" name="phone" defaultValue={editingOwner.phone ?? ""} /></label>
        <label>Email<input className="form-input" name="email" type="email" defaultValue={editingOwner.email ?? ""} /></label>
        <button className="btn-primary" type="submit">Enregistrer les modifications</button>
      </form>
    </div>}
  </div>;
}
