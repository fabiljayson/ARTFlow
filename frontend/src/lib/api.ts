const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api/v1";

export interface HealthPayload {
  status: string;
  database: string;
}

export async function getHealth(signal?: AbortSignal): Promise<HealthPayload> {
  const res = await fetch(`${API_BASE}/health/`, { signal, cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }
  return (await res.json()) as HealthPayload;
}
