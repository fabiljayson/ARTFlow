import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ApiError, type OrderDetail } from "@/lib/api";
import { formatXAF } from "@/lib/money";

const push = vi.fn();
const replace = vi.fn();
// Routeur stable : un objet neuf à chaque render re-déclencherait l'effet de
// chargement de la page et écraserait les mises à jour d'état testées.
const router = { push, replace };

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  useParams: () => ({ ref: "ORD-2026-000042" }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, getOrder: vi.fn(), cancelOrder: vi.fn() };
});

const { getOrder, cancelOrder } = await import("@/lib/api");
const DetailPage = (await import("@/app/commandes/[ref]/page")).default;

function money(amount: number) {
  const expected = formatXAF(amount).replace(/\s+/g, " ");
  return (content: string) => content.replace(/\s+/g, " ") === expected;
}

function makeOrder(overrides: Partial<OrderDetail> = {}): OrderDetail {
  return {
    reference: "ORD-2026-000042",
    status: "PENDING_PAYMENT",
    placed_at: "2026-10-28T10:00:00Z",
    paid_at: null,
    cancelled_at: null,
    subtotal_items_xaf: 50000,
    shipping_total_xaf: 2000,
    fees_total_xaf: 0,
    grand_total_xaf: 52000,
    currency: "XAF",
    shipping_address_snapshot: {
      recipient_name: "Jean",
      line1: "12 rue des Palmiers",
      line2: "",
      city: "Douala",
      region: "Littoral",
      phone: "690000001",
    },
    buyer_note: "Emballage cadeau",
    items: [
      {
        id: 1,
        artwork_id: 7,
        title_snapshot: "Aube sur le Wouri",
        unit_price_xaf: 25000,
        quantity: 2,
        line_total_xaf: 50000,
        commission_rate_bps: 1000,
        commission_xaf: 5000,
        artist_net_xaf: 45000,
        artist: { id: 3, display_name: "Atelier Njoya" },
        primary_image_url: null,
      },
    ],
    payment: {
      provider: "MOCK",
      status: "CREATED",
      external_reference: "ext-ref-42",
      failure_reason: "",
    },
    shipments: [],
    disputes: [],
    ...overrides,
  };
}

describe("/commandes/[ref]", () => {
  beforeEach(() => {
    vi.mocked(getOrder).mockReset();
    vi.mocked(cancelOrder).mockReset();
    push.mockReset();
    replace.mockReset();
  });

  it("affiche les instantanés figés, l'adresse et le paiement", async () => {
    vi.mocked(getOrder).mockResolvedValue(makeOrder());
    render(<DetailPage />);

    expect(await screen.findByText("Commande ORD-2026-000042")).toBeInTheDocument();
    expect(screen.getByText("Aube sur le Wouri")).toBeInTheDocument();
    expect(screen.getAllByText(money(50000)).length).toBeGreaterThan(0);
    expect(screen.getByText(/12 rue des Palmiers/)).toBeInTheDocument();
    expect(screen.getByText(/MOCK — CREATED/)).toBeInTheDocument();
    expect(screen.getByText(/Emballage cadeau/)).toBeInTheDocument();
  });

  it("affiche la bannière d'attente et annule la commande impayée", async () => {
    vi.mocked(getOrder).mockResolvedValue(makeOrder());
    vi.mocked(cancelOrder).mockResolvedValue(
      makeOrder({ status: "CANCELLED", cancelled_at: "2026-10-28T11:00:00Z" }),
    );
    render(<DetailPage />);

    expect(await screen.findByText("Paiement en attente.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Annuler la commande/ }));

    await vi.waitFor(() => expect(cancelOrder).toHaveBeenCalledWith("ORD-2026-000042"));
    expect(await screen.findByText("Annulée")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Annuler la commande/ })).not.toBeInTheDocument();
  });

  it("n'affiche pas d'annulation une fois payée", async () => {
    vi.mocked(getOrder).mockResolvedValue(
      makeOrder({ status: "PAID", paid_at: "2026-10-28T10:05:00Z" }),
    );
    render(<DetailPage />);

    expect(await screen.findByText("Payée")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Annuler la commande/ })).not.toBeInTheDocument();
    expect(screen.queryByText("Paiement en attente.")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /Payer maintenant/ }),
    ).not.toBeInTheDocument();
  });

  it("propose de payer depuis la bannière d'attente", async () => {
    vi.mocked(getOrder).mockResolvedValue(makeOrder());
    render(<DetailPage />);

    const link = await screen.findByRole("link", { name: /Payer maintenant/ });
    expect(link).toHaveAttribute(
      "href",
      "/commandes/ORD-2026-000042/paiement",
    );
  });

  it("affiche une erreur quand la commande est introuvable", async () => {
    vi.mocked(getOrder).mockRejectedValue(new ApiError(404, "Commande introuvable"));
    render(<DetailPage />);

    expect(await screen.findByText("Commande introuvable.")).toBeInTheDocument();
  });

  it("bascule vers /connexion sur 401", async () => {
    vi.mocked(getOrder).mockRejectedValue(new ApiError(401, "Non authentifié"));
    render(<DetailPage />);

    await vi.waitFor(() =>
      expect(replace).toHaveBeenCalledWith(
        `/connexion?next=${encodeURIComponent("/commandes/ORD-2026-000042")}`,
      ),
    );
  });
});
