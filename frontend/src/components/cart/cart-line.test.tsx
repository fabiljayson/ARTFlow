import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { CartLine } from "@/components/cart/cart-line";
import { formatXAF } from "@/lib/money";
import type { CartItem } from "@/lib/api";

function makeItem(overrides: Partial<CartItem> = {}): CartItem {
  return {
    id: 7,
    quantity: 2,
    line_total_xaf: 600000,
    quantity_exceeds_stock: false,
    artwork_unavailable: false,
    artwork: {
      id: 3,
      slug: "portrait-awa",
      title: "Portrait d'Awa",
      price_xaf: 300000,
      stock_quantity: 3,
      is_available: true,
      artist_display_name: "Awa Ndiaye",
      primary_image_url: null,
    },
    ...overrides,
  };
}

/** Les montants XAF contiennent des espaces insécables : RTL les normalise côté
 * candidat mais pas le matcheur littéral — on compare donc normalisé de bord à bord. */
function money(amount: number) {
  const expected = formatXAF(amount).replace(/\s+/g, " ");
  return (content: string) => content.replace(/\s+/g, " ") === expected;
}

describe("CartLine", () => {
  it("affiche le titre, l'artiste et le prix en XAF", () => {
    render(<CartLine item={makeItem()} onQuantityChange={() => {}} onRemove={() => {}} />);

    expect(screen.getByText("Portrait d'Awa")).toBeInTheDocument();
    expect(screen.getByText(/Awa Ndiaye/)).toBeInTheDocument();
    expect(screen.getByText(money(300000))).toBeInTheDocument();
    expect(screen.getByText(money(600000))).toBeInTheDocument();
  });

  it("affiche l'alerte stock modifié quand quantity_exceeds_stock", () => {
    render(
      <CartLine
        item={makeItem({ quantity_exceeds_stock: true, quantity: 5, artwork: { ...makeItem().artwork, stock_quantity: 2 } })}
        onQuantityChange={() => {}}
        onRemove={() => {}}
      />,
    );

    expect(screen.getByText(/Stock modifié/)).toBeInTheDocument();
  });

  it("affiche l'alerte indisponible quand artwork_unavailable", () => {
    render(
      <CartLine item={makeItem({ artwork_unavailable: true })} onQuantityChange={() => {}} onRemove={() => {}} />,
    );

    expect(screen.getByText(/plus disponible/)).toBeInTheDocument();
  });

  it("n'affiche aucune alerte en temps normal", () => {
    render(<CartLine item={makeItem()} onQuantityChange={() => {}} onRemove={() => {}} />);

    expect(screen.queryByText(/Stock modifié/)).not.toBeInTheDocument();
    expect(screen.queryByText(/plus disponible/)).not.toBeInTheDocument();
  });

  it("appelle onQuantityChange avec la nouvelle quantité", async () => {
    const onQuantityChange = vi.fn();
    render(<CartLine item={makeItem()} onQuantityChange={onQuantityChange} onRemove={() => {}} />);

    fireEvent.click(screen.getByRole("button", { name: "Augmenter la quantité" }));
    expect(onQuantityChange).toHaveBeenCalledWith(7, 3);

    fireEvent.click(screen.getByRole("button", { name: "Diminuer la quantité" }));
    expect(onQuantityChange).toHaveBeenCalledWith(7, 1);
  });

  it("n'augmente pas au-delà du stock affiché", async () => {
    const onQuantityChange = vi.fn();
    render(
      <CartLine
        item={makeItem({ quantity: 2, artwork: { ...makeItem().artwork, stock_quantity: 2 } })}
        onQuantityChange={onQuantityChange}
        onRemove={() => {}}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Augmenter la quantité" }));
    expect(onQuantityChange).not.toHaveBeenCalled();
  });

  it("appelle onRemove au clic sur Retirer", async () => {
    const onRemove = vi.fn();
    render(<CartLine item={makeItem()} onQuantityChange={() => {}} onRemove={onRemove} />);

    fireEvent.click(screen.getByRole("button", { name: "Retirer du panier" }));
    expect(onRemove).toHaveBeenCalledWith(7);
  });
});
