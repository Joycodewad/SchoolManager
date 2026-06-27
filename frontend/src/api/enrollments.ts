const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api";

export interface Enrollment {
  id: number;
  enrollment_number: string;
  student: number;
  student_name: string;
  student_username: string;
  gender_label: string;
  date_of_birth_display: string;
  level: number;
  level_name: string;
  level_stage: string;
  status: string;
  enrolled_at: string;
}

export interface EnrollmentPayload {
  enrollment_number: string;
  last_name: string;
  first_names: string;
  gender: "M" | "F";
  date_of_birth: string;
  address?: string;
  level: number;
}

export interface SchoolLevel {
  id: number;
  name: string;
  stage: "primaire" | "college" | "lycee";
  stage_label: string;
  order: number;
}

export interface EnrollmentImportResult {
  message: string;
  count: number;
  enrollments: Enrollment[];
}

const headers = () => {
  const year = JSON.parse(localStorage.getItem("active_academic_year") || "null");
  return { "Content-Type": "application/json", Authorization: `Token ${localStorage.getItem("auth_token") ?? ""}`,
    ...(year?.id ? { "X-Academic-Year-ID": String(year.id) } : {}) };
};

const parse = async (response: Response) => {
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = Object.entries(data ?? {}).map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(" ") : errors}`).join(" — ");
    throw new Error(message || "Une erreur est survenue.");
  }
  return data;
};

export const listEnrollments = (schoolId: string): Promise<Enrollment[]> =>
  fetch(`${API_URL}/schools/${schoolId}/enrollments/`, { headers: headers() }).then(parse);
export const createEnrollment = (schoolId: string, payload: EnrollmentPayload): Promise<Enrollment> =>
  fetch(`${API_URL}/schools/${schoolId}/enrollments/`, { method: "POST", headers: headers(), body: JSON.stringify(payload) }).then(parse);
export const cancelEnrollment = (schoolId: string, id: number): Promise<void> =>
  fetch(`${API_URL}/schools/${schoolId}/enrollments/${id}/`, { method: "DELETE", headers: headers() }).then(parse);
export const listSchoolLevels = (schoolId: string): Promise<SchoolLevel[]> =>
  fetch(`${API_URL}/schools/${schoolId}/levels/`, { headers: headers() }).then(parse);
export const suggestEnrollmentNumber = async (schoolId: string): Promise<string> => {
  const data = await fetch(`${API_URL}/schools/${schoolId}/enrollments/suggest-number/`, { headers: headers() }).then(parse);
  return data.enrollment_number;
};

export const importEnrollments = (schoolId: string, file: File): Promise<EnrollmentImportResult> => {
  const year = JSON.parse(localStorage.getItem("active_academic_year") || "null");
  const form = new FormData();
  form.append("file", file);
  return fetch(`${API_URL}/schools/${schoolId}/enrollments/import/`, {
    method: "POST",
    headers: {
      Authorization: `Token ${localStorage.getItem("auth_token") ?? ""}`,
      ...(year?.id ? { "X-Academic-Year-ID": String(year.id) } : {}),
    },
    body: form,
  }).then(parse);
};
