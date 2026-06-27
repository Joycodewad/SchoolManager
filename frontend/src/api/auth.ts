const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api";

export interface School {
  id: number;
  username: string;
  name: string;
  code: string;
  user_role: string;
  logo?: string | null;
}

export interface AuthUser {
  id: number;
  first_names: string;
  last_name: string;
  phone?: string | null;
  role: string;
  role_label: string;
  is_superuser: boolean;
}

export interface LoginResponse {
  token: string;
  user: AuthUser;
  schools: School[];
}

export async function loginUser(username: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_URL}/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.message || "Nom d’utilisateur ou mot de passe incorrect.");
  return data;
}

export async function logoutUser(token: string): Promise<void> {
  await fetch(`${API_URL}/auth/logout/`, {
    method: "POST",
    headers: { Authorization: `Token ${token}` },
  });
}

export async function fetchSchools(token: string): Promise<School[]> {
  const response = await fetch(`${API_URL}/schools/`, {
    headers: { Authorization: `Token ${token}` },
  });
  const data = await response.json().catch(() => ([]));
  if (!response.ok) throw new Error("Impossible de charger les écoles.");
  return Array.isArray(data) ? data : data.results ?? [];
}
