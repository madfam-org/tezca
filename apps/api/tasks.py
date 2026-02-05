"""
Celery tasks for background processing.
"""

import json
import subprocess
from pathlib import Path

from celery import shared_task
from django.utils import timezone

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
STATUS_FILE = DATA_DIR / "ingestion_status.json"
LOG_FILE = DATA_DIR / "logs" / "ingestion.log"


def _ensure_paths():
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "logs").mkdir(exist_ok=True, parents=True)


def _write_status(data):
    _ensure_paths()
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f)


@shared_task(bind=True, name="apps.api.tasks.run_ingestion")
def run_ingestion(self, params=None):
    """
    Run the ingestion pipeline as a Celery task.

    Replaces the old thread-based IngestionManager._run_process().
    The task updates a JSON status file that the API reads for progress.
    """
    _ensure_paths()

    # Build command
    cmd = ["python", "scripts/ingestion/bulk_ingest.py"]

    if params:
        mode = params.get("mode", "all")
        if mode == "all":
            cmd.append("--all")
        elif mode == "priority":
            cmd.append("--priority")
            cmd.append(str(params.get("priority_level", 1)))
        elif mode == "specific" and params.get("laws"):
            cmd.extend(["--laws", params["laws"]])
        elif mode == "tier" and params.get("tier"):
            cmd.extend(["--tier", params["tier"]])

        if params.get("skip_download"):
            cmd.append("--skip-download")

        workers = params.get("workers", 4)
        cmd.extend(["--workers", str(workers)])

    results_file = DATA_DIR / "latest_ingestion_results.json"
    cmd.extend(["--output", str(results_file)])

    # Write initial running status
    _write_status(
        {
            "status": "running",
            "message": "Starting ingestion...",
            "progress": 0,
            "timestamp": timezone.now().isoformat(),
            "params": params,
            "task_id": self.request.id,
        }
    )

    try:
        with open(LOG_FILE, "a") as log:
            log.write(
                f"\n\n--- Ingestion started at {timezone.now().isoformat()} ---\n"
            )
            log.write(f"Command: {' '.join(cmd)}\n")
            log.write(f"Celery task ID: {self.request.id}\n")

            process = subprocess.Popen(
                cmd,
                cwd=BASE_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )

            for line in process.stdout:
                log.write(line)
                if "Indexing" in line:
                    _write_status(
                        {
                            "status": "running",
                            "message": line.strip(),
                            "timestamp": timezone.now().isoformat(),
                            "task_id": self.request.id,
                        }
                    )

            process.wait()

        # Completion status
        status_data = {
            "timestamp": timezone.now().isoformat(),
            "task_id": self.request.id,
        }

        if process.returncode == 0:
            status_data["status"] = "completed"
            status_data["message"] = "Ingestion finished successfully"

            if results_file.exists():
                try:
                    with open(results_file, "r") as f:
                        status_data["results"] = json.load(f)
                except Exception as e:
                    status_data["warning"] = f"Could not read results file: {e}"
        else:
            status_data["status"] = "failed"
            status_data["message"] = f"Ingestion failed with code {process.returncode}"

        _write_status(status_data)
        return status_data

    except Exception as e:
        error_status = {
            "status": "error",
            "message": f"Execution error: {str(e)}",
            "timestamp": timezone.now().isoformat(),
            "task_id": self.request.id,
        }
        _write_status(error_status)
        raise
