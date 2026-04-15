"""
Classify laws into legal domains based on keyword matching against law names.

Populates the Law.domains JSONField with legal branch classifications
(labor, fiscal, criminal, etc.) derived from keyword analysis.

Usage:
    python manage.py classify_law_domains --all --dry-run
    python manage.py classify_law_domains --all
    python manage.py classify_law_domains --law-id cpeum
    python manage.py classify_law_domains --all --force
    python manage.py classify_law_domains --all --tier federal
"""

import re
from collections import Counter

from django.core.management.base import BaseCommand

from apps.api.models import Law

# Keyword patterns for domain classification.
# Each key is a domain, values are substrings matched case-insensitively
# against Law.name. A law can match multiple domains.
DOMAIN_KEYWORDS = {
    "labor": [
        "trabajo",
        "trabajador",
        "laboral",
        "empleo",
        "salario",
        "sindic",
        "patronal",
        "jornada",
        "seguro social",
        "imss",
        "infonavit",
        "pensión",
        "pension",
        "jubilaci",
        "aguinaldo",
        "prestacion",
    ],
    "fiscal": [
        "impuesto",
        "tributar",
        "fiscal",
        "hacienda",
        "contribuci",
        "sat ",
        "recaudaci",
        " iva ",
        " isr ",
        " ieps ",
        "arancel",
        "aduana",
        "comercio exterior",
    ],
    "criminal": [
        "penal",
        "delito",
        "crimen",
        "criminal",
        "pena privativa",
        "ministerio público",
        "ministerio publico",
        "sentencia penal",
    ],
    "civil": [
        "civil",
        "propiedad",
        "arrendamiento",
        "sucesi",
        "herencia",
        "matrimonio",
        "divorcio",
    ],
    "commercial": [
        "mercantil",
        "comerci",
        "sociedad",
        "empresa",
        "quiebra",
        "concurso mercantil",
    ],
    "administrative": [
        "administrativ",
        "procedimiento administrativo",
        "servidor público",
        "servidor publico",
        "función pública",
        "funcion publica",
        "licitaci",
        "concesi",
    ],
    "constitutional": [
        "constitución",
        "constitucion",
        "amparo",
        "derechos humanos",
    ],
    "environmental": [
        "ambiente",
        "ambiental",
        "ecológ",
        "ecolog",
        "forestal",
        "residuo",
        "contaminaci",
    ],
    "health": [
        "salud",
        "sanitari",
        "médic",
        "medic",
        "farmac",
        "cofepris",
    ],
    "education": [
        "educaci",
        "escol",
        "universid",
        "académi",
        "academi",
    ],
    "fintech": [
        "fintech",
        "tecnología financiera",
        "tecnologia financiera",
        "institución de tecnología financiera",
        "institucion de tecnologia financiera",
        " itf ",
        "cnbv",
        "sandbox regulatorio",
        "activos virtuales",
        "criptomoneda",
    ],
    "digital_services": [
        "plataforma digital",
        "intermediación digital",
        "intermediacion digital",
        "servicio digital",
        "comercio electrónico",
        "comercio electronico",
        "economía digital",
        "economia digital",
    ],
    "data_protection": [
        "datos personales",
        "privacidad",
        "lfpdppp",
        "protección de datos",
        "proteccion de datos",
        " arco ",
        "aviso de privacidad",
    ],
}


def classify_domains(name: str) -> list[str]:
    """Return list of domain keys matching keywords in the law name."""
    if not name:
        return []
    name_lower = f" {name.lower()} "
    matched = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in name_lower:
                matched.append(domain)
                break
    return matched


class Command(BaseCommand):
    help = "Classify laws into legal domains based on keyword matching."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--all",
            action="store_true",
            help="Process all laws.",
        )
        group.add_argument(
            "--law-id",
            type=str,
            help="Process a single law by official_id.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Classify but do not save to DB.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Number of records per bulk_update batch (default: 500).",
        )
        parser.add_argument(
            "--tier",
            type=str,
            choices=["federal", "state", "municipal", "all"],
            default="all",
            help="Filter by law tier (default: all).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-classify even if domains is already populated.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        tier = options["tier"]
        force = options["force"]
        law_id = options.get("law_id")

        qs = Law.objects.all()

        if law_id:
            qs = qs.filter(official_id=law_id)

        if not force:
            # Skip laws that already have domains populated
            from django.db.models import Q

            qs = qs.filter(Q(domains=[]) | Q(domains__isnull=True))

        if tier != "all":
            qs = qs.filter(tier=tier)

        total = qs.count()
        self.stdout.write(f"Found {total} laws to classify.")
        if dry_run:
            self.stdout.write("DRY RUN — no changes will be saved.")

        classified = 0
        unmatched = 0
        domain_dist = Counter()
        batch = []

        for law in qs.iterator(chunk_size=batch_size):
            domains = classify_domains(law.name)
            law.domains = domains

            if domains:
                classified += 1
                for d in domains:
                    domain_dist[d] += 1
            else:
                unmatched += 1

            batch.append(law)

            if len(batch) >= batch_size and not dry_run:
                Law.objects.bulk_update(batch, ["domains"], batch_size=batch_size)
                batch = []

        # Flush remaining
        if batch and not dry_run:
            Law.objects.bulk_update(batch, ["domains"], batch_size=batch_size)

        # Summary
        self.stdout.write("\n--- Summary ---")
        self.stdout.write(f"Total:        {total}")
        self.stdout.write(f"Classified:   {classified}")
        self.stdout.write(f"Unmatched:    {unmatched}")
        self.stdout.write("Domain distribution:")
        for domain, count in domain_dist.most_common():
            self.stdout.write(f"  {domain}: {count}")

        if dry_run:
            self.stdout.write("\nDRY RUN — no changes were saved.")
