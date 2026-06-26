import { useState } from "react";
import { useNavigate } from "react-router-dom";
// import LoginCSS from "../styles/Login.css";
export default function Login() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState(null);

  const validate = () => {
    const errs = {};
    if (!formData.email) errs.email = "L'email est requis.";
    else if (!/\S+@\S+\.\S+/.test(formData.email))
      errs.email = "Format d'email invalide.";
    if (!formData.password) errs.password = "Le mot de passe est requis.";
    else if (formData.password.length < 6)
      errs.password = "Minimum 6 caractères.";
    return errs;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: "" }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) {
      setErrors(errs);
      return;
    }

    setLoading(true);
    setAlert(null);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/v1/users/login/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setAlert({
          type: "success",
          msg: "Connexion réussie ! Redirection en cours…",
        });
        
        // Store token if provided
        if (data.access) {
          localStorage.setItem("auth_access_token", data.access);
        }

        if(data.refresh) {
          localStorage.setItem("auth_refresh_token", data.refresh);
        }

        if (data.user) {
          localStorage.setItem("auth_user", JSON.stringify(data.user));
        }
        
        // Redirect to dashboard after a short delay
        setTimeout(() => {
          navigate("/dashboard");
        }, 1000);
      } else {
        const error = await response.json();
        setLoading(false);
        setAlert({
          type: "error",
          msg: error.message || "Email ou mot de passe incorrect. Veuillez réessayer.",
        });
      }
    } catch (error) {
      setLoading(false);
      setAlert({
        type: "error",
        msg: "Erreur de connexion. Veuillez vérifier l'URL du serveur et réessayer.",
      });
      console.error("Login error:", error);
    }
  };

  return (
    <>
      <div className="login-root">
        {/* ── LEFT ── */}
        <div className="login-left">
          <div className="noise-overlay" />

          {/* // Place une image de fond ici, par exemple il doit couvrir toute la partie gauche et être légèrement floutée pour ne pas gêner la lecture du texte: */}
            <img
                src="https://images.unsplash.com/photo-1504384308090-c894fdcc538d?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8bGFwdG9wJTIwcGFyfGVufDB8fDB8fHww&auto=format&fit=crop&w=800&q=60" 
                alt="Background"
                className="background-image"
            />
        </div>

        {/* ── RIGHT ── */}
        <div className="login-right">
          <div className="form-container">
            <div className="form-header">
              <p>
                Pas encore de compte ? <a href="/register">Créez-en un</a>
              </p>
            </div>

            {alert && (
              <div className={`alert alert-${alert.type}`}>
                <span>{alert.type === "error" ? "⚠️" : "✅"}</span>
                {alert.msg}
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate>
              {/* Email */}
              <div className="field">
                <label htmlFor="email">Adresse email</label>
                <div className="input-wrap">
                  <span className="input-icon">
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <rect x="2" y="4" width="20" height="16" rx="3" />
                      <path d="m2 7 10 7 10-7" />
                    </svg>
                  </span>
                  <input
                    id="email"
                    type="email"
                    name="email"
                    placeholder="vous@exemple.com"
                    value={formData.email}
                    onChange={handleChange}
                    autoComplete="email"
                  />
                </div>
                {errors.email && (
                  <p className="field-error">⚠ {errors.email}</p>
                )}
              </div>

              {/* Password */}
              <div className="field">
                <label htmlFor="password">Mot de passe</label>
                <div className="input-wrap">
                  <span className="input-icon">
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <rect x="3" y="11" width="18" height="11" rx="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  </span>
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    name="password"
                    placeholder="••••••••"
                    value={formData.password}
                    onChange={handleChange}
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    className="toggle-password"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label="Afficher/masquer le mot de passe"
                  >
                    {showPassword ? (
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                        <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                        <line x1="1" y1="1" x2="23" y2="23" />
                      </svg>
                    ) : (
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    )}
                  </button>
                </div>
                {errors.password && (
                  <p className="field-error">⚠ {errors.password}</p>
                )}
              </div>

              {/* Options */}
              <div className="options-row">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                  />
                  Se souvenir de moi
                </label>
                <a href="/forgot-password" className="forgot-link">
                  Mot de passe oublié ?
                </a>
              </div>

              {/* Submit */}
              <button type="submit" className="btn-submit" disabled={loading}>
                {loading ? (
                  <>
                    <span className="spinner" />
                    Connexion…
                  </>
                ) : (
                  "Se connecter"
                )}
              </button>
            </form>

            {/* OAuth */}
            <div className="divider">ou continuer avec</div>
            <div className="oauth-grid">
              <button type="button" className="btn-oauth">
                <svg viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                Google
              </button>
              <button type="button" className="btn-oauth">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z" />
                </svg>
                GitHub
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
