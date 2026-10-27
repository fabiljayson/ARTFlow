/**
 * Client HTTP pour l'API ArtFlow — C4.
 *
 * Toute la communication traverse le proxy Next (`/api/:path*` → Django), pour
 * que cookies de session et CSRF restent sur le même origine que le navigateur.
 *
 * Particularités verifiées empiriquement (cf. notes de session C4) :
 *  - Le proxy Next réécrit `/api/:path` vers `${Django}/api/:path` et réajoute le
 *    slash final que Django exige (APPEND_SLASH). On appelle donc l'API SANS slash
 *    final, ce qui est servi en 200 directement — sans boucle 308/301.
 *  - Django renvoie les URLs de médias en absolu (`http://127.0.0.1:8003/...`),
 *    ce qui contournerait le proxy. On les réécrit en relatif (`/api/v1/...`).
 *  - L'erreur API est enveloppée : `{"error": {"code","message","details"}}`.
 */

/**
 * Base API.
 *
 * Côté navigateur : le proxy Next (`/api/v1`), pour que cookies et CSRF restent
 * sur la même origine. Côté serveur (composants Server) : `fetch` ne sait pas
 * résoudre une URL relative, donc on pointe directement sur Django via
 * `API_PROXY_BASE` — la même variable que celle des rewrites de next.config.ts.
 */
export const API_BASE =
  typeof window === "undefined"
    ? (process.env.API_PROXY_BASE ?? "http://127.0.0.1:8003") + "/api/v1"
    : (process.env.NEXT_PUBLIC_API_BASE ?? "/api/v1");

/** Erreur API typée — porte le code HTTP et le code métier quand fournis. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly details: unknown;

  constructor(status: number, message: string, code?: string | null, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code ?? null;
    this.details = details ?? null;
  }
}

/** Lit le cookie CSRF posé par `GET /auth/csrf/` (double submit cookie). */
export function readCsrfToken(cookieString?: string): string | null {
  const source =
    cookieString ?? (typeof document === "undefined" ? "" : document.cookie);
  for (const part of source.split(";")) {
    const [rawName, ...rest] = part.trim().split("=");
    if (rawName === "csrftoken") {
      return decodeURIComponent(rest.join("="));
    }
  }
  return null;
}

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

type ErrorEnvelope = { code?: string; message?: string; details?: unknown };

async function parseError(res: Response): Promise<ApiError> {
  let envelope: ErrorEnvelope | null = null;
  try {
    const body: unknown = await res.json();
    if (body && typeof body === "object") {
      const wrapper = (body as { error?: unknown }).error;
      if (wrapper && typeof wrapper === "object") {
        envelope = wrapper as ErrorEnvelope;
      } else if ("detail" in (body as object)) {
        envelope = { message: String((body as { detail: unknown }).detail) };
      }
    }
  } catch {
    envelope = null;
  }
  const message = envelope?.message ?? `Erreur ${res.status}`;
  return new ApiError(res.status, message, envelope?.code, envelope?.details);
}

/** Appel API : credentials (cookies session) + CSRF double submit. */
export async function apiFetch<T>(
  path: string,
  init: RequestInit & { csrfToken?: string | null } = {},
): Promise<T> {
  const { csrfToken, headers, ...rest } = init;
  const method = (rest.method ?? "GET").toUpperCase();

  const finalHeaders = new Headers(headers);
  finalHeaders.set("Accept", "application/json");
  if (rest.body !== undefined && !(rest.body instanceof FormData)) {
    finalHeaders.set("Content-Type", "application/json");
  }
  if (UNSAFE_METHODS.has(method)) {
    const token = csrfToken ?? readCsrfToken();
    if (token) finalHeaders.set("X-CSRFToken", token);
  }

  // Pas de slash final : cf. en-tête du fichier.
  const url = `${API_BASE}${path.replace(/\/$/, "")}`;

  const res = await fetch(url, {
    ...rest,
    method,
    headers: finalHeaders,
    credentials: "include",
    cache: "no-store",
  });

  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  const data = (await res.json()) as T;

  // Les URLs de médias et de pagination reviennent en absolu depuis Django
  // (ex. http://127.0.0.1:8003/...), ce qui contournerait le proxy Next et donc
  // la session/CSRF. On les ramène en relatif (/api/v1/...).
  return normalizeApiUrls<T>(data);
}

/** Réécrit en relatif toute URL pointant sur l'API Django, dans un payload typé. */
function normalizeApiUrls<T>(data: T): T {
  if (Array.isArray(data)) {
    return data.map((item) => normalizeApiUrls(item)) as unknown as T;
  }
  if (data && typeof data === "object") {
    const out: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
      out[key] =
        (key === "url" || key.endsWith("_url") || key === "next" || key === "previous") &&
        typeof value === "string"
          ? proxiedUrl(value)
          : normalizeApiUrls(value);
    }
    return out as T;
  }
  return data;
}

