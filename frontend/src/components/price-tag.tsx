import { formatXAF } from "@/lib/money";

export function PriceTag({ amount, className }: { amount: number; className?: string }) {
  return (
    <span className={className ?? "font-semibold text-primary"}>{formatXAF(amount)}</span>
  );
}
