import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ArtworkCard } from "@/components/artwork-card";
import type { ArtworkSummary } from "@/lib/api";

function makeArtwork(overrides: Partial<ArtworkSummary> = {}): ArtworkSummary {
  return {
    id: 1,
    reference: "ART-2026-000001",
    slug: "masque-wouri",
    title: "Masque du Wouri",
    price_xaf: 320000,
    status: "PUBLISHED",
    stock_quantity: 1,
    is_available: true,
    artist_display_name: "Amina Ngo",
    artist_slug: "amina-ngo",
    category: 2,
    primary_image_url: "/api/v1/catalog/artworks/masque-wouri/media/3/thumb/",
    published_at: "2026-10-27T00:00:00Z",
    created_at: "2026-10-27T00:00:00Z",
    ...overrides,
  };
}

describe("ArtworkCard", () => {
  it("affiche le titre, l'artiste et le prix en XAF", () => {
    render(<ArtworkCard artwork={makeArtwork()} />);

    expect(screen.getByText("Masque du Wouri")).toBeInTheDocument();
    expect(screen.getByText("Amina Ngo")).toBeInTheDocument();
    expect(screen.getByText(/320/)).toBeInTheDocument();
    expect(screen.getByText(/XAF/)).toBeInTheDocument();
  });

  it("pointe vers la fiche de l'œuvre", () => {
    render(<ArtworkCard artwork={makeArtwork()} />);

    expect(screen.getByRole("link")).toHaveAttribute("href", "/oeuvre/masque-wouri");
  });

  it("affiche le badge Épuisé quand l'œuvre n'est pas disponible", () => {
    render(<ArtworkCard artwork={makeArtwork({ is_available: false, stock_quantity: 0 })} />);

    expect(screen.getByText("Épuisé")).toBeInTheDocument();
  });

  it("n'affiche pas de badge quand l'œuvre est disponible", () => {
    render(<ArtworkCard artwork={makeArtwork()} />);

    expect(screen.queryByText("Épuisé")).not.toBeInTheDocument();
  });

  it("gère une œuvre sans image principale", () => {
    render(<ArtworkCard artwork={makeArtwork({ primary_image_url: null })} />);

    expect(screen.getByText("Masque du Wouri")).toBeInTheDocument();
  });
});
