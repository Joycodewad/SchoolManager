const API_URL = import.meta.env.VITE_API_URL ?? "/api";
export interface Subject {
  id: number;
  name: string;
  code: string;
  category: number | null;
  category_name?: string | null;
  description: string;
  is_active: boolean;
  created_at: string;
}

export interface SubjectPayload {
  name: string;
  code: string;
  category?: number | null;
  description?: string;
}

export interface SubjectCategory {
  id: number;
  name: string;
  subject_count: number;
  created_at: string;
}

const request = async (schoolId: string, path = "", options: RequestInit = {}) => {
  const response = await fetch(`${API_URL}/schools/${schoolId}/subjects/${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Token ${localStorage.getItem("auth_token") ?? ""}`,
      ...options.headers,
    },
  });
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = Object.entries(data ?? {}).map(([field, errors]) =>
      `${field}: ${Array.isArray(errors) ? errors.join(" ") : errors}`).join(" — ");
    throw new Error(message || "Une erreur est survenue.");
  }
  return data;
};

export const listSubjects = (schoolId: string): Promise<Subject[]> => request(schoolId);
export const createSubject = (schoolId: string, payload: SubjectPayload): Promise<Subject> =>
  request(schoolId, "", { method: "POST", body: JSON.stringify(payload) });
export const updateSubject = (schoolId: string, id: number, payload: SubjectPayload): Promise<Subject> =>
  request(schoolId, `${id}/`, { method: "PATCH", body: JSON.stringify(payload) });
export const deleteSubject = (schoolId: string, id: number): Promise<void> =>
  request(schoolId, `${id}/`, { method: "DELETE" });

const categoryRequest = async (schoolId: string, path = "", options: RequestInit = {}) => {
  const response = await fetch(`${API_URL}/schools/${schoolId}/subject-categories/${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Token ${localStorage.getItem("auth_token") ?? ""}`,
      ...options.headers,
    },
  });
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = Object.entries(data ?? {}).map(([field, errors]) =>
      `${field}: ${Array.isArray(errors) ? errors.join(" ") : errors}`).join(" — ");
    throw new Error(message || "Une erreur est survenue.");
  }
  return data;
};

export const listSubjectCategories = (schoolId: string): Promise<SubjectCategory[]> =>
  categoryRequest(schoolId);
export const createSubjectCategory = (schoolId: string, payload: { name: string }): Promise<SubjectCategory> =>
  categoryRequest(schoolId, "", { method: "POST", body: JSON.stringify(payload) });
export const updateSubjectCategory = (schoolId: string, id: number, payload: { name: string }): Promise<SubjectCategory> =>
  categoryRequest(schoolId, `${id}/`, { method: "PATCH", body: JSON.stringify(payload) });
export const deleteSubjectCategory = (schoolId: string, id: number): Promise<void> =>
  categoryRequest(schoolId, `${id}/`, { method: "DELETE" });
