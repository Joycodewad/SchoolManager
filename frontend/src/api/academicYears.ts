const API_URL = import.meta.env.VITE_API_URL ?? "/api";
export interface AcademicYear {
  id: number;
  school: number;
  name: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  is_closed: boolean;
  sessions: AcademicSession[];
}
export interface AcademicSession { id: number; academic_year: number; name: string; label: string; start_date: string; end_date: string; classes: number[]; class_names: string[]; is_active: boolean; is_closed: boolean; created_at: string; }
export interface AcademicSessionPayload { name: string; label: string; start_date: string; end_date: string; classes: number[]; is_active?: boolean; }

export interface AcademicYearPayload {
  name: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
}

const call = async (schoolId: number | string, path = "", options: RequestInit = {}) => {
  const response = await fetch(`${API_URL}/schools/${schoolId}/academic-years/${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", Authorization: `Token ${localStorage.getItem("auth_token") ?? ""}`, ...options.headers },
  });
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = Object.values(data ?? {}).flat().join(" ") || "Une erreur est survenue.";
    throw new Error(message);
  }
  return data;
};

export const listAcademicYears = (schoolId: number | string): Promise<AcademicYear[]> => call(schoolId);
export const createAcademicYear = (schoolId: number | string, payload: AcademicYearPayload): Promise<AcademicYear> =>
  call(schoolId, "", { method: "POST", body: JSON.stringify(payload) });
export const updateAcademicYear = (schoolId: number | string, id: number, payload: Partial<AcademicYearPayload>): Promise<AcademicYear> =>
  call(schoolId, `${id}/`, { method: "PATCH", body: JSON.stringify(payload) });
export const deleteAcademicYear = (schoolId: number | string, id: number): Promise<void> =>
  call(schoolId, `${id}/`, { method: "DELETE" });
export const closeAcademicYear = (schoolId: number | string, id: number): Promise<AcademicYear> =>
  call(schoolId, `${id}/close/`, { method: "POST" });
export const createAcademicSession = (schoolId: number | string, yearId: number, payload: AcademicSessionPayload): Promise<AcademicSession> =>
  call(schoolId, `${yearId}/sessions/`, { method: "POST", body: JSON.stringify(payload) });
export const updateAcademicSession = (schoolId: number | string, yearId: number, id: number, payload: Partial<AcademicSessionPayload>): Promise<AcademicSession> =>
  call(schoolId, `${yearId}/sessions/${id}/`, { method: "PATCH", body: JSON.stringify(payload) });
export const deleteAcademicSession = (schoolId: number | string, yearId: number, id: number): Promise<void> =>
  call(schoolId, `${yearId}/sessions/${id}/`, { method: "DELETE" });
export const closeAcademicSession = (schoolId: number | string, yearId: number, id: number): Promise<AcademicSession> =>
  call(schoolId, `${yearId}/sessions/${id}/close/`, { method: "POST" });
