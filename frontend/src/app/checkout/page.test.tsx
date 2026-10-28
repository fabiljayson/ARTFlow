import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ApiError, type Address, type Paginated, type Quote } from "@/lib/api";
import { formatXAF } from "@/lib/money";

const push = vi.fn();
const replace = vi.fn();
// Routeur stable : un objet neuf à chaque render re-déclenche l'effet de
// chargement (useCallback dépend de `router`) et écrase l'état testé.
const router = { push, replace };

vi.mock("next/navigation", () => ({
  useRouter: () => router,
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    quoteCheckout: vi.fn(),
    listAddresses: vi.fn(),
    createAddress: vi.fn(),
    checkout: vi.fn(),
  };
});

const { quoteCheckout, listAddresses, createAddress, checkout } = await import("@/lib/api");
const CheckoutPage = (await import("@/app/checkout/page")).default;

function money(amount: number) {
  const expected = formatXAF(amount).replace(/\s+/g, " ");
  return (content: string) => content.replace(/\s+/g, " ") === expected;
}

const ADDRESS: Address = {
  id: 1,
  label: "Maison",
  recipient_name: "Jean",
  line1: "12 rue des Palmiers",
  line2: "",
  city: "Douala",
  region: "Littoral",
  phone: "690000001",
  is_default: true,
};

const QUOTE: Quote = {
  items: [
    {
      artwork_id: 7,
      slug: "a-un",
      title: "Aube sur le Wouri",
      quantity: 2,
      unit_price_xaf: 25000,
      line_total_xaf: 50000,
      artist: { id: 3, display_name: "Atelier Njoya" },
      commission_rate_bps: 1000,
      commission_xaf: 5000,
      artist_net_xaf: 45000,
      primary_image_url: null,
    },
  ],
  shipping: [{ artist_id: 3, display_name: "Atelier Njoya", shipping_fee_xaf: 2000 }],
  subtotal_items_xaf: 50000,
  shipping_total_xaf: 2000,
  fees_total_xaf: 0,
  grand_total_xaf: 52000,
  items_count: 2,
  blocking_issues: [],
};

const ADDRESSES: Paginated<Address> = {
  count: 1,
  next: null,
  previous: null,
  results: [ADDRESS],
};

describe("/checkout", () => {
  beforeEach(() => {
    vi.mocked(quoteCheckout).mockReset();
    vi.mocked(listAddresses).mockReset();
    vi.mocked(createAddress).mockReset();
    vi.mocked(checkout).mockReset();
    push.mockReset();
    replace.mockReset();
  });

  it("affiche les articles, les totaux serveur et l'adresse par défaut", async () => {
    vi.mocked(quoteCheckout).mockResolvedValue(QUOTE);
    vi.mocked(listAddresses).mockResolvedValue(ADDRESSES);
    render(<CheckoutPage />);

    expect(await screen.findByText("Aube sur le Wouri")).toBeInTheDocument();
    expect(screen.getByText(money(52000))).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Maison/ })).toBeChecked();
  });

  it("propose le mini-formulaire quand aucune adresse n'existe", async () => {
    vi.mocked(quoteCheckout).mockResolvedValue(QUOTE);
    vi.mocked(listAddresses).mockResolvedValue({ count: 0, next: null, previous: null, results: [] });
    render(<CheckoutPage />);

    expect(await screen.findByText(/Aucune adresse enregistrée/)).toBeInTheDocument();
    // Le bouton de confirmation est sans adresse sélectionnée : désactivé.
    expect(screen.getByRole("button", { name: /Confirmer la commande/ })).toBeDisabled();
  });

  it("crée une adresse via le mini-form et la sélectionne", async () => {
    vi.mocked(quoteCheckout).mockResolvedValue(QUOTE);
    vi.mocked(listAddresses).mockResolvedValue({ count: 0, next: null, previous: null, results: [] });
    vi.mocked(createAddress).mockResolvedValue({
      ...ADDRESS,
      id: 9,
      label: "Bureau",
      is_default: false,
    });
    render(<CheckoutPage />);

    fireEvent.change(await screen.findByPlaceholderText("Maison"), {
      target: { value: "Bureau" },
    });
    fireEvent.change(screen.getByLabelText("Destinataire"), {
      target: { value: "Jean" },
    });
    // jsdom ne déclenche pas `submit` depuis un clic sur un bouton : on soumet
    // le formulaire directement.
    const form = screen.getByRole("button", { name: /Enregistrer l'adresse/ }).closest("form");
    expect(form).not.toBeNull();
    fireEvent.submit(form!);

    expect(await screen.findByRole("radio", { name: /Bureau/ })).toBeChecked();
    expect(createAddress).toHaveBeenCalledTimes(1);
  });

  it("confirme avec un Idempotency-Key UUID et redirige vers la page de paiement", async () => {
    vi.mocked(quoteCheckout).mockResolvedValue(QUOTE);
    vi.mocked(listAddresses).mockResolvedValue(ADDRESSES);
    vi.mocked(checkout).mockResolvedValue({
      order_reference: "ORD-2026-000042",
      status: "PENDING_PAYMENT",
      grand_total_xaf: 52000,
      placed_at: "2026-10-28T10:00:00Z",
      payment: { provider: "MOCK", status: "CREATED", redirect_info: null },
    });
    render(<CheckoutPage />);

    fireEvent.click(await screen.findByRole("button", { name: /Confirmer la commande/ }));

    await vi.waitFor(() => expect(checkout).toHaveBeenCalledTimes(1));
    const [payload, key] = vi.mocked(checkout).mock.calls[0];
    expect(payload.address_id).toBe(1);
    expect(key).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    );
    await vi.waitFor(() =>
      expect(push).toHaveBeenCalledWith("/commandes/ORD-2026-000042/paiement"),
    );
  });

  it("bascule vers /connexion sur 401", async () => {
    vi.mocked(quoteCheckout).mockRejectedValue(new ApiError(401, "Non authentifié"));
    vi.mocked(listAddresses).mockRejectedValue(new ApiError(401, "Non authentifié"));
    render(<CheckoutPage />);

    await vi.waitFor(() =>
      expect(replace).toHaveBeenCalledWith(
        `/connexion?next=${encodeURIComponent("/checkout")}`,
      ),
    );
  });

  it("affiche les blocages de stock et désactive la confirmation", async () => {
    vi.mocked(quoteCheckout).mockResolvedValue({
      ...QUOTE,
      blocking_issues: [
        { artwork_id: 7, code: "stock_insufficient", message: "Stock insuffisant pour « Aube sur le Wouri ».", quantity_demandee: 2 },
      ],
    });
    vi.mocked(listAddresses).mockResolvedValue(ADDRESSES);
    render(<CheckoutPage />);

    expect(await screen.findByText(/Stock insuffisant pour/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Confirmer la commande/ })).toBeDisabled();
  });

  it("affiche l'état vide quand le panier est vide", async () => {
    vi.mocked(quoteCheckout).mockResolvedValue({
      ...QUOTE,
      items: [],
      items_count: 0,
      grand_total_xaf: 0,
    });
    vi.mocked(listAddresses).mockResolvedValue(ADDRESSES);
    render(<CheckoutPage />);

    expect(await screen.findByText("Rien à commander")).toBeInTheDocument();
  });
});