/**
 * Réécrit une URL de média Django (absolue ou relative) en chemin proxifié.
 * Les URLs de médias passent par `/api/v1/catalog/artworks/.../{stream|thumb|poster}/`.
 */
export function proxiedUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url, "http://relative.invalid");
    if (parsed.origin === "http://relative.invalid") return url;
    return `${parsed.pathname}${parsed.search}`;
  } catch {
    return url;
  }
}

// ---------------------------------------------------------------------------
// Types — miroir exact des serializers du backend (apps/catalogue/serializers.py)
// ---------------------------------------------------------------------------

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type ArtworkStatus =
  | "DRAFT"
  | "IN_MODERATION"
  | "PUBLISHED"
  | "REFUSED"
  | "HIDDEN"
  | "ARCHIVED";

export type MediaKind = "IMAGE" | "VIDEO";

export interface Category {
  id: number;
  slug: string;
  name_fr: string;
  name_en: string;
  description_fr: string;
  parent: number | null;
  children: Category[];
  position: number;
}

export interface Media {
  id: number;
  kind: MediaKind;
  position: number;
  alt_text_fr: string;
  alt_text_en: string;
  is_primary: boolean;
  width_px: number | null;
  height_px: number | null;
  content_type: string;
  thumbnail_url: string | null;
  poster_url: string | null;
  stream_url: string | null;
}

export interface ArtworkSummary {
  id: number;
  reference: string;
  slug: string;
  title: string;
  price_xaf: number;
  status: ArtworkStatus;
  stock_quantity: number;
  is_available: boolean;
  artist_display_name: string;
  artist_slug: string;
  category: number;
  primary_image_url: string | null;
  published_at: string | null;
  created_at: string;
}

export interface ArtworkDetail extends ArtworkSummary {
  description: string;
  dimensions: string;
  materials: string;
  technique: string;
  year_created: number | null;
  weight_kg: string | null;
  is_unique_piece: boolean;
  category_detail: Category;
  media: Media[];
}

export interface ArtistPublic {
  slug: string;
  display_name: string;
  bio: string;
  city: string;
  region: string;
  artwork_count: number;
}

export interface ArtistPublicDetail extends ArtistPublic {
  artworks: ArtworkSummary[];
}

export interface VideoFeedItem extends Media {
  artwork_slug: string;
  artwork_title: string;
  artist_display_name: string;
  artist_slug: string;
}

export interface MeUser {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  roles: string[];
  is_artist: boolean;
  email_verified_at: string | null;
  created_at: string;
}

export interface ArtworkDraft {
  title: string;
  description: string;
  category: number;
  price_xaf: number;
  stock_quantity: number;
  dimensions?: string;
  materials?: string;
  technique?: string;
  year_created?: number | null;
  is_unique_piece?: boolean;
}

/**
 * Fiche telle que renvoyée par `GET /artist/artworks/{id}` (ArtworkCreateSerializer) :
 * les champs éditables complets, mais pas les champs d'affichage public
 * (artist_display_name, primary_image_url, is_available).
 */
export interface ArtworkEditable extends ArtworkDraft {
  id: number;
  reference: string;
  slug: string;
  status: ArtworkStatus;
  dimensions: string;
  materials: string;
  technique: string;
  year_created: number | null;
  weight_kg: string | null;
  is_unique_piece: boolean;
}

export interface ArtistDashboard {
  total_artworks: number;
  published: number;
  in_moderation: number;
  drafts: number;
  unavailable: number;
  total_favorites: number;
}

export interface CatalogFilters {
  q?: string;
  category?: string;
  price_min?: string;
  price_max?: string;
  available?: string;
  artist?: string;
  /** Tri côté catalogue public ; réutilisé comme filtre `status` côté admin. */
  sort?: string;
  status?: ArtworkStatus;
  page?: string;
}

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------

