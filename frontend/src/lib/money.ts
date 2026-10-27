/**
 * Formatage monétaire XAF — entiers uniquement, zéro décimale.
 * Source: docs/requirements.md (EX-1) + docs/design.md §4.
 */
const xafFormatter = new Intl.NumberFormat("fr-CM", {
  style: "currency",
  currency: "XAF",
  currencyDisplay: "code",
  maximumFractionDigits: 0,
});

export function formatXAF(amount: number): string {
  if (!Number.isInteger(amount)) {
    throw new Error("XAF amounts must be integers");
  }
  return xafFormatter.format(amount);
}
