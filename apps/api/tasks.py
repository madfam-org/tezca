"""
Celery tasks for background processing.
"""

import json
import subprocess
import time
from pathlib import Path

from celery import shared_task
from django.utils import timezone

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
STATUS_FILE = DATA_DIR / "ingestion_status.json"
LOG_FILE = DATA_DIR / "logs" / "ingestion.log"
PIPELINE_STATUS_FILE = DATA_DIR / "pipeline_status.json"
PIPELINE_LOG_FILE = DATA_DIR / "logs" / "pipeline.log"


def _ensure_paths():
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "logs").mkdir(exist_ok=True, parents=True)


def _write_status(data):
    _ensure_paths()
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f)


def _write_pipeline_status(data):
    _ensure_paths()
    with open(PIPELINE_STATUS_FILE, "w") as f:
        json.dump(data, f, default=str)


def _run_subprocess(cmd, log_file, cwd=None):
    """Run a subprocess, stream output to log, return (returncode, last lines)."""
    cwd = cwd or BASE_DIR
    output_lines = []
    with open(log_file, "a") as log:
        log.write(f"\n>>> {' '.join(cmd)}\n")
        log.flush()
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )
        for line in process.stdout:
            log.write(line)
            log.flush()
            output_lines.append(line.rstrip())
            # Keep only last 50 lines in memory
            if len(output_lines) > 50:
                output_lines.pop(0)
        process.wait()
    return process.returncode, output_lines[-10:] if output_lines else []


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


def _build_pipeline_phases(params):
    """Build the list of pipeline phases based on params/skip flags."""
    params = params or {}
    skip_scrape = params.get("skip_scrape", False)
    skip_states = params.get("skip_states", False)
    skip_municipal = params.get("skip_municipal", False)
    skip_municipal_ojn = params.get("skip_municipal_ojn", False)
    skip_parse = params.get("skip_parse", False)
    skip_index = params.get("skip_index", False)
    workers = params.get("workers", 4)

    results_file = str(DATA_DIR / "latest_ingestion_results.json")

    phases = []

    # === PHASE GROUP 1: SCRAPING ===
    if not skip_scrape:
        phases.append(
            {
                "name": "Scrape federal catalog",
                "cmd": ["python", "scripts/scraping/scrape_federal_catalog.py"],
                "cwd": str(BASE_DIR),
            }
        )
        if not skip_states:
            phases.append(
                {
                    "name": "Scrape state laws",
                    "cmd": ["python", "bulk_state_scraper.py"],
                    "cwd": str(BASE_DIR / "scripts" / "scraping"),
                }
            )
        if not skip_municipal:
            phases.append(
                {
                    "name": "Scrape municipal laws",
                    "cmd": ["python", "scripts/scraping/scrape_tier1_cities.py"],
                    "cwd": str(BASE_DIR),
                }
            )
            if not skip_municipal_ojn:
                phases.append(
                    {
                        "name": "Scrape municipal laws (OJN)",
                        "cmd": ["python", "scripts/scraping/bulk_municipal_scraper.py"],
                        "cwd": str(BASE_DIR),
                    }
                )

    # === PHASE GROUP 2: CONSOLIDATE METADATA ===
    # Always consolidate state metadata (needed for ingestion, cheap to run)
    phases.append(
        {
            "name": "Consolidate state metadata",
            "cmd": ["python", "scripts/scraping/consolidate_state_metadata.py"],
            "cwd": str(BASE_DIR),
        }
    )

    if not skip_municipal:
        phases.append(
            {
                "name": "Consolidate municipal metadata",
                "cmd": [
                    "python",
                    "scripts/scraping/consolidate_municipal_metadata.py",
                ],
                "cwd": str(BASE_DIR),
            }
        )

    # === PHASE GROUP 3: PARSE TO AKN XML ===
    if not skip_parse:
        if not skip_states:
            phases.append(
                {
                    "name": "Parse state laws to AKN XML",
                    "cmd": [
                        "python",
                        "scripts/ingestion/parse_state_laws.py",
                        "--all",
                        "--workers",
                        str(workers),
                    ],
                    "cwd": str(BASE_DIR),
                }
            )
        if not skip_municipal:
            phases.append(
                {
                    "name": "Parse municipal laws to AKN XML",
                    "cmd": [
                        "python",
                        "scripts/ingestion/parse_state_laws.py",
                        "--municipal",
                        "--all",
                        "--workers",
                        str(workers),
                    ],
                    "cwd": str(BASE_DIR),
                }
            )

    # === PHASE GROUP 4: DB INGESTION ===
    # Federal ingestion (includes its own parsing via bulk_ingest.py)
    phases.append(
        {
            "name": "Ingest federal laws",
            "cmd": [
                "python",
                "scripts/ingestion/bulk_ingest.py",
                "--all",
                "--force",
                "--workers",
                str(workers),
                "--output",
                results_file,
            ],
            "cwd": str(BASE_DIR),
        }
    )

    # State ingestion (now reads AKN paths from metadata)
    phases.append(
        {
            "name": "Ingest state laws",
            "cmd": ["python", "manage.py", "ingest_state_laws", "--all"],
            "cwd": str(BASE_DIR),
        }
    )

    # Municipal ingestion
    if not skip_municipal:
        phases.append(
            {
                "name": "Ingest municipal laws",
                "cmd": ["python", "manage.py", "ingest_municipal_laws", "--all"],
                "cwd": str(BASE_DIR),
            }
        )

    # === PHASE GROUP 5: ELASTICSEARCH INDEXING ===
    if not skip_index:
        phases.append(
            {
                "name": "Index to Elasticsearch",
                "cmd": [
                    "python",
                    "manage.py",
                    "index_laws",
                    "--all",
                    "--create-indices",
                ],
                "cwd": str(BASE_DIR),
            }
        )

    return phases


