const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api";

export interface AcademicPeriod {
  id: number;
  number: number;
  name: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  is_closed: boolean;
}

export interface AcademicYear {
  id: number;
  school: number;
  name: string;
  start_date: string;
  end_date: string;
  division_system: "trimestre" | "semestre";
  division_label: string;
  is_active: boolean;
  is_closed: boolean;
  periods: AcademicPeriod[];
}

export interface AcademicYearPayload {
  name: string;
  start_date: string;
  end_date: string;
  division_system: "trimestre" | "semestre";
  is_active: boolean;
  periods?: Array<{
    name: string;
    start_date: string;
    end_date: string;
    is_closed?: boolean;
  }>;
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
export const closeAcademicPeriod = (schoolId: number | string, yearId: number, periodId: number): Promise<AcademicPeriod> =>
  call(schoolId, `${yearId}/periods/${periodId}/close/`, { method: "POST" });
