"""Seed catalogue categories (idempotent)."""
from django.core.management.base import BaseCommand

from apps.catalogue.models import Category

ROOT_CATEGORIES = [
    ("peinture", "Peinture", "Painting", 0),
    ("sculpture", "Sculpture", "Sculpture", 1),
    ("artisanat", "Artisanat", "Craft", 2),
    ("photographie", "Photographie", "Photography", 3),
    ("art-contemporain", "Art contemporain", "Contemporary art", 4),
    ("textile", "Textile", "Textile", 5),
]

SUB_CATEGORIES = {
    "peinture": [
        ("peinture-huile", "Huile", "Oil", 0),
        ("peinture-aquarelle", "Aquarelle", "Watercolour", 1),
        ("peinture-acrylique", "Acrylique", "Acrylic", 2),
    ],
    "artisanat": [
        ("vannerie", "Vannerie", "Basketry", 0),
        ("poterie", "Poterie", "Pottery", 1),
        ("bois-sculpte", "Bois sculpté", "Carved wood", 2),
    ],
}


class Command(BaseCommand):
    help = "Seed catalogue categories (idempotent — skips existing slugs)."

    def handle(self, *args, **options):
        created = 0
        parents = {}
        for slug, name_fr, name_en, position in ROOT_CATEGORIES:
            obj, was_created = Category.objects.get_or_create(
                slug=slug,
                defaults={"name_fr": name_fr, "name_en": name_en, "position": position, "is_active": True},
            )
            parents[slug] = obj
            created += int(was_created)

        for parent_slug, children in SUB_CATEGORIES.items():
            parent = parents.get(parent_slug) or Category.objects.filter(slug=parent_slug).first()
            if parent is None:
                continue
            for slug, name_fr, name_en, position in children:
                _, was_created = Category.objects.get_or_create(
                    slug=slug,
                    defaults={
                        "name_fr": name_fr,
                        "name_en": name_en,
                        "position": position,
                        "is_active": True,
                        "parent": parent,
                    },
                )
                created += int(was_created)

        self.stdout.write(
            self.style.SUCCESS(f"Categories ready ({created} created, {Category.objects.count()} total).")
        )
