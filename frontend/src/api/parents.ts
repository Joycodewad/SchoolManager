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

export interface ParentChild {
  enrollment_id: number;
  student_id: number;
  name: string;
  matricule: string;
  class_name: string | null;
  level: string | null;
}

export interface Parent {
  id: number;
  username: string;
  last_name: string;
  first_names: string;
  phone: string | null;
  email: string | null;
  profession: string;
  address: string;
  children: ParentChild[];
}

export interface ParentList {
  parents: Parent[];
  students_total: number;
  students_with_guardian: number;
}

export async function listParents(schoolId: string | number): Promise<ParentList> {
  return parse(await fetch(`${API_URL}/schools/${schoolId}/parents/`, { headers: headers() }));
}
