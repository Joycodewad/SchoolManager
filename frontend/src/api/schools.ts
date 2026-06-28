import type { AuthUser, School } from "./auth";

const API_URL = import.meta.env.VITE_API_URL ?? "/api";
const headers = () => ({
  "Content-Type": "application/json",
  Authorization: `Token ${localStorage.getItem("auth_token") ?? ""}`,
});

async function parse(response: Response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = Object.values(data).flat().join(" ") || "Une erreur est survenue.";
    throw new Error(message);
  }
  return data;
}

export async function createSchool(payload: { name: string; code: string; owner?: number; logo?: File }): Promise<School> {
  const form = new FormData();
  form.append("name", payload.name.trim());
  form.append("code", payload.code.trim());
  if (payload.owner) form.append("owner", String(payload.owner));
  if (payload.logo) form.append("logo", payload.logo);
  return parse(await fetch(`${API_URL}/schools/`, {
    method: "POST",
    headers: { Authorization: `Token ${localStorage.getItem("auth_token") ?? ""}` },
    body: form,
  }));
}

export async function updateSchool(
  id: number,
  payload: { name: string; code: string; logo?: File },
): Promise<School> {
  const form = new FormData();
  form.append("name", payload.name.trim());
  form.append("code", payload.code.trim());
  if (payload.logo) form.append("logo", payload.logo);
  return parse(await fetch(`${API_URL}/schools/${id}/`, {
    method: "PATCH",
    headers: { Authorization: `Token ${localStorage.getItem("auth_token") ?? ""}` },
    body: form,
  }));
}

export async function listOwners(): Promise<AuthUser[]> {
  return parse(await fetch(`${API_URL}/owners/`, { headers: headers() }));
}

export async function createOwner(payload: {
  username: string; last_name: string; first_names: string; phone?: string; email?: string; gender?: string;
}): Promise<AuthUser> {
  return parse(await fetch(`${API_URL}/owners/`, {
    method: "POST", headers: headers(), body: JSON.stringify(payload),
  }));
}
