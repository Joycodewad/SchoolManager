const API_URL = import.meta.env.VITE_API_URL ?? "/api";
export interface Enrollment {
  id: number;
  enrollment_number: string;
  student: number;
  student_name: string;
  student_last_name: string;
  student_first_names: string;
  student_gender: "M" | "F";
  student_username: string;
  student_address: string;
  gender_label: string;
  date_of_birth_display: string;
  level: number;
  level_name: string;
  level_stage: string;
  school_class: number | null;
  school_class_name: string | null;
  school_class_series: string | null;
  academic_year_name: string;
  history: EnrollmentHistory[];
  status: string;
  enrolled_at: string;
}
export interface EnrollmentHistory { id: number; academic_year: string; level: string | null; school_class: string | null; status: string; enrolled_at: string; }

export interface EnrollmentPayload {
  enrollment_number: string;
  last_name: string;
  first_names: string;
  gender: "M" | "F";
  date_of_birth: string;
  address?: string;
  level: number;
  school_class?: number | null;
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
    if (Array.isArray(data?.errors)) {
      const details = data.errors.map((row: { ligne?: number; erreurs?: Record<string, unknown> }) => {
        const fields = Object.entries(row.erreurs ?? {}).map(([field, value]) => {
          const text = Array.isArray(value) ? value.join(" ") : String(value);
          return `${field}: ${text}`;
        }).join(" ; ");
        return `Ligne ${row.ligne ?? "?"} — ${fields}`;
      }).join("\n");
      throw new Error(`${data.message ?? "Le fichier contient des erreurs."}\n${details}`);
    }
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
export const getEnrollment = (schoolId: string, id: number): Promise<Enrollment> =>
  fetch(`${API_URL}/schools/${schoolId}/enrollments/${id}/`, { headers: headers() }).then(parse);
export const updateEnrollment = (schoolId: string, id: number, payload: Partial<EnrollmentPayload>): Promise<Enrollment> =>
  fetch(`${API_URL}/schools/${schoolId}/enrollments/${id}/`, { method: "PATCH", headers: headers(), body: JSON.stringify(payload) }).then(parse);
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
