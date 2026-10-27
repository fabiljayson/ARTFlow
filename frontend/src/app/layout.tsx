import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ArtFlow — Marketplace d'art au Cameroun",
  description:
    "ArtFlow : découvrez et achetez des œuvres d'art camerounaises — peintures, sculptures, artisanat et art contemporain.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
