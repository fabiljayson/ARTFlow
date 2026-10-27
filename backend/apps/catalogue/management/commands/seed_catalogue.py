"""Seed the catalogue with artworks, media and a video feed.

Idempotent: keyed on the artwork slug. Generates its own media (Pillow for
images, ffmpeg for the sample video) so the seed never depends on files
committed to the repo. Covers every ArtworkStatus so the artist space and the
moderation queue have realistic content to display.
"""
import io
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from apps.artists.models import ApplicationStatus, ArtistProfile
from apps.catalogue.media_service import make_thumbnail
from apps.catalogue.models import Artwork, ArtworkStatus, Category

User = get_user_model()

SEED_PASSWORD = "Str0ng!Passw0rd2026"


def _hex(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def _make_image(*, size: tuple[int, int], base: str, accent: str, seed: int) -> bytes:
    """A deterministic abstract composition so cards are visually distinct."""
    from PIL import Image, ImageDraw

    width, height = size
    image = Image.new("RGB", size, _hex(base))
    draw = ImageDraw.Draw(image)

    # Diagonal accent bands.
    step = 40 + (seed % 5) * 12
    for offset in range(-height, width + height, step):
        draw.line(
            [(offset, 0), (offset + height, height)],
            fill=_hex(accent),
            width=6 + (seed % 4) * 3,
        )

    # A soft focal shape, position driven by the seed.
    cx = width // 3 + (seed * 37) % (width // 3)
    cy = height // 3 + (seed * 53) % (height // 3)
    radius = min(width, height) // 5 + (seed % 3) * 10
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        outline=_hex(accent),
        width=8,
    )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _make_video(path: Path) -> None:
    """A short silent MP4 (motion = a panning colour wash)."""
    if shutil.which("ffmpeg") is None:
        raise CommandError("ffmpeg introuvable : requis pour générer la vidéo seed.")
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=size=640x360:rate=15:duration=4",
            "-pix_fmt", "yuv420p", "-c:v", "libx264", "-profile:v", "baseline",
            "-movflags", "+faststart", str(path),
        ],
        check=True,
    )


# slug, title, category slug, price XAF, stock, status, alt text, palette, seed
ARTWORKS = [
    ("le-marche-de-ndop", "Marché de Ndop", "peinture-huile", 185_000, 1,
     ArtworkStatus.PUBLISHED, "Scène de marché en pigments chauds", ("#7c2d12", "#d97706"), 1),
    ("masque-wouri", "Masque du Wouri", "sculpture", 320_000, 1,
     ArtworkStatus.PUBLISHED, "Masque sculpté dans le bois sombre", ("#3f1d0b", "#a16207"), 2),
    ("vannerie-bafia", "Vannerie de Bafia", "vannerie", 45_000, 6,
     ArtworkStatus.PUBLISHED, "Panier tressé aux fibres naturelles", ("#4d3319", "#ca8a04"), 3),
    ("lagune-egalune", "Lagune à Ékéla", "photographie", 78_000, 3,
     ArtworkStatus.PUBLISHED, "Reflets sur la lagune au petit matin", ("#0c4a6e", "#38bdf8"), 4),
    ("terre-de-douala", "Terre de Douala", "art-contemporain", 950_000, 1,
     ArtworkStatus.PUBLISHED, "Installation contemporaine sur la terre rouge", ("#450a0a", "#b91c1c"), 5),
    ("pagne-fachu", "Pagne Fàchu", "textile", 26_500, 12,
     ArtworkStatus.PUBLISHED, "Motifs géométriques teints à la main", ("#3b0764", "#a855f7"), 6),
    ("torse-douala", "Torse de Douala", "sculpture", 145_000, 2,
     ArtworkStatus.PUBLISHED, "Sculpture figurative en bois sculpté", ("#292524", "#a16207"), 7),
    ("poterie-foumban", "Jarre de Foumban", "poterie", 38_000, 5,
     ArtworkStatus.PUBLISHED, "Céramique tournée aux lignes sobres", ("#78350f", "#f59e0b"), 8),
    ("etoile-sur-lesau", "Étoile sur le Sanaga", "peinture-aquarelle", 62_000, 0,
     ArtworkStatus.PUBLISHED, "Aquarelle d'un ciel au-dessus du fleuve", ("#1e3a8a", "#60a5fa"), 9),
    ("portrait-ndaoundere", "Portrait de Ngaoundéré", "peinture-acrylique", 110_000, 1,
     ArtworkStatus.IN_MODERATION, "Portrait en aplats colorés", ("#064e3b", "#10b981"), 10),
    ("aube-sur-mounGO", "Aube sur MunGO", "peinture-huile", 88_000, 1,
     ArtworkStatus.IN_MODERATION, "Paysage urbain à l'aube", ("#1e293b", "#f97316"), 11),
    ("esquisse-atelier", "Esquisse d'atelier", "peinture-aquarelle", 15_000, 1,
     ArtworkStatus.DRAFT, "Étude préparatoire au fusain", ("#27272a", "#a1a1aa"), 12),
    ("maquette-cameroun", "Maquette du Cameroun", "art-contemporain", 2_400_000, 1,
     ArtworkStatus.REFUSED, "Maquette monumentale refusée", ("#451a03", "#ea580c"), 13),
    ("relief-ouest", "Relief de l'Ouest", "sculpture", 210_000, 1,
     ArtworkStatus.ARCHIVED, "Relief en bas-relief archivé", ("#14532d", "#22c55e"), 14),
]

