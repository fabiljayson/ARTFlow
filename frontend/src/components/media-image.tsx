import Image from "next/image";
import { proxiedUrl } from "@/lib/api";

type Props = {
  src: string | null;
  alt: string;
  fill?: boolean;
  sizes?: string;
  className?: string;
  priority?: boolean;
};

/**
 * Image de média ArtFlow.
 *
 * Le backend renvoie les URLs de médias en absolu (`http://127.0.0.1:8003/...`),
 * ce qui contiournerait le proxy Next. On les réécrit en relatif (`/api/v1/...`)
 * pour rester sur la même origine que la page, cookies et CSRF compris.
 */
export function MediaImage({ src, alt, fill, sizes, className, priority }: Props) {
  const resolved = proxiedUrl(src);

  if (!resolved) {
    return (
      <div
        className={
          fill
            ? "flex h-full w-full items-center justify-center bg-surface-muted text-xs text-text/50"
            : "flex h-48 w-full items-center justify-center bg-surface-muted text-xs text-text/50"
        }
      >
        Pas d&apos;image
      </div>
    );
  }

  return (
    <Image
      src={resolved}
      alt={alt}
      fill={fill}
      sizes={sizes}
      className={className}
      priority={priority}
    />
  );
}
