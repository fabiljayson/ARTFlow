import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { VerifiedBadge } from "@/components/verified-badge";

describe("VerifiedBadge", () => {
  it("affiche le badge avec un libellé accessible", () => {
    render(<VerifiedBadge />);
    expect(screen.getByLabelText("Artiste vérifié")).toBeInTheDocument();
  });
});