ALT_EN = "Artwork from the ArtFlow seed catalogue"


class Command(BaseCommand):
    help = "Seed the catalogue: artists, artworks across every status, images and a video."

    def handle(self, *args, **options):
        category_by_slug = {c.slug: c for c in Category.objects.filter(is_active=True)}
        if not category_by_slug:
            raise CommandError("Aucune catégorie. Lancez d'abord `seed_categories`.")

        created_artworks = 0
        created_media = 0

        profile = (
            ArtistProfile.objects.filter(status=ApplicationStatus.APPROVED)
            .order_by("-id")
            .first()
        )
        if profile is None:
            raise CommandError("Aucun profil artiste approuvé. Lancez d'abord le seed d'authentification.")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for index, (slug, title, cat_slug, price, stock, status, alt, palette, seed) in enumerate(
                ARTWORKS
            ):
                category = category_by_slug.get(cat_slug)
                if category is None:
                    self.stdout.write(self.style.WARNING(f"  catégorie inconnue: {cat_slug} — ignorée"))
                    continue

                artwork, was_created = Artwork.objects.get_or_create(
                    slug=slug,
                    defaults={
                        "artist": profile,
                        "title": title,
                        "description": f"{title} — œuvre du seed ArtFlow, catégorie {category.name_fr}.",
                        "category": category,
                        "price_xaf": price,
                        "stock_quantity": stock,
                        "status": status,
                        "dimensions": "60 × 80 cm",
                        "materials": "Technique mixte sur toile",
                        "technique": "Peinture",
                        "year_created": 2024,
                        "is_unique_piece": stock <= 1,
                    },
                )
                created_artworks += int(was_created)

                if not was_created:
                    continue

                if status == ArtworkStatus.PUBLISHED or index % 3 == 0:
                    png = _make_image(size=(800, 1000), base=palette[0], accent=palette[1], seed=seed)
                    media = self._add_image(artwork, png, alt=alt, is_primary=True, position=0)
                    created_media += int(media)

                    detail = _make_image(size=(800, 1000), base=palette[1], accent=palette[0], seed=seed + 50)
                    media = self._add_image(artwork, detail, alt=f"{alt} — détail", is_primary=False, position=1)
                    created_media += int(media)

                if slug == "le-marche-de-ndop":
                    video_path = tmp_path / "sample.mp4"
                    if not video_path.exists():
                        _make_video(video_path)
                    media = self._add_video(artwork, video_path.read_bytes(), position=2)
                    created_media += int(media)

                if status == ArtworkStatus.PUBLISHED and not artwork.published_at:
                    from django.utils import timezone

                    artwork.published_at = timezone.now()
                    artwork.save(update_fields=["published_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Catalogue seed: {created_artworks} œuvres, {created_media} médias "
                f"({Artwork.objects.count()} au total)."
            )
        )

    def _add_image(self, artwork: Artwork, png: bytes, *, alt: str, is_primary: bool, position: int) -> bool:
        from apps.catalogue.models import ArtworkMedia, MediaKind

        if artwork.media.filter(kind=MediaKind.IMAGE, position=position).exists():
            return False
        media = ArtworkMedia(
            artwork=artwork,
            kind=MediaKind.IMAGE,
            position=position,
            alt_text_fr=alt,
            alt_text_en=ALT_EN,
            is_primary=is_primary,
            content_type="image/png",
            size_bytes=len(png),
        )
        media.file.save(f"{artwork.slug}-{position}.png", ContentFile(png), save=False)
        # Generate the thumbnail through the same service the upload flow uses.
        thumb_bytes = make_thumbnail(io.BytesIO(png))
        media.thumbnail_file.save(
            f"thumb_{artwork.slug}-{position}.png", ContentFile(thumb_bytes), save=False
        )
        media.width_px, media.height_px = 800, 1000
        media.save()
        return True

    def _add_video(self, artwork: Artwork, mp4: bytes, *, position: int) -> bool:
        from apps.catalogue.models import ArtworkMedia, MediaKind

        if artwork.media.filter(kind=MediaKind.VIDEO).exists():
            return False
        media = ArtworkMedia(
            artwork=artwork,
            kind=MediaKind.VIDEO,
            position=position,
            alt_text_fr="Vidéo de l'œuvre",
            alt_text_en=ALT_EN,
            content_type="video/mp4",
            size_bytes=len(mp4),
        )
        media.file.save(f"{artwork.slug}.mp4", ContentFile(mp4), save=False)
        media.save()
        return True
