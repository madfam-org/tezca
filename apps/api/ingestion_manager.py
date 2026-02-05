import json
import os
import subprocess
import threading
import time
from pathlib import Path

from django.utils import timezone

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
STATUS_FILE = DATA_DIR / "ingestion_status.json"
LOG_FILE = DATA_DIR / "logs" / "ingestion.log"


class IngestionManager:
    """
    Manages background ingestion processes and status tracking.

    Uses Celery when available (production), falls back to threads (local dev).
    """

    @staticmethod
    def _ensure_paths():
        DATA_DIR.mkdir(exist_ok=True)
        (DATA_DIR / "logs").mkdir(exist_ok=True, parents=True)

    @staticmethod
    def get_status():
        """Read the current ingestion status."""
        IngestionManager._ensure_paths()

        if not STATUS_FILE.exists():
            return {
                "status": "idle",
                "message": "No ingestion active",
                "timestamp": timezone.now().isoformat(),
            }

        try:
            with open(STATUS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to read status: {str(e)}",
                "timestamp": timezone.now().isoformat(),
            }

    @staticmethod
    def start_ingestion(params=None):
        """
        Start the ingestion process.

        Tries Celery first; falls back to thread-based execution if
        the broker is unavailable (e.g. local dev without Redis).
        """
        IngestionManager._ensure_paths()

        # Check if already running
        current_status = IngestionManager.get_status()
        if current_status.get("status") == "running":
            return False, "Ingestion already running"

        # Try Celery first
        try:
            from apps.api.tasks import run_ingestion

            result = run_ingestion.delay(params)
            return True, f"Ingestion started (task {result.id})"
        except Exception:
            # Celery/Redis unavailable — fall back to thread
            pass

        # Fallback: thread-based execution
        cmd = IngestionManager._build_command(params)
        results_file = DATA_DIR / "latest_ingestion_results.json"
        cmd.extend(["--output", str(results_file)])

        # Write initial running status
        initial_status = {
            "status": "running",
            "message": "Starting ingestion (thread fallback)...",
            "progress": 0,
            "total": 0,
            "timestamp": timezone.now().isoformat(),
            "params": params,
        }
        with open(STATUS_FILE, "w") as f:
            json.dump(initial_status, f)

        thread = threading.Thread(
            target=IngestionManager._run_process, args=(cmd, results_file)
        )
        thread.daemon = True
        thread.start()

        return True, "Ingestion started (thread fallback)"

    @staticmethod
    def _build_command(params):
        """Build the subprocess command from params."""
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

        return cmd

    @staticmethod
    def _run_process(cmd, results_file=None):
        """
        Thread-based fallback for running ingestion when Celery is unavailable.
        """
        try:
            with open(LOG_FILE, "a") as log:
                log.write(
                    f"\n\n--- Ingestion started at {timezone.now().isoformat()} ---\n"
                )
                log.write(f"Command: {' '.join(cmd)}\n")

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
                        IngestionManager._update_status_message(line.strip())

                process.wait()

            status_data = {"timestamp": timezone.now().isoformat()}

            if process.returncode == 0:
                status_data["status"] = "completed"
                status_data["message"] = "Ingestion finished successfully"

                if results_file and results_file.exists():
                    try:
                        with open(results_file, "r") as f:
                            results = json.load(f)
                            status_data["results"] = results
                    except Exception as e:
                        status_data["warning"] = f"Could not read results file: {e}"
            else:
                status_data["status"] = "failed"
                status_data["message"] = (
                    f"Ingestion failed with code {process.returncode}"
                )

            with open(STATUS_FILE, "w") as f:
                json.dump(status_data, f)

        except Exception as e:
            with open(STATUS_FILE, "w") as f:
                json.dump(
                    {
                        "status": "error",
                        "message": f"Execution error: {str(e)}",
                        "timestamp": timezone.now().isoformat(),
                    },
                    f,
                )

    @staticmethod
    def _update_status_message(message):
        """Update just the message/timestamp, keep 'running' status."""
        try:
            if STATUS_FILE.exists():
                with open(STATUS_FILE, "r") as f:
                    data = json.load(f)
            else:
                data = {"status": "running"}

            data["message"] = message
            data["timestamp"] = timezone.now().isoformat()

            with open(STATUS_FILE, "w") as f:
                json.dump(data, f)
        except Exception:
            pass
