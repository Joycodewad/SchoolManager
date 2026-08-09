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

export interface ReportCardSubject {
  class_subject_id: number;
  subject: string;
  coefficient: string;
  weekly_hours: number;
  average: string | null;
}

export interface ReportCardStudent {
  enrollment_id: number;
  matricule: string;
  student_name: string;
  subjects: ReportCardSubject[];
  general_average: string | null;
  rank: number | null;
}

export interface ReportCards {
  session: { id: number; name: string; label: string };
  school_class: { id: number; name: string; group: string };
  students: ReportCardStudent[];
  statistics: {
    students_total: number;
    students_graded: number;
    class_average: string | null;
    highest: string | null;
    lowest: string | null;
    pass_count: number;
  };
}

export async function getReportCards(
  schoolId: string | number,
  sessionId: number,
  classId: number,
): Promise<ReportCards> {
  return parse(await fetch(
    `${API_URL}/schools/${schoolId}/report-cards/sessions/${sessionId}/classes/${classId}/`,
    { headers: headers() },
  ));
}

// ── Génération, paramétrage et édition PDF ──

export interface ReportCardStatus {
  session: { id: number; name: string; label: string };
  generated: boolean;
  total: number;
  classes: Array<{ id: number; name: string; level: string; count: number; generated_at: string | null }>;
  can_configure: boolean;
}

export interface ReportCardAppreciation { id?: number; label: string; minimum: string }

export interface CategoryOrderRule {
  id?: number;
  name: string;
  /** Portée : tout l'établissement, un cycle, une série ou des classes. */
  scope: "ecole" | "cycle" | "serie" | "classes";
  scope_label?: string;
  stage: string;
  series: string;
  classes: number[];
  class_names?: string[];
  /** Noms des types de matières, du premier bloc au dernier. */
  categories: string[];
}

/** Disposition imprimée du bulletin. */
export type ReportCardTemplate = "standard" | "officiel";

/** Marque de fond imprimée derrière le bulletin. Elles se cumulent. */
export type ReportCardWatermark = "mosaique" | "diagonale" | "logo";
/** Serrage du motif en mosaïque. */
export type WatermarkDensity = "normale" | "pleine" | "max";
export type WatermarkSource = "nom" | "code";

export interface ReportCardSettings {
  template: ReportCardTemplate;
  templates: Array<{ value: ReportCardTemplate; label: string }>;
  /** Filigranes cochés : vide pour aucun, plusieurs pour un fond combiné. */
  watermarks: ReportCardWatermark[];
  watermark_density: WatermarkDensity;
  watermark_source: WatermarkSource;
  watermark_choices: Array<{ value: ReportCardWatermark; label: string }>;
  watermark_densities: Array<{ value: WatermarkDensity; label: string }>;
  watermark_sources: Array<{ value: WatermarkSource; label: string }>;
  /**
   * Le paramétrage a-t-il déjà été enregistré ? Tant que non, les valeurs
   * affichées sont celles d'usage et peuvent encore être complétées
   * automatiquement ; après le premier enregistrement, plus rien n'y touche.
   */
  is_configured: boolean;
  show_score_detail: boolean;
  group_by_category: boolean;
  show_rank: boolean;
  show_teacher: boolean;
  show_appreciation: boolean;
  show_class_statistics: boolean;
  council_note: string;
  appreciations: ReportCardAppreciation[];
  school: {
    name: string;
    /** Code de l'établissement, repris par le filigrane. Non modifiable ici. */
    code: string;
    /** Un logo est-il chargé ? Conditionne le filigrane « logo ». */
    logo: boolean;
    /** Mentions officielles imprimées en tête du bulletin. */
    country: string; country_motto: string; ministry: string;
    cabinet: string; general_secretariat: string;
    education_direction: string; direction_city: string; inspection: string;
    /** Coordonnées de l'établissement. */
    motto: string; phone: string; postal_box: string; city: string;
  };
  can_configure: boolean;
  category_orders: CategoryOrderRule[];
  categories: Array<{ id: number; name: string }>;
  stages: Array<{ value: string; label: string }>;
  series: string[];
}

export const getReportCardStatus = (schoolId: string | number, sessionId: number): Promise<ReportCardStatus> =>
  fetch(`${API_URL}/schools/${schoolId}/report-cards/sessions/${sessionId}/generate/`, { headers: headers() }).then(parse);

/** `scope` : "school" à la première génération, "class" ou "student" pour corriger. */
export const generateReportCards = (
  schoolId: string | number, sessionId: number,
  payload: { scope: "school" | "class" | "student"; school_class?: number; enrollment?: number },
): Promise<{ detail: string; written: number }> =>
  fetch(`${API_URL}/schools/${schoolId}/report-cards/sessions/${sessionId}/generate/`,
    { method: "POST", headers: headers(), body: JSON.stringify(payload) }).then(parse);

export const getReportCardSettings = (schoolId: string | number): Promise<ReportCardSettings> =>
  fetch(`${API_URL}/schools/${schoolId}/report-cards/settings/`, { headers: headers() }).then(parse);

export const saveReportCardSettings = (
  schoolId: string | number, payload: Partial<ReportCardSettings>,
): Promise<ReportCardSettings> =>
  fetch(`${API_URL}/schools/${schoolId}/report-cards/settings/`,
    { method: "PUT", headers: headers(), body: JSON.stringify(payload) }).then(parse);

/** Télécharge le PDF ; en cas d'erreur le corps reste du JSON, qu'on relit. */
export async function downloadReportCards(
  schoolId: string | number, sessionId: number,
  scope: "school" | "class" | "student",
  target?: number,
): Promise<void> {
  const query = new URLSearchParams({ scope });
  if (scope === "class" && target) query.set("school_class", String(target));
  if (scope === "student" && target) query.set("enrollment", String(target));

  const response = await fetch(
    `${API_URL}/schools/${schoolId}/report-cards/sessions/${sessionId}/export/?${query}`,
    { headers: headers() },
  );
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const message = Object.entries(data ?? {})
      .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(" ") : value}`).join(" — ");
    throw new Error(message || "Le PDF n’a pas pu être généré.");
  }
  const blob = await response.blob();
  const filename = response.headers.get("Content-Disposition")?.match(/filename="(.+)"/)?.[1] ?? "bulletins.pdf";
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url; link.download = filename;
  document.body.appendChild(link); link.click(); link.remove();
  URL.revokeObjectURL(url);
}
