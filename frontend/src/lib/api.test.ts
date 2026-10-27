import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  apiFetch,
  buildCatalogQuery,
  proxiedUrl,
  readCsrfToken,
} from "@/lib/api";

describe("readCsrfToken", () => {
  it("lit le cookie csrftoken parmi plusieurs cookies", () => {
    expect(readCsrfToken("a=1; csrftoken=abc123; b=2")).toBe("abc123");
  });

  it("retourne null quand le cookie est absent", () => {
    expect(readCsrfToken("sessionid=xyz")).toBeNull();
  });

  it("ignore les cookies dont le nom contient csrftoken en suffixe", () => {
    expect(readCsrfToken("notcsrftoken=nope")).toBeNull();
  });

  it("décodit les caractères encodés", () => {
    expect(readCsrfToken("csrftoken=a%20b")).toBe("a b");
  });
});

describe("buildCatalogQuery", () => {
  it("retourne une chaîne vide sans filtre", () => {
    expect(buildCatalogQuery({})).toBe("");
  });

  it("sérialise les filtres dans un ordre stable", () => {
    expect(
      buildCatalogQuery({
        page: "2",
        q: "masque",
        category: "sculpture",
        price_min: "1000",
        price_max: "5000",
        available: "true",
        sort: "price",
      }),
    ).toBe("?q=masque&category=sculpture&price_min=1000&price_max=5000&available=true&sort=price&page=2");
  });

  it("ignore les valeurs vides ou en blanc", () => {
    expect(buildCatalogQuery({ q: "", category: "  ", price_min: undefined })).toBe("");
  });

  it("inclut le filtre de statut utilisé par l'admin", () => {
    expect(buildCatalogQuery({ status: "IN_MODERATION" })).toBe("?status=IN_MODERATION");
  });

  it("encode les caractères spéciaux de la recherche", () => {
    expect(buildCatalogQuery({ q: "a&b" })).toBe("?q=a%26b");
  });
});

describe("proxiedUrl", () => {
  it("ramène une URL absolue de l'API en chemin relatif", () => {
    expect(proxiedUrl("http://127.0.0.1:8003/api/v1/catalog/artworks/x/media/1/thumb/")).toBe(
      "/api/v1/catalog/artworks/x/media/1/thumb/",
    );
  });

  it("conserve une URL déjà relative", () => {
    expect(proxiedUrl("/api/v1/catalog/artworks/")).toBe("/api/v1/catalog/artworks/");
  });

  it("conserve les paramètres de requête", () => {
    expect(proxiedUrl("http://127.0.0.1:8003/api/v1/catalog/artworks?page=2")).toBe(
      "/api/v1/catalog/artworks?page=2",
    );
  });

  it("retourne null pour une URL absente", () => {
    expect(proxiedUrl(null)).toBeNull();
    expect(proxiedUrl(undefined)).toBeNull();
    expect(proxiedUrl("")).toBeNull();
  });
});

describe("apiFetch", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    document.cookie = "csrftoken=tok123; Path=/";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "csrftoken=; Path=/; Max-Age=0";
  });

  it("envoie X-CSRFToken sur les méthodes non sûres", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));

    await apiFetch("/auth/login", { method: "POST", body: JSON.stringify({ a: 1 }) });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/login");
    expect(new Headers(init.headers).get("X-CSRFToken")).toBe("tok123");
    expect(init.credentials).toBe("include");
  });

  it("n'envoie pas de CSRF sur les requêtes GET", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));

    await apiFetch("/catalog/artworks");

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).get("X-CSRFToken")).toBeNull();
  });

  it("retire le slash final pour éviter la boucle de redirection", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));

    await apiFetch("/catalog/artworks/");

    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/catalog/artworks");
  });

  it("découpe l'enveloppe d'erreur du backend", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { code: "invalid", message: "Champ invalide.", details: { email: ["Requis"] } },
        }),
        { status: 400 },
      ),
    );

    await expect(apiFetch("/auth/register", { method: "POST" })).rejects.toMatchObject({
      name: "ApiError",
      status: 400,
      code: "invalid",
      message: "Champ invalide.",
    });
    await expect(apiFetch("/auth/register", { method: "POST" })).rejects.toBeInstanceOf(ApiError);
  });

  it("retombe sur un message générique sans enveloppe", async () => {
    fetchMock.mockResolvedValue(new Response("boom", { status: 500 }));

    await expect(apiFetch("/x")).rejects.toMatchObject({ status: 500, message: "Erreur 500" });
  });

  it("renvoie undefined sur une réponse 204", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    await expect(apiFetch("/artist/artworks/1", { method: "DELETE" })).resolves.toBeUndefined();
  });

  it("réécrit les URLs de médias absolues vers le proxy", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          results: [
            { id: 1, primary_image_url: "http://127.0.0.1:8003/api/v1/media/1/" },
            { id: 2, primary_image_url: null },
          ],
        }),
        { status: 200 },
      ),
    );

    const data = await apiFetch<{ results: { primary_image_url: string | null }[] }>(
      "/catalog/artworks",
    );

    expect(data.results[0].primary_image_url).toBe("/api/v1/media/1/");
    expect(data.results[1].primary_image_url).toBeNull();
  });
});
