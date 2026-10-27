import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "@/components/status-badge";
import type { ArtworkStatus } from "@/lib/api";

const CASES: [ArtworkStatus, string][] = [
  ["DRAFT", "Brouillon"],
  ["IN_MODERATION", "En modération"],
  ["PUBLISHED", "Publié"],
  ["REFUSED", "Refusé"],
  ["HIDDEN", "Masqué"],
  ["ARCHIVED", "Archivé"],
];

describe("StatusBadge", () => {
  it.each(CASES)("traduit le statut %s en libellé FR", (status, label) => {
    render(<StatusBadge status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("couvre les six statuts du modèle ArtworkStatus", () => {
    expect(CASES.map(([status]) => status).sort()).toEqual(
      ["ARCHIVED", "DRAFT", "HIDDEN", "IN_MODERATION", "PUBLISHED", "REFUSED"].sort(),
    );
  });
});
