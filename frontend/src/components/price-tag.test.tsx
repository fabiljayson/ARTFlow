import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PriceTag } from "@/components/price-tag";

describe("PriceTag", () => {
  it("renders an XAF amount", () => {
    render(<PriceTag amount={45000} />);
    expect(screen.getByText(/45/)).toBeInTheDocument();
    expect(screen.getByText(/XAF/)).toBeInTheDocument();
  });
});
