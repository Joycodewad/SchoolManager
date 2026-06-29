const API_URL = import.meta.env.VITE_API_URL ?? "/api";
const headers = () => {
  const year = JSON.parse(localStorage.getItem("active_academic_year") || "null");
  return { "Content-Type": "application/json", Authorization: `Token ${localStorage.getItem("auth_token") ?? ""}`, ...(year?.id ? { "X-Academic-Year-ID": String(year.id) } : {}) };
};
const parse = async (response: Response) => {
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) { const message = Object.entries(data ?? {}).map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(" ") : value}`).join(" — "); throw new Error(message || "Une erreur est survenue."); }
  return data;
};
export interface GradeLine { id: number; name: string; weight: string | null; max_score: string; order: number; }
export interface GradeGroup { id: number; name: string; weight: string | null; order: number; lines: GradeLine[]; }
export interface GradeScheme { id: number; session: number; calculation_method: "equal" | "weighted" | "groups"; method_label: string; lines: GradeLine[]; groups: GradeGroup[]; }
export interface GradeContext { can_configure: boolean; sessions: Array<{ id: number; name: string; label: string; classes: Array<{ id: number; name: string; subjects: Array<{ id: number; name: string }> }> }> }
export interface GradeSheet { scheme: GradeScheme; class_subject: { id: number; subject: string }; students: Array<{ enrollment: number; matricule: string; student_name: string; scores: Record<string, string>; average: string | null }> }
export interface GradeSchemePayload { calculation_method: "equal" | "weighted" | "groups"; lines: Array<{ name: string; weight: number | null; max_score: number; order: number }>; groups: Array<{ name: string; weight: number; order: number; lines: Array<{ name: string; weight: number; max_score: number; order: number }> }> }
const base = (schoolId: string) => `${API_URL}/schools/${schoolId}/grades`;
export const getGradeContexts = (schoolId: string): Promise<GradeContext> => fetch(`${base(schoolId)}/contexts/`, { headers: headers() }).then(parse);
export const getGradeScheme = (schoolId: string, sessionId: number): Promise<GradeScheme | null> => fetch(`${base(schoolId)}/sessions/${sessionId}/scheme/`, { headers: headers() }).then(parse);
export const saveGradeScheme = (schoolId: string, sessionId: number, payload: GradeSchemePayload): Promise<GradeScheme> => fetch(`${base(schoolId)}/sessions/${sessionId}/scheme/`, { method: "PUT", headers: headers(), body: JSON.stringify(payload) }).then(parse);
export const getGradeSheet = (schoolId: string, sessionId: number, classSubjectId: number): Promise<GradeSheet> => fetch(`${base(schoolId)}/sessions/${sessionId}/subjects/${classSubjectId}/`, { headers: headers() }).then(parse);
export const saveGrades = (schoolId: string, sessionId: number, classSubjectId: number, grades: Array<{ enrollment: number; line: number; score: number }>): Promise<GradeSheet> => fetch(`${base(schoolId)}/sessions/${sessionId}/subjects/${classSubjectId}/`, { method: "POST", headers: headers(), body: JSON.stringify({ grades }) }).then(parse);
