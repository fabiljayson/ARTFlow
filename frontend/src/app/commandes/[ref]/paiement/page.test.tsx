import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ApiError, type OrderDetail } from "@/lib/api";
import { formatXAF } from "@/lib/money";

const push = vi.fn();
const replace = vi.fn();
const router = { push, replace };

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  useParams: () => ({ ref: "ORD-2026-000042" }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getOrder: vi.fn(),
    initiatePayment: vi.fn(),
    simulatePayment: vi.fn(),
  };
});

const { getOrder, initiatePayment, simulatePayment } = await import("@/lib/api");
const PayPage = (await import("@/app/commandes/[ref]/paiement/page")).default;

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
    buyer_note: "",
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

const INITIATED = {
  external_reference: "ext-ref-42",
  status: "PENDING",
  provider_reference: "MOCK-abc123",
  initiated_at: "2026-10-28T10:01:00Z",
};

describe("/commandes/[ref]/paiement", () => {
  beforeEach(() => {
    vi.mocked(getOrder).mockReset();
    vi.mocked(initiatePayment).mockReset();
    vi.mocked(simulatePayment).mockReset();
    push.mockReset();
    replace.mockReset();
  });

  it("affiche le montant et le formulaire de paiement", async () => {
    vi.mocked(getOrder).mockResolvedValue(makeOrder());
    render(<PayPage />);

    expect(await screen.findByText("Payer la commande")).toBeInTheDocument();
    expect(screen.getByText(money(52000))).toBeInTheDocument();
    expect(screen.getByLabelText(/Téléphone/)).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "MTN" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "ORANGE" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Payer/ })).toBeInTheDocument();
  });

  it("initie le paiement avec le téléphone et l'opérateur choisis", async () => {
    const pending = makeOrder({
      payment: {
        provider: "MOCK",
        status: "PENDING",
        external_reference: "ext-ref-42",
        failure_reason: "",
      },
    });
    vi.mocked(getOrder).mockResolvedValue(makeOrder());
    vi.mocked(initiatePayment).mockResolvedValue(INITIATED);
    render(<PayPage />);

    fireEvent.change(await screen.findByLabelText(/Téléphone/), {
      target: { value: "+237690000002" },
    });
    fireEvent.click(screen.getByRole("radio", { name: "ORANGE" }));
    vi.mocked(getOrder).mockResolvedValue(pending);
    fireEvent.click(screen.getByRole("button", { name: /^Payer/ }));

    await vi.waitFor(() =>
      expect(vi.mocked(initiatePayment).mock.calls[0]).toEqual([
        "ext-ref-42",
        { phone: "+237690000002", operator: "ORANGE" },
      ]),
    );
    expect(
      await screen.findByText(/En attente de confirmation/),
    ).toBeInTheDocument();
  });

  it("bascule en succès quand l'ordre devient payé, puis pousse vers le détail", async () => {
    const pending = makeOrder({
      payment: {
        provider: "MOCK",
        status: "PENDING",
        external_reference: "ext-ref-42",
        failure_reason: "",
      },
    });
    const paid = makeOrder({
      status: "PAID",
      paid_at: "2026-10-28T10:05:00Z",
      payment: {
        provider: "MOCK",
        status: "SUCCEEDED",
        external_reference: "ext-ref-42",
        failure_reason: "",
      },
    });
    vi.mocked(getOrder)
      .mockResolvedValueOnce(makeOrder())
      .mockResolvedValue(pending);
    vi.mocked(initiatePayment).mockResolvedValue(INITIATED);
    render(<PayPage />);

    fireEvent.click(await screen.findByRole("button", { name: /^Payer/ }));
    await screen.findByText(/En attente de confirmation/);

    // Le prochain rafraîchissement (poll toutes les 3 s) ramène la commande payée.
    vi.mocked(getOrder).mockResolvedValue(paid);
    expect(
      await screen.findByText("Paiement confirmé !", undefined, { timeout: 5000 }),
    ).toBeInTheDocument();
    await vi.waitFor(
      () => expect(push).toHaveBeenCalledWith("/commandes/ORD-2026-000042"),
      { timeout: 6000 },
    );
  });

  it("offre le simulateur en attente et déclenche le scénario choisi", async () => {
    const pending = makeOrder({
      payment: {
        provider: "MOCK",
        status: "PENDING",
        external_reference: "ext-ref-42",
        failure_reason: "",
      },
    });
    const paid = makeOrder({
      status: "PAID",
      paid_at: "2026-10-28T10:05:00Z",
      payment: {
        provider: "MOCK",
        status: "SUCCEEDED",
        external_reference: "ext-ref-42",
        failure_reason: "",
      },
    });
    vi.mocked(getOrder).mockResolvedValue(pending);
    vi.mocked(simulatePayment).mockResolvedValue({ delivered: 1 });
    render(<PayPage />);

    await screen.findByRole("button", { name: /Simuler un paiement réussi/ });
    vi.mocked(getOrder).mockResolvedValue(paid);
    fireEvent.click(screen.getByRole("button", { name: /Simuler un paiement réussi/ }));

    await vi.waitFor(() =>
      expect(vi.mocked(simulatePayment)).toHaveBeenCalledWith(
        "ext-ref-42",
        "success",
      ),
    );
    expect(await screen.findByText("Paiement confirmé !")).toBeInTheDocument();
  });

  it("affiche l'échec avec la raison après un échec simulé", async () => {
    const pending = makeOrder({
      payment: {
        provider: "MOCK",
        status: "PENDING",
        external_reference: "ext-ref-42",
        failure_reason: "",
      },
    });
    const failed = makeOrder({
      status: "CANCELLED",
      cancelled_at: "2026-10-28T10:05:00Z",
      payment: {
        provider: "MOCK",
        status: "FAILED",
        external_reference: "ext-ref-42",
        failure_reason: "Échec simulé (scénario fail).",
      },
    });
    vi.mocked(getOrder).mockResolvedValue(pending);
    vi.mocked(simulatePayment).mockResolvedValue({ delivered: 1 });
    render(<PayPage />);

    await screen.findByRole("button", { name: /Simuler un échec/ });
    vi.mocked(getOrder).mockResolvedValue(failed);
    fireEvent.click(screen.getByRole("button", { name: /Simuler un échec/ }));

    expect(
      await screen.findByText(/Le paiement a échoué/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Échec simulé \(scénario fail\)/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Retour au panier/ })).toHaveAttribute(
      "href",
      "/panier",
    );
  });

  it("remplace vers le détail si la commande est déjà payée au montage", async () => {
    vi.mocked(getOrder).mockResolvedValue(
      makeOrder({
        status: "PAID",
        paid_at: "2026-10-28T10:05:00Z",
        payment: {
          provider: "MOCK",
          status: "SUCCEEDED",
          external_reference: "ext-ref-42",
          failure_reason: "",
        },
      }),
    );
    render(<PayPage />);

    await vi.waitFor(() =>
      expect(replace).toHaveBeenCalledWith("/commandes/ORD-2026-000042"),
    );
  });

  it("bascule vers /connexion sur 401", async () => {
    vi.mocked(getOrder).mockRejectedValue(new ApiError(401, "Non authentifié"));
    render(<PayPage />);

    await vi.waitFor(() =>
      expect(replace).toHaveBeenCalledWith(
        `/connexion?next=${encodeURIComponent("/commandes/ORD-2026-000042/paiement")}`,
      ),
    );
  });
});
