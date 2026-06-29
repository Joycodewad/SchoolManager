const API_URL = import.meta.env.VITE_API_URL ?? "/api";
const authHeaders = () => {
  const token = localStorage.getItem("auth_token");
  const school = JSON.parse(localStorage.getItem("active_school") || "null");
  const academicYear = JSON.parse(localStorage.getItem("active_academic_year") || "null");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Token ${token}` } : {}),
    ...(school?.id ? { "X-School-ID": String(school.id) } : {}),
    ...(academicYear?.id ? { "X-Academic-Year-ID": String(academicYear.id) } : {}),
  };
};

const teachersUrl = () => {
  const school = JSON.parse(localStorage.getItem("active_school") || "null");
  if (!school?.id) throw new Error("Sélectionnez une école.");
  return `${API_URL}/schools/${school.id}/teachers`;
};

export interface TeacherPayload {
  username: string;
  last_name: string;
  first_names: string;
  email?: string;
  phone: string;
  gender: "M" | "F";
  subjects?: number[];
  primary_subject?: number | null;
  school_ids?: number[];
  role: string;
}

export interface RoleOption { value: string; label: string; }
export interface TeacherUnavailability {
  id?: number; day: number; day_label?: string; all_day: boolean;
  start_time: string | null; end_time: string | null;
}
export interface TeacherAssignments {
  assignments: { class_id: number; subject_ids: number[] }[];
  unavailable_subjects: { class_id: number; subject_id: number; teacher_name: string }[];
}

export interface Teacher extends TeacherPayload {
  id: number;
  gender_label: string;
  role: string;
  role_label: string;
  is_active: boolean;
  is_archived: boolean;
  date_joined: string;
  subject_names: string[];
  primary_subject_name: string | null;
  assigned_school_ids: number[];
  assigned_classes: { id: number; name: string; subjects: string[]; weekly_hours: number }[];
  homeroom_classes: { id: number; name: string }[];
  unavailability_schedule: TeacherUnavailability[];
  date_of_birth: string | null;
  address: string;
}

export class TeacherApiError extends Error {
  fieldErrors: Record<string, string>;

  constructor(message: string, fieldErrors: Record<string, string>) {
    super(message);
    this.name = "TeacherApiError";
    this.fieldErrors = fieldErrors;
  }
}

export async function suggestUsername(lastName: string, firstNames: string): Promise<string> {
  const params = new URLSearchParams({ last_name: lastName, first_names: firstNames });
  const response = await fetch(`${API_URL}/usernames/suggest/?${params}`, { headers: authHeaders() });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error("Impossible de générer le nom d’utilisateur.");
  return data.username ?? "";
}

export async function listRoles(): Promise<RoleOption[]> {
  const response = await fetch(`${API_URL}/roles/`, { headers: authHeaders() });
  const data = await response.json().catch(() => ([]));
  if (!response.ok) throw new Error("Impossible de charger les rôles.");
  return data;
}

async function parseResponse(response: Response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const labels: Record<string, string> = {
      email: "Courriel",
      phone: "Téléphone",
      gender: "Genre",
      non_field_errors: "Erreur",
    };
    const fieldErrors = Object.fromEntries(
      Object.entries(data).map(([field, errors]) => [
        field,
        Array.isArray(errors) ? errors.join(" ") : String(errors),
      ]),
    );
    const message = Object.entries(fieldErrors)
      .map(([field, error]) => `${labels[field] ?? field}: ${error}`)
      .join(" — ");
    throw new TeacherApiError(
      message || "Impossible d’enregistrer l’enseignant.",
      fieldErrors,
    );
  }

  return data;
}

export async function listTeachers(): Promise<Teacher[]> {
  const response = await fetch(`${teachersUrl()}/`, { headers: authHeaders() });
  const data = await parseResponse(response);
  return Array.isArray(data) ? data : data.results ?? [];
}

export async function getTeacher(id: number): Promise<Teacher> {
  const response = await fetch(`${teachersUrl()}/${id}/`, { headers: authHeaders() });
  return parseResponse(response);
}

export async function createTeacher(teacher: TeacherPayload): Promise<Teacher> {
  const response = await fetch(`${teachersUrl()}/`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(teacher),
  });
  return parseResponse(response);
}

export async function updateTeacher(id: number, teacher: Partial<TeacherPayload>): Promise<Teacher> {
  const response = await fetch(`${teachersUrl()}/${id}/`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(teacher),
  });
  return parseResponse(response);
}

export async function deleteTeacher(id: number): Promise<void> {
  const response = await fetch(`${teachersUrl()}/${id}/`, { method: "DELETE", headers: authHeaders() });
  if (!response.ok) await parseResponse(response);
}

export async function getTeacherAssignments(id: number): Promise<TeacherAssignments> {
  const response = await fetch(`${teachersUrl()}/${id}/classes/`, { headers: authHeaders() });
  return parseResponse(response);
}
export async function saveTeacherAssignments(id: number, assignments: { class_id: number; subject_ids: number[] }[]): Promise<void> {
  const response = await fetch(`${teachersUrl()}/${id}/classes/`, { method: "POST", headers: authHeaders(), body: JSON.stringify({ assignments }) });
  await parseResponse(response);
}
export async function getTeacherUnavailability(id: number): Promise<TeacherUnavailability[]> {
  const response = await fetch(`${teachersUrl()}/${id}/unavailability/`, { headers: authHeaders() });
  return parseResponse(response);
}
export async function saveTeacherUnavailability(id: number, slots: TeacherUnavailability[]): Promise<void> {
  const response = await fetch(`${teachersUrl()}/${id}/unavailability/`, { method: "POST", headers: authHeaders(), body: JSON.stringify({ slots }) });
  await parseResponse(response);
}
