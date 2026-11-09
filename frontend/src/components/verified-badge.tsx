/**
 * Petit ✓ d'artiste vérifié — preuve sociale §1 (design 2026-11-09).
 * Présentatif, sans props : `role="img"` + `aria-label` portent l'accessibilité.
 */
export function VerifiedBadge() {
  return (
    <span
      role="img"
      aria-label="Artiste vérifié"
      className="inline-flex shrink-0 items-center align-middle"
    >
      <svg
        aria-hidden="true"
        viewBox="0 0 16 16"
        className="h-3.5 w-3.5 text-primary"
        fill="none"
      >
        <circle cx="8" cy="8" r="7" fill="currentColor" />
        <path
          d="M4.6 8.2l2.2 2.2 4.6-5"
          stroke="white"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  );
}
