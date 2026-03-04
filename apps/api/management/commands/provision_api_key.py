"""
Management command to provision API keys without the admin UI.

Usage:
    python manage.py provision_api_key \
        --name "Forgesight Prod" \
        --email ops@madfam.io \
        --org "MADFAM" \
        --tier internal \
        --scopes read,search,bulk \
        --domains manufacturing,commerce,foreign_trade
"""

from django.core.management.base import BaseCommand

from apps.api.apikeys import generate_api_key
from apps.api.constants import DOMAIN_MAP
from apps.api.models import APIKey


class Command(BaseCommand):
    help = "Provision an API key for programmatic access"

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Key display name")
        parser.add_argument("--email", required=True, help="Owner email")
        parser.add_argument("--org", default="", help="Organization name")
        parser.add_argument(
            "--tier",
            default="free",
            choices=[c[0] for c in APIKey.Tier.choices],
            help="Rate-limit tier (default: free)",
        )
        parser.add_argument(
            "--scopes",
            default="read,search",
            help="Comma-separated scopes (default: read,search)",
        )
        parser.add_argument(
            "--domains",
            default="",
            help="Comma-separated domain filter (empty = all domains)",
        )

    def handle(self, **options):
        scopes = [s.strip() for s in options["scopes"].split(",") if s.strip()]
        domains = [d.strip() for d in options["domains"].split(",") if d.strip()]

        # Validate domains against DOMAIN_MAP
        for d in domains:
            if d not in DOMAIN_MAP:
                self.stderr.write(
                    self.style.ERROR(
                        f"Unknown domain '{d}'. Valid: {', '.join(sorted(DOMAIN_MAP))}"
                    )
                )
                return

        full_key, prefix, hashed = generate_api_key()

        api_key = APIKey.objects.create(
            prefix=prefix,
            hashed_key=hashed,
            name=options["name"],
            owner_email=options["email"],
            organization=options["org"],
            tier=options["tier"],
            scopes=scopes,
            allowed_domains=domains,
        )

        self.stdout.write(self.style.SUCCESS(f"Created API key: {api_key.name}"))
        self.stdout.write(self.style.SUCCESS(f"Tier: {api_key.tier}"))
        self.stdout.write(self.style.SUCCESS(f"Scopes: {scopes}"))
        self.stdout.write(self.style.SUCCESS(f"Domains: {domains or 'all'}"))
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Full key (shown once, save it now):"))
        self.stdout.write(full_key)
