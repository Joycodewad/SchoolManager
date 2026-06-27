import { FormEvent, useEffect, useState } from "react";
import { AuthUser, School } from "../api/auth";
import { createOwner, createSchool, listOwners, updateSchool } from "../api/schools";
import { useAuth } from "../hooks/AuthContext";

export default function Schools() {
  const { user, schools, addSchool, updateSchoolInContext } = useAuth();
  const [owners, setOwners] = useState<AuthUser[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [editingSchool, setEditingSchool] = useState<School | null>(null);

  useEffect(() => {
    if (user?.is_superuser) listOwners().then(setOwners).catch((e) => setError(e.message));
  }, [user]);

  if (user && user.role !== "proprietaire" && !user.is_superuser) {
    return <div className="content-inner"><div className="form-error">Cette page est réservée aux propriétaires et superutilisateurs.</div></div>;
  }

  const submitSchool = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(""); setMessage("");
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      const school = await createSchool({
        name: String(form.get("name")).trim(), code: String(form.get("code")).trim(),
        ...(user?.is_superuser ? { owner: Number(form.get("owner")) } : {}),
        ...(form.get("logo") instanceof File && (form.get("logo") as File).size > 0
          ? { logo: form.get("logo") as File } : {}),
      });
      addSchool(school); formElement.reset(); setMessage("École créée avec succès.");
    } catch (e) { setError(e instanceof Error ? e.message : "Création impossible."); }
  };

  const submitOwner = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(""); setMessage("");
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      const owner = await createOwner({ username: String(form.get("username")), last_name: String(form.get("last_name")),
        first_names: String(form.get("first_names")), phone: String(form.get("phone")), email: String(form.get("email")) });
      setOwners((current) => [...current, owner]); formElement.reset(); setMessage("Propriétaire créé avec succès.");
    } catch (e) { setError(e instanceof Error ? e.message : "Création impossible."); }
  };

  const submitEditSchool = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editingSchool) return;
    setError(""); setMessage("");
    const form = new FormData(event.currentTarget);
    const logo = form.get("logo");
    try {
      const school = await updateSchool(editingSchool.id, {
        name: String(form.get("name")).trim(),
        code: String(form.get("code")).trim(),
        ...(logo instanceof File && logo.size > 0 ? { logo } : {}),
      });
      updateSchoolInContext(school);
      setEditingSchool(null);
      setMessage("École modifiée avec succès.");
    } catch (e) { setError(e instanceof Error ? e.message : "Modification impossible."); }
  };

  return <div className="content-inner schools-page">
    <div className="page-header"><h1 className="page-title">Vue d’ensemble des écoles</h1></div>
    {error && <div className="form-error">{error}</div>}{message && <div className="form-success">{message}</div>}
    <div className="school-cards">{schools.map((school) => <article className="school-card" key={school.id}>
      {school.logo ? <img className="school-card-logo" src={school.logo} alt={`Logo de ${school.name}`} /> : <span className="school-card-icon">▦</span>}
      <div className="school-card-content"><h3>{school.name}</h3><p>Code : {school.code}</p><small>{school.user_role}</small></div>
      <button className="school-edit-btn" type="button" onClick={() => setEditingSchool(school)}>Modifier</button>
    </article>)}</div>

    <section className="school-panel"><h2>Créer une nouvelle école</h2><form className="school-form" onSubmit={submitSchool}>
      <label>Nom de l’école<input className="form-input" name="name" required /></label>
      <label>Code unique<input className="form-input" name="code" placeholder="ex: ekd-lome" required /></label>
      <label>Logo de l’école<input className="form-input school-logo-input" name="logo" type="file" accept="image/png,image/jpeg,image/webp" /></label>
      {user?.is_superuser && <label>Propriétaire<select className="form-select" name="owner" required><option value="">Choisir</option>
        {owners.map((owner) => <option key={owner.id} value={owner.id}>{owner.last_name} {owner.first_names}</option>)}</select></label>}
      <button className="btn-primary" type="submit">Créer l’école</button>
    </form></section>

    {user?.is_superuser && <section className="school-panel"><h2>Créer un propriétaire</h2><form className="school-form" onSubmit={submitOwner}>
      <label>Nom d’utilisateur<input className="form-input" name="username" pattern="\S+" title="Aucun espace n’est autorisé" required /></label>
      <label>Nom<input className="form-input" name="last_name" required /></label><label>Prénoms<input className="form-input" name="first_names" required /></label>
      <label>Téléphone<input className="form-input" name="phone" defaultValue="+228" required /></label><label>Email<input className="form-input" name="email" type="email" /></label>
      <button className="btn-primary" type="submit">Créer le propriétaire</button>
    </form></section>}

    {editingSchool && <div className="teacher-modal-backdrop" onMouseDown={() => setEditingSchool(null)}>
      <form className="teacher-modal school-edit-modal" onSubmit={submitEditSchool} onMouseDown={(event) => event.stopPropagation()}>
        <button type="button" className="modal-close" onClick={() => setEditingSchool(null)}>×</button>
        <h2>Modifier l’école</h2>
        <label>Nom de l’école<input className="form-input" name="name" defaultValue={editingSchool.name} required /></label>
        <label>Code unique<input className="form-input" name="code" defaultValue={editingSchool.code} required /></label>
        {editingSchool.logo && <img className="school-edit-preview" src={editingSchool.logo} alt="Logo actuel" />}
        <label>Nouveau logo (optionnel)<input className="form-input school-logo-input" name="logo" type="file" accept="image/png,image/jpeg,image/webp" /></label>
        <button className="btn-primary" type="submit">Enregistrer les modifications</button>
      </form>
    </div>}
  </div>;
}
