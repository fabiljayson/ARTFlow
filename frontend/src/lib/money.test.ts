import { describe, expect, it } from "vitest";
import { formatXAF } from "@/lib/money";

describe("formatXAF", () => {
  it("formats integer amounts without decimals", () => {
    expect(formatXAF(100000)).toContain("100");
    expect(formatXAF(100000)).toContain("XAF");
    expect(formatXAF(100000)).not.toContain(".");
  });

  it("rejects non-integer amounts", () => {
    expect(() => formatXAF(99.5)).toThrow(/integers/);
  });
});
