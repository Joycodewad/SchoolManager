import { useState, type ChangeEvent, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { loginUser } from "../api/auth";
import { useAuth } from "../hooks/AuthContext";

function UserIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4.1 3.6-7 8-7s8 2.9 8 7" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="5" y="10" width="14" height="11" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
      <path d="M12 14v3" />
    </svg>
  );
}

function EyeIcon({ open }: { open: boolean }) {
  return open ? (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M3 3l18 18" />
      <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8" />
      <path d="M9.9 4.2A10.6 10.6 0 0 1 12 4c6.1 0 10 8 10 8a17.6 17.6 0 0 1-3.1 4.1" />
      <path d="M6.1 6.1C3.9 7.6 2 10.3 2 12c0 0 3.9 8 10 8 1.7 0 3.2-.5 4.5-1.2" />
    </svg>
  ) : (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M2 12s3.9-8 10-8 10 8 10 8-3.9 8-10 8S2 12 2 12Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [formData, setFormData] = useState({ username: "", password: "" });
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target;
    setFormData((current) => ({ ...current, [name]: value }));
    if (error) setError("");
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!formData.username.trim() || !formData.password) {
      setError("Veuillez saisir votre nom d'utilisateur et votre mot de passe.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const data = await loginUser(formData.username, formData.password);
      login(data);
      navigate(data.schools[0] ? `/schools/${data.schools[0].id}/dashboard` : "/schools");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Connexion impossible. Réessayez.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="login-title">
        <div className="login-avatar" aria-hidden="true"><UserIcon /></div>
        <h1 id="login-title" className="sr-only">Connexion</h1>
        {error && <p className="login-error" role="alert">{error}</p>}

        <form className="login-form" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="username">Nom d'utilisateur</label>
          <div className="login-input">
            <UserIcon />
            <input id="username" name="username" type="text" placeholder="Username" value={formData.username} onChange={handleChange} autoComplete="username" autoFocus required />
          </div>

          <label className="sr-only" htmlFor="password">Mot de passe</label>
          <div className="login-input login-input--password">
            <LockIcon />
            <input id="password" name="password" type={showPassword ? "text" : "password"} placeholder="Password" value={formData.password} onChange={handleChange} autoComplete="current-password" required />
            <button
              type="button"
              className="password-toggle"
              onClick={() => setShowPassword((current) => !current)}
              aria-label={showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"}
            >
              <EyeIcon open={showPassword} />
            </button>
          </div>

          <div className="login-options">
            <label className="remember-me">
              <input type="checkbox" checked={rememberMe} onChange={(event) => setRememberMe(event.target.checked)} />
              Remember me
            </label>
            <a href="/forgot-password">Forgot Password?</a>
          </div>
          <button type="submit" className="login-submit" disabled={loading}>
            {loading ? "Connexion..." : "Login"}
          </button>
        </form>
      </section>
    </main>
  );
}
