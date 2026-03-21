"""Management command to verify DOF daily task health."""

import datetime
import json

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verify DOF daily check health over the last N days."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Number of days to look back (default: 7)",
        )
        parser.add_argument(
            "--run-now",
            action="store_true",
            help="Run a manual DOF check for today",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="output_json",
            help="Output structured JSON",
        )

    def handle(self, *args, **options):
        from apps.scraper.dataops.models import AcquisitionLog

        days = options["days"]
        since = datetime.date.today() - datetime.timedelta(days=days)

        logs = AcquisitionLog.objects.filter(
            operation="dof_daily_check",
            started_at__date__gte=since,
        ).order_by("-started_at")

        total_runs = logs.count()
        successful = sum(1 for log in logs if log.finished_at is not None)
        total_entries = sum(log.found for log in logs)
        total_changes = sum(log.ingested for log in logs)

        last_run = logs.first()
        last_run_ts = last_run.started_at.isoformat() if last_run else None
        last_run_changes = last_run.ingested if last_run else 0

        report = {
            "period_days": days,
            "since": since.isoformat(),
            "total_runs": total_runs,
            "successful_runs": successful,
            "success_rate": (
                f"{successful / total_runs * 100:.0f}%" if total_runs else "N/A"
            ),
            "total_entries_found": total_entries,
            "total_changes_detected": total_changes,
            "avg_entries_per_run": (
                round(total_entries / total_runs, 1) if total_runs else 0
            ),
            "last_run": last_run_ts,
            "last_run_changes": last_run_changes,
        }

        if options["output_json"]:
            self.stdout.write(json.dumps(report, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS(f"DOF Health Report ({days} days)"))
            self.stdout.write(f"  Period: {since} to {datetime.date.today()}")
            self.stdout.write(f"  Total runs: {report['total_runs']}")
            self.stdout.write(
                f"  Successful: {report['successful_runs']} ({report['success_rate']})"
            )
            self.stdout.write(f"  Total entries found: {report['total_entries_found']}")
            self.stdout.write(
                f"  Total changes detected: {report['total_changes_detected']}"
            )
            self.stdout.write(f"  Avg entries/run: {report['avg_entries_per_run']}")
            self.stdout.write(f"  Last run: {report['last_run'] or 'Never'}")
            self.stdout.write(f"  Last run changes: {report['last_run_changes']}")

        if options["run_now"]:
            self.stdout.write("\nRunning manual DOF check...")
            from apps.scraper.scheduling.tasks import check_dof_daily

            result = check_dof_daily()
            self.stdout.write(
                self.style.SUCCESS(
                    f"DOF check complete: {result['total_entries']} entries, "
                    f"{result['law_changes']} changes"
                )
            )
            if options["output_json"]:
                report["manual_run"] = result
                self.stdout.write(json.dumps(report, indent=2))
