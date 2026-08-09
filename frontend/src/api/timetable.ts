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

export interface TimetableSlot {
  id: number;
  class_id: number;
  class_name: string;
  level: string;
  subject: string;
  subject_code: string;
  teacher: string | null;
  teacher_id: number | null;
  day: number;
  day_label: string;
  start_time: string;
  end_time: string;
}

export interface TimetablePeriod {
  id: number;
  label: string;
  kind: "cours" | "pause";
  kind_label: string;
  start_time: string;
  end_time: string;
  order: number;
}

export interface SubjectRestriction {
  id?: number;
  subject: number;
  subject_name?: string;
  period: number;
  day: number | null;
}

/** Un groupe de classes rattachées à une matière : réunion ou exclusion. */
export interface SubjectClassSet {
  id?: number;
  subject: number;
  subject_name?: string;
  classes: number[];
  class_names?: string[];
}

export type ClassGroup = SubjectClassSet;

export interface TimetableOptions {
  enforce_paired_hours: boolean;
  enforce_single_hour_middle: boolean;
  enforce_day_spacing: boolean;
  enforce_max_two_hours: boolean;
  skip_primary: boolean;
}

export interface Timetable {
  id: number;
  status: "brouillon" | "valide";
  status_label: string;
  is_validated: boolean;
  days_per_week: number;
  period_duration: number;
  generated_at: string;
  validated_at: string | null;
  options: TimetableOptions;
  days_without_afternoon: number[];
  max_class_hours: number;
  periods: TimetablePeriod[];
  restrictions: SubjectRestriction[];
  excluded_classes: SubjectClassSet[];
  class_groups: ClassGroup[];
  slots: TimetableSlot[];
}

export interface TimetableResponse {
  timetable: Timetable | null;
  can_manage: boolean;
  unplaced?: string[];
  relaxed?: Array<{ constraint: string; classes: string[] }>;
  attempts?: number;
  irreducible?: number;
  overloaded_classes?: Record<string, number>;
}

export interface TimetableSetup {
  timetable: Timetable;
  subjects: Array<{ id: number; name: string; code: string }>;
  classes: Array<{ id: number; name: string; level: string }>;
  /** "classId-subjectId" -> enseignant qui assure la matière dans cette classe. */
  class_subject_teachers: Record<string, { id: number; name: string }>;
  can_manage: boolean;
}

export interface SetupPayload extends Partial<TimetableOptions> {
  days_per_week?: number;
  days_without_afternoon?: number[];
  periods?: Array<{ id?: number; label: string; kind: string; start_time: string; end_time: string }>;
  restrictions?: Array<{ subject: number; period: number; day: number | null }>;
  excluded_classes?: Array<{ subject: number; classes: number[] }>;
  class_groups?: Array<{ subject: number; classes: number[] }>;
}

export async function getTimetableSetup(schoolId: string | number): Promise<TimetableSetup> {
  return parse(await fetch(`${API_URL}/schools/${schoolId}/timetable/setup/`, { headers: headers() }));
}

export async function saveTimetableSetup(
  schoolId: string | number,
  payload: SetupPayload,
): Promise<Timetable> {
  return parse(await fetch(`${API_URL}/schools/${schoolId}/timetable/setup/`, {
    method: "PUT", headers: headers(), body: JSON.stringify(payload),
  }));
}

export async function getTimetable(schoolId: string | number): Promise<TimetableResponse> {
  return parse(await fetch(`${API_URL}/schools/${schoolId}/timetable/`, { headers: headers() }));
}

export async function generateTimetable(
  schoolId: string | number,
  payload: { days_per_week?: number; period_duration?: number } = {},
): Promise<TimetableResponse> {
  return parse(await fetch(`${API_URL}/schools/${schoolId}/timetable/`, {
    method: "POST", headers: headers(), body: JSON.stringify(payload),
  }));
}

export async function validateTimetable(schoolId: string | number): Promise<Timetable> {
  return parse(await fetch(`${API_URL}/schools/${schoolId}/timetable/validate/`, {
    method: "POST", headers: headers(), body: "{}",
  }));
}

export async function deleteTimetable(schoolId: string | number): Promise<void> {
  await parse(await fetch(`${API_URL}/schools/${schoolId}/timetable/`, {
    method: "DELETE", headers: headers(),
  }));
}

export interface MyTimetable {
  timetable: { id: number; is_validated: boolean; days_per_week: number } | null;
  /** "mine" = les cours de l'utilisateur ; "all" = toutes les classes. */
  scope: "mine" | "all";
  can_manage?: boolean;
  periods: TimetablePeriod[];
  slots: Array<{
    id: number; class_id: number; class_name: string; level: string;
    subject: string; teacher?: string | null; teacher_id?: number | null;
    day: number; day_label: string;
    start_time: string; end_time: string;
  }>;
}

/**
 * Emploi du temps consulté sans droit de gestion.
 *
 * `scope: "all"` demande la vue générale ; le serveur la refuse aux non-gestionnaires
 * et renvoie alors leurs propres cours (le champ `scope` de la réponse fait foi).
 */
export async function getMyTimetable(
  schoolId: string | number,
  scope: "mine" | "all" = "mine",
): Promise<MyTimetable> {
  const query = scope === "all" ? "?scope=all" : "";
  return parse(await fetch(`${API_URL}/schools/${schoolId}/timetable/mine/${query}`, { headers: headers() }));
}

/**
 * Télécharge le PDF. `ids` vide demande tout le périmètre autorisé.
 *
 * La réponse est un fichier, pas du JSON : en cas d'erreur le corps reste du
 * JSON, qu'on relit pour afficher le message du serveur.
 */
export async function downloadTimetablePdf(
  schoolId: string | number,
  scope: "classes" | "teachers",
  ids: number[] = [],
): Promise<void> {
  const query = new URLSearchParams({ scope });
  if (ids.length) query.set("ids", ids.join(","));

  const response = await fetch(
    `${API_URL}/schools/${schoolId}/timetable/export/?${query}`,
    { headers: headers() },
  );

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const message = Object.entries(data ?? {})
      .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(" ") : value}`)
      .join(" — ");
    throw new Error(message || "Le PDF n’a pas pu être généré.");
  }

  const blob = await response.blob();
  const filename = response.headers.get("Content-Disposition")?.match(/filename="(.+)"/)?.[1]
    ?? "emploi-du-temps.pdf";

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
