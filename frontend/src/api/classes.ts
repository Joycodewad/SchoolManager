const API_URL = import.meta.env.VITE_API_URL ?? "/api";
export interface SchoolClass {
  id: number; name: string; level: number; level_name: string;
  cycle: "primaire" | "college" | "lycee"; cycle_label: string;
  series: string; group: string; is_active: boolean;
  homeroom_teacher: number | null; homeroom_teacher_name: string | null;
  subjects: ClassSubjectConfiguration[];
  effectif: number;
}
export interface ClassSubjectConfiguration {
  id?: number; subject: number; subject_name?: string; weekly_hours: number; coefficient: string | number;
  can_schedule_after_break: boolean; can_schedule_afternoon: boolean;
}
export interface SchoolClassPayload {
  level: number; series: string; group: string;
  homeroom_teacher?: number | null;
  subjects?: ClassSubjectConfiguration[];
}

const request = async (schoolId: string, path = "", options: RequestInit = {}) => {
  const year = JSON.parse(localStorage.getItem("active_academic_year") || "null");
  const response = await fetch(`${API_URL}/schools/${schoolId}/classes/${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", Authorization: `Token ${localStorage.getItem("auth_token") ?? ""}`,
      ...(year?.id ? { "X-Academic-Year-ID": String(year.id) } : {}), ...options.headers },
  });
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = Object.entries(data ?? {}).map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(" ") : errors}`).join(" — ");
    throw new Error(message || "Une erreur est survenue.");
  }
  return data;
};

export const listClasses = (schoolId: string): Promise<SchoolClass[]> => request(schoolId);
export const createClass = (schoolId: string, payload: SchoolClassPayload): Promise<SchoolClass> => request(schoolId, "", { method: "POST", body: JSON.stringify(payload) });
export const updateClass = (schoolId: string, id: number, payload: Partial<SchoolClassPayload>): Promise<SchoolClass> => request(schoolId, `${id}/`, { method: "PATCH", body: JSON.stringify(payload) });
export const deleteClass = (schoolId: string, id: number): Promise<void> => request(schoolId, `${id}/`, { method: "DELETE" });
