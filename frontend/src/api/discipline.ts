const API_URL = import.meta.env.VITE_API_URL ?? "/api";

const headers = () => {
  const year = JSON.parse(localStorage.getItem("active_academic_year") || "null");
  return {
    "Content-Type": "application/json",
    Authorization: `Token ${localStorage.getItem("auth_token") ?? ""}`,
    ...(year?.id ? { "X-Academic-Year-ID": String(year.id) } : {}),
  };
};

const parse = async (response: Response) => {
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = Object.entries(data ?? {}).map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(" ") : value}`).join(" — ");
    throw new Error(message || "Une erreur est survenue.");
  }
  return data;
};

export interface DisciplineStudent {
  id: number;
  enrollment_number: string;
  student_name: string;
  class_name: string;
  level_name: string;
}

export interface DisciplineRecord {
  id: number;
  enrollment: number;
  student_name: string;
  enrollment_number: string;
  class_name: string | null;
  entry_type: "retard" | "absence" | "incident";
  entry_type_label: string;
  occurred_on: string;
  late_hours: string;
  incident_type: string;
  severity: "leger" | "moyen" | "grave" | "";
  severity_label: string;
  description: string;
  action_taken: string;
  recorded_by_name: string;
  created_at: string;
}

export interface DisciplineResponse {
  students: DisciplineStudent[];
  records: DisciplineRecord[];
  summary: { total_late_hours: string; total_absence_hours: string; absence_count: number; incident_count: number; record_count: number };
}

export interface DisciplinePayload {
  enrollment: number;
  entry_type: "retard" | "absence" | "incident";
  occurred_on: string;
  late_hours?: number;
  incident_type?: string;
  severity?: "leger" | "moyen" | "grave" | "";
  description?: string;
  action_taken?: string;
}

const base = (schoolId: string) => `${API_URL}/schools/${schoolId}/discipline/records/`;

export const listDisciplineRecords = (schoolId: string, enrollment?: number, entryType?: string): Promise<DisciplineResponse> => {
  const params = new URLSearchParams();
  if (enrollment) params.set("enrollment", String(enrollment));
  if (entryType) params.set("entry_type", entryType);
  const query = params.toString();
  return fetch(`${base(schoolId)}${query ? `?${query}` : ""}`, { headers: headers() }).then(parse);
};

export const createDisciplineRecord = (schoolId: string, payload: DisciplinePayload): Promise<DisciplineRecord> =>
  fetch(base(schoolId), { method: "POST", headers: headers(), body: JSON.stringify(payload) }).then(parse);
