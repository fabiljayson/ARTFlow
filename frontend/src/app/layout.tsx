import type { Metadata } from "next";
import { SiteFooter, SiteHeader } from "@/components/site-header";
import "./globals.css";

export const metadata: Metadata = {
  title: "ArtFlow — Marketplace d'art au Cameroun",
  description:
    "ArtFlow : découvrez et achetez des œuvres d'art camerounaises — peintures, sculptures, artisanat et art contemporain.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="flex min-h-screen flex-col">
        <SiteHeader />
        <div className="flex-1">{children}</div>
        <SiteFooter />
      </body>
    </html>
  );
}
