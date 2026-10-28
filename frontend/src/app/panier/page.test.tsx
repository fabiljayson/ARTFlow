import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ApiError, type Cart } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getCart: vi.fn(),
    updateCartItem: vi.fn(),
    removeCartItem: vi.fn(),
  };
});

const { getCart } = await import("@/lib/api");
const PanierPage = (await import("@/app/panier/page")).default;

const EMPTY_CART: Cart = { id: 1, items_count: 0, items_total_xaf: 0, items: [] };

describe("/panier", () => {
  beforeEach(() => {
    vi.mocked(getCart).mockReset();
  });

  it("affiche l'état vide avec un lien vers le catalogue", async () => {
    vi.mocked(getCart).mockResolvedValue(EMPTY_CART);
    render(<PanierPage />);

    expect(await screen.findByText("Votre panier est vide")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /Parcourir le catalogue/ });
    expect(link).toHaveAttribute("href", "/catalogue");
  });

  it("affiche une erreur FR quand l'API échoue", async () => {
    vi.mocked(getCart).mockRejectedValue(new ApiError(500, "Erreur 500"));
    render(<PanierPage />);

    expect(await screen.findByText(/impossible de charger/i)).toBeInTheDocument();
  });
});
