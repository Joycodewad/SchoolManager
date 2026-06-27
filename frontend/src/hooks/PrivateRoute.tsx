import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

// Protège toutes les routes qui nécessitent d'être connecté
export default function PrivateRoute({ children }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/" replace />;
}