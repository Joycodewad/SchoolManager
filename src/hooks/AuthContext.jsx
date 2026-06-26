import { createContext, useContext, useState } from "react";

// Valeur par défaut — évite le null si utilisé hors Provider
const AuthContext = createContext({
  user: null,
  login: () => {},
  logout: async () => {},
  getAccessToken: () => null,
  isAuthenticated: false,
});

// ─── URL de base — change selon ton environnement ───────────────────
const API_BASE = "http://127.0.0.1:8000/api/v1/users"; // adapte si besoin

export function AuthProvider({ children }) {
  // On stocke access + refresh token dans localStorage
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("auth_user");
    return saved ? JSON.parse(saved) : null;
  });

//   // ── Login ─────────────────────────────────────────────────────────
//   // Appelle ton endpoint existant, stocke les deux tokens
  const login = (userData, tokens) => {
    localStorage.setItem("auth_user", JSON.stringify(userData));
    localStorage.setItem("auth_access_token", tokens.access);
    localStorage.setItem("auth_refresh_token", tokens.refresh);
    setUser(userData);
  };

  // ── Logout ────────────────────────────────────────────────────────
  const logout = async () => {
    const accessToken = localStorage.getItem("auth_access_token");
    const refreshToken = localStorage.getItem("auth_refresh_token");

    // 1. Appel API pour blacklister le refresh token côté serveur
    try {
      const response = await fetch(`${API_BASE}/logout/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`, // access token requis
        },
        body: JSON.stringify({ refresh: refreshToken }), // body attendu par ton API
      });

      if (!response.ok) {
        const data = await response.json();
        console.warn("Logout API error:", data.detail);
      }
    } catch (err) {
      // Erreur réseau — on déconnecte quand même localement
      console.error("Erreur réseau lors du logout:", err);
    } finally {
      // 2. Nettoyage local — toujours exécuté, même si l'API échoue
      localStorage.removeItem("auth_user");
      localStorage.removeItem("auth_access_token");
      localStorage.removeItem("auth_refresh_token");
      setUser(null);
    }
  };

  // ── Helpers ───────────────────────────────────────────────────────
  const getAccessToken = () => localStorage.getItem("auth_access_token");

  return (
    <AuthContext.Provider
      value={{
        user,
        // login,
        logout,
        getAccessToken,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// Garde — lève une erreur claire si utilisé hors AuthProvider
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth doit être utilisé dans un <AuthProvider>");
  return context;
}
