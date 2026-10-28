import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ApiError, type Cart } from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, getCart: vi.fn(), addCartItem: vi.fn() };
});

const { getCart, addCartItem } = await import("@/lib/api");
const { CartLink } = await import("@/components/cart/cart-link");
const { AddToCartButton } = await import("@/components/cart/add-to-cart-button");

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/oeuvre/portrait-awa",
}));

const FULL_CART: Cart = { id: 1, items_count: 3, items_total_xaf: 90000, items: [] };
const EMPTY_CART: Cart = { id: 1, items_count: 0, items_total_xaf: 0, items: [] };

describe("CartLink", () => {
  beforeEach(() => {
    vi.mocked(getCart).mockReset();
  });

  it("affiche le badge du nombre d'articles", async () => {
    vi.mocked(getCart).mockResolvedValue(FULL_CART);
    render(<CartLink />);

    expect(await screen.findByRole("link", { name: /Panier/ })).toHaveAttribute("href", "/panier");
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("n'affiche pas de badge pour un panier vide", async () => {
    vi.mocked(getCart).mockResolvedValue(EMPTY_CART);
    render(<CartLink />);

    await screen.findByRole("link", { name: /Panier/ });
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("reste invisible pour un visiteur anonyme (401)", async () => {
    vi.mocked(getCart).mockRejectedValue(new ApiError(401, "Authentification requise."));
    const { container } = render(<CartLink />);

    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});

describe("AddToCartButton", () => {
  beforeEach(() => {
    vi.mocked(addCartItem).mockReset();
  });

  it("ajoute l'œuvre au panier et signale le succès", async () => {
    vi.mocked(addCartItem).mockResolvedValue({
      id: 1,
      quantity: 1,
      line_total_xaf: 0,
      quantity_exceeds_stock: false,
      artwork_unavailable: false,
      artwork: {
        id: 5,
        slug: "x",
        title: "X",
        price_xaf: 1,
        stock_quantity: 1,
        is_available: true,
        artist_display_name: "A",
        primary_image_url: null,
      },
    });
    render(<AddToCartButton artworkId={5} />);

    fireEvent.click(screen.getByRole("button", { name: /Ajouter au panier/ }));

    expect(await screen.findByText(/Ajouté au panier/)).toBeInTheDocument();
    expect(addCartItem).toHaveBeenCalledWith(5, 1);
  });

  it("affiche le message serveur quand le stock est insuffisant", async () => {
    vi.mocked(addCartItem).mockRejectedValue(
      new ApiError(400, "Stock insuffisant : il reste 1 exemplaire(s).", "validation_error"),
    );
    render(<AddToCartButton artworkId={5} />);

    fireEvent.click(screen.getByRole("button", { name: /Ajouter au panier/ }));

    expect(await screen.findByText(/Stock insuffisant/)).toBeInTheDocument();
  });
});
