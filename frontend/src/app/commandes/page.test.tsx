import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ApiError, type OrderSummary, type Paginated } from "@/lib/api";
import { formatXAF } from "@/lib/money";

const push = vi.fn();
const replace = vi.fn();
// Routeur stable (voir checkout/page.test.tsx) : sinon la page re-fetch à
// chaque render et les assertions d'état deviennent non déterministes.
const router = { push, replace };

vi.mock("next/navigation", () => ({
  useRouter: () => router,
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, listOrders: vi.fn() };
});

const { listOrders } = await import("@/lib/api");
const CommandesPage = (await import("@/app/commandes/page")).default;

function money(amount: number) {
  const expected = formatXAF(amount).replace(/\s+/g, " ");
  return (content: string) => content.replace(/\s+/g, " ") === expected;
}

const ORDER: OrderSummary = {
  reference: "ORD-2026-000042",
  status: "PENDING_PAYMENT",
  placed_at: "2026-10-28T10:00:00Z",
  paid_at: null,
  subtotal_items_xaf: 50000,
  shipping_total_xaf: 2000,
  grand_total_xaf: 52000,
  items_count: 2,
};

const PAGE: Paginated<OrderSummary> = {
  count: 1,
  next: null,
  previous: null,
  results: [ORDER],
};

describe("/commandes", () => {
  beforeEach(() => {
    vi.mocked(listOrders).mockReset();
    push.mockReset();
    replace.mockReset();
  });

  it("liste les commandes avec référence, statut FR et total", async () => {
    vi.mocked(listOrders).mockResolvedValue(PAGE);
    render(<CommandesPage />);

    expect(await screen.findByText("ORD-2026-000042")).toBeInTheDocument();
    expect(screen.getByText("En attente de paiement")).toBeInTheDocument();
    expect(screen.getByText(money(52000))).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /ORD-2026-000042/ });
    expect(link).toHaveAttribute("href", "/commandes/ORD-2026-000042");
  });

  it("affiche l'état vide sans commande", async () => {
    vi.mocked(listOrders).mockResolvedValue({ count: 0, next: null, previous: null, results: [] });
    render(<CommandesPage />);

    expect(await screen.findByText("Aucune commande")).toBeInTheDocument();
  });

  it("bascule vers /connexion sur 401", async () => {
    vi.mocked(listOrders).mockRejectedValue(new ApiError(401, "Non authentifié"));
    render(<CommandesPage />);

    await vi.waitFor(() =>
      expect(replace).toHaveBeenCalledWith(
        `/connexion?next=${encodeURIComponent("/commandes")}`,
      ),
    );
  });
});