/** Construit la query string du catalogue à partir des filtres (sérialisation stable). */
export function buildCatalogQuery(filters: CatalogFilters): string {
  const params = new URLSearchParams();
  const order: (keyof CatalogFilters)[] = [
    "q",
    "category",
    "price_min",
    "price_max",
    "available",
    "artist",
    "sort",
    "status",
    "page",
  ];
  for (const key of order) {
    const value = filters[key];
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      params.set(key, String(value));
    }
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

// --- Authentification (C1) ---

export function getCsrf(): Promise<{ detail: string; csrfToken: string }> {
  return apiFetch("/auth/csrf");
}

export function login(payload: { email: string; password: string }): Promise<MeUser> {
  return apiFetch("/auth/login", { method: "POST", body: JSON.stringify(payload) });
}

export function logout(): Promise<{ detail: string }> {
  return apiFetch("/auth/logout", { method: "POST" });
}

export function me(): Promise<MeUser> {
  return apiFetch("/auth/me");
}

export function register(payload: {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone?: string;
}): Promise<MeUser> {
  return apiFetch("/auth/register", { method: "POST", body: JSON.stringify(payload) });
}

// --- Catalogue public (C3) ---

export function listCatalogue(filters: CatalogFilters): Promise<Paginated<ArtworkSummary>> {
  return apiFetch(`/catalog/artworks/${buildCatalogQuery(filters)}`);
}

export function getArtwork(slug: string): Promise<ArtworkDetail> {
  return apiFetch(`/catalog/artworks/${encodeURIComponent(slug)}/`);
}

/**
 * Liste des catégories racines (avec enfants imbriqués).
 * Paginé : le backend applique sa pagination globale (page 20).
 */
export function listCategories(): Promise<Paginated<Category>> {
  return apiFetch("/catalog/categories/");
}

/** Artistes approuvés — paginé, pagination globale du backend. */
export function listArtists(): Promise<Paginated<ArtistPublic>> {
  return apiFetch("/catalog/artists/");
}

/**
 * Œuvres similaires — tableau brut : la vue définit `pagination_class = None`
 * (maximum fixe de 6, cf. CatalogArtworkSimilar).
 */
export function getSimilarArtworks(slug: string): Promise<ArtworkSummary[]> {
  return apiFetch(`/catalog/artworks/${encodeURIComponent(slug)}/similar/`);
}

export function getArtist(slug: string): Promise<ArtistPublicDetail> {
  return apiFetch(`/catalog/artists/${encodeURIComponent(slug)}/`);
}

export function listVideos(): Promise<VideoFeedItem[]> {
  return apiFetch("/videos/feed/");
}

export function toggleFavorite(artworkId: number): Promise<{ favorited: boolean }> {
  return apiFetch("/catalog/artworks/favorite/", {
    method: "POST",
    body: JSON.stringify({ artwork_id: artworkId }),
  });
}

// --- Espace artiste (C3, réservé IsArtist) ---

export function listMyArtworks(): Promise<Paginated<ArtworkSummary>> {
  return apiFetch("/artist/artworks");
}

export function createArtwork(draft: ArtworkDraft): Promise<ArtworkSummary> {
  return apiFetch("/artist/artworks", { method: "POST", body: JSON.stringify(draft) });
}

export function getMyArtwork(id: number): Promise<ArtworkEditable> {
  return apiFetch(`/artist/artworks/${id}/`);
}

export function updateArtwork(id: number, draft: Partial<ArtworkDraft>): Promise<ArtworkSummary> {
  return apiFetch(`/artist/artworks/${id}/`, { method: "PATCH", body: JSON.stringify(draft) });
}

/** DELETE = archivage logique (EF-7) : l'œuvre passe en ARCHIVED, jamais supprimée. */
export function archiveArtwork(id: number): Promise<void> {
  return apiFetch(`/artist/artworks/${id}/`, { method: "DELETE" });
}

export function publishArtwork(id: number): Promise<{ status: ArtworkStatus }> {
  return apiFetch(`/artist/artworks/${id}/publish`, { method: "POST" });
}

export function unpublishArtwork(id: number): Promise<{ status: ArtworkStatus }> {
  return apiFetch(`/artist/artworks/${id}/unpublish`, { method: "POST" });
}

export function getArtistDashboard(): Promise<ArtistDashboard> {
  return apiFetch("/artist/dashboard");
}

export function uploadArtworkMedia(
  artworkId: number,
  form: FormData,
): Promise<Media> {
  // FormData : on laisse le navigateur fixer le boundary multipart.
  return apiFetch(`/artist/artworks/${artworkId}/media`, { method: "POST", body: form });
}

export function deleteArtworkMedia(artworkId: number, mediaId: number): Promise<void> {
  return apiFetch(`/artist/artworks/${artworkId}/media/${mediaId}/`, { method: "DELETE" });
}

// --- Modération admin (C3, réservé IsModeratorOrAdmin) ---

export function listAdminArtworks(status?: ArtworkStatus): Promise<Paginated<ArtworkSummary>> {
  const query = status ? buildCatalogQuery({ status }) : "";
  return apiFetch(`/admin/artworks/${query}`);
}

export type ModerationDecision = "approve" | "refuse" | "hide";

export function moderateArtwork(
  id: number,
  decision: ModerationDecision,
  reason = "",
): Promise<{ status: ArtworkStatus }> {
  return apiFetch(`/admin/artworks/${id}/moderate`, {
    method: "POST",
    body: JSON.stringify({ decision, reason }),
  });
}