def _format_duration(seconds):
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    hours = seconds / 3600
    return f"{hours:.1f}h"


@shared_task(
    bind=True,
    name="apps.api.tasks.run_full_pipeline",
    soft_time_limit=86400,
    time_limit=90000,
)
def run_full_pipeline(self, params=None):
    """
    Run the full data collection pipeline as a Celery task.

    Orchestrates scraping, parsing, DB ingestion, and ES indexing
    as sequential subprocess phases. Errors in one phase do NOT stop
    the pipeline — it continues and reports failures at end.

    Params:
        skip_scrape (bool):   Skip all scraping phases (1-3)
        skip_states (bool):   Skip state law scraping (longest phase)
        skip_municipal (bool): Skip municipal scraping
        skip_index (bool):    Skip ES indexing
        workers (int):        Parallel workers for ingestion (default: 4)
    """
    _ensure_paths()

    phases = _build_pipeline_phases(params)
    total_phases = len(phases)
    started_at = timezone.now()
    task_id = self.request.id if self.request else None

    # Initial status
    _write_pipeline_status(
        {
            "status": "running",
            "message": "Pipeline starting...",
            "phase": phases[0]["name"] if phases else "",
            "phase_number": 0,
            "total_phases": total_phases,
            "progress": 0,
            "started_at": started_at.isoformat(),
            "timestamp": started_at.isoformat(),
            "task_id": task_id,
            "phase_results": [],
        }
    )

    with open(PIPELINE_LOG_FILE, "a") as log:
        log.write(f"\n{'=' * 70}\n")
        log.write(f"PIPELINE STARTED at {started_at.isoformat()}\n")
        log.write(f"Task ID: {task_id}\n")
        log.write(f"Params: {json.dumps(params)}\n")
        log.write(f"Phases: {total_phases}\n")
        log.write(f"{'=' * 70}\n")

    phase_results = []

    # DataOps logging (optional - fails gracefully if models not available)
    pipeline_log = _create_acquisition_log("full_pipeline", params)

    for i, phase in enumerate(phases):
        phase_number = i + 1
        phase_name = phase["name"]
        progress = int((i / total_phases) * 100)

        # Update status: starting phase
        _write_pipeline_status(
            {
                "status": "running",
                "message": f"Phase {phase_number}/{total_phases}: {phase_name}",
                "phase": phase_name,
                "phase_number": phase_number,
                "total_phases": total_phases,
                "progress": progress,
                "started_at": started_at.isoformat(),
                "timestamp": timezone.now().isoformat(),
                "task_id": task_id,
                "phase_results": phase_results,
            }
        )

        with open(PIPELINE_LOG_FILE, "a") as log:
            log.write(f"\n--- Phase {phase_number}/{total_phases}: {phase_name} ---\n")

        phase_start = time.time()

        try:
            returncode, output_tail = _run_subprocess(
                phase["cmd"],
                str(PIPELINE_LOG_FILE),
                cwd=phase.get("cwd"),
            )
            phase_duration = time.time() - phase_start

            result = {
                "phase": phase_name,
                "phase_number": phase_number,
                "returncode": returncode,
                "status": "success" if returncode == 0 else "failed",
                "duration": _format_duration(phase_duration),
                "output_tail": output_tail,
            }
        except Exception as e:
            phase_duration = time.time() - phase_start
            result = {
                "phase": phase_name,
                "phase_number": phase_number,
                "returncode": -1,
                "status": "error",
                "duration": _format_duration(phase_duration),
                "error": str(e),
            }

        phase_results.append(result)

        with open(PIPELINE_LOG_FILE, "a") as log:
            log.write(
                f"--- Phase {phase_number} {result['status'].upper()} "
                f"({result['duration']}) ---\n"
            )

    # Final summary
    completed_at = timezone.now()
    total_duration = (completed_at - started_at).total_seconds()
    succeeded = sum(1 for r in phase_results if r["status"] == "success")
    failed = sum(1 for r in phase_results if r["status"] != "success")

    final_status = "completed" if failed == 0 else "completed_with_errors"

    status_data = {
        "status": final_status,
        "message": (f"Pipeline finished: {succeeded}/{total_phases} phases succeeded"),
        "phase": "done",
        "phase_number": total_phases,
        "total_phases": total_phases,
        "progress": 100,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_human": _format_duration(total_duration),
        "timestamp": completed_at.isoformat(),
        "task_id": task_id,
        "phase_results": phase_results,
        "summary": {
            "total_phases": total_phases,
            "succeeded": succeeded,
            "failed": failed,
        },
    }

    _write_pipeline_status(status_data)

    with open(PIPELINE_LOG_FILE, "a") as log:
        log.write(f"\n{'=' * 70}\n")
        log.write(f"PIPELINE {final_status.upper()} at {completed_at.isoformat()}\n")
        log.write(f"Duration: {_format_duration(total_duration)}\n")
        log.write(f"Succeeded: {succeeded}/{total_phases}\n")
        log.write(f"{'=' * 70}\n")

    # Finalize DataOps log
    _finish_acquisition_log(pipeline_log, succeeded, failed, total_phases)

    return status_data


def _create_acquisition_log(operation, params):
    """Create a DataOps AcquisitionLog entry (fails gracefully)."""
    try:
        from apps.scraper.dataops.models import AcquisitionLog

        return AcquisitionLog.objects.create(
            operation=operation,
            parameters=params or {},
        )
    except Exception:
        return None


def _finish_acquisition_log(log_entry, succeeded, failed, total):
    """Finalize a DataOps AcquisitionLog entry."""
    if log_entry is None:
        return
    try:
        error_summary = ""
        if failed > 0:
            error_summary = f"{failed}/{total} phases failed"
        log_entry.found = total
        log_entry.downloaded = succeeded
        log_entry.failed = failed
        log_entry.ingested = succeeded
        log_entry.finish(error_summary=error_summary)
    except Exception:
        pass
