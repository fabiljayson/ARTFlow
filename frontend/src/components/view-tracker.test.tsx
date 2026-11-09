import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    recordView: vi.fn(),
  };
});

const { recordView } = await import("@/lib/api");
const { ViewTracker } = await import("@/components/view-tracker");

describe("ViewTracker", () => {
  beforeEach(() => {
    vi.mocked(recordView).mockReset();
    vi.mocked(recordView).mockResolvedValue({ view_count: 1, counted: true });
  });

  it("envoie une vue au montage une seule fois", async () => {
    render(<ViewTracker slug="masque-wouri" />);
    await waitFor(() => expect(recordView).toHaveBeenCalledWith("masque-wouri"));
    expect(recordView).toHaveBeenCalledTimes(1);
  });

  it("reste silencieux si l'enregistrement échoue", async () => {
    vi.mocked(recordView).mockRejectedValue(new Error("boom"));
    render(<ViewTracker slug="masque-wouri" />);
    await waitFor(() => expect(recordView).toHaveBeenCalled());
    expect(screen.queryByText(/erreur/i)).not.toBeInTheDocument();
  });
});
