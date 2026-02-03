import json
import os
import threading
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
STATUS_FILE = DATA_DIR / 'ingestion_status.json'
LOG_FILE = DATA_DIR / 'logs' / 'ingestion.log'

class IngestionManager:
    """
    Manages background ingestion processes and status tracking.
    """
    
    @staticmethod
    def _ensure_paths():
        DATA_DIR.mkdir(exist_ok=True)
        (DATA_DIR / 'logs').mkdir(exist_ok=True, parents=True)
        
    @staticmethod
    def get_status():
        """Read the current ingestion status."""
        IngestionManager._ensure_paths()
        
        if not STATUS_FILE.exists():
            return {
                "status": "idle",
                "message": "No ingestion active",
                "timestamp": datetime.now().isoformat()
            }
            
        try:
            with open(STATUS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to read status: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    @staticmethod
    def start_ingestion(params=None):
        """
        Start the ingestion process in a background thread/process.
        
        params: dict of arguments (e.g., {'mode': 'all', 'laws': 'amparo'})
        """
        IngestionManager._ensure_paths()
        
        # Check if already running
        current_status = IngestionManager.get_status()
        if current_status.get('status') == 'running':
             # Check if process is actually alive (optional, simplistic for now)
             # For now, just return error to prevent duplicates
             return False, "Ingestion already running"

        # Prepare command
        cmd = ["python", "scripts/ingestion/bulk_ingest.py"]
        
        if params:
            if params.get('mode') == 'all':
                cmd.append("--all")
            elif params.get('mode') == 'priority':
                cmd.append("--priority")
                cmd.append(str(params.get('priority_level', 1)))
            elif params.get('mode') == 'specific' and params.get('laws'):
                cmd.append("--laws")
                cmd.append(params['laws'])
            elif params.get('mode') == 'tier' and params.get('tier'):
                cmd.append("--tier")
                cmd.append(params['tier'])
            else:
                # Default to all if nothing specified? Or fail?
                # Let's fail safe
                pass
                
        if params.get('skip_download'):
            cmd.append("--skip-download")
            
        workers = params.get('workers', 4)
        cmd.extend(["--workers", str(workers)])
        
        # Output to status file for the script to update? 
        # Actually the script doesn't currently update 'ingestion_status.json'.
        # We need to wrap it or modify the script to update status.
        # For this iteration, we will wrapp it in a thread here that updates status.
        
        # Write initial running status
        initial_status = {
            "status": "running",
            "message": "Starting ingestion...",
            "progress": 0,
            "total": 0,
            "timestamp": datetime.now().isoformat(),
            "params": params
        }
        with open(STATUS_FILE, 'w') as f:
            json.dump(initial_status, f)
            
        # Spawn thread to run command
        thread = threading.Thread(
            target=IngestionManager._run_process,
            args=(cmd,)
        )
        thread.daemon = True
        thread.start()
        
        return True, "Ingestion started"

    @staticmethod
    def _run_process(cmd):
        """
        Internal method to run the process and capture output. 
        In a real production system, this would be a Celery task.
        """
        try:
            # Open log file
            with open(LOG_FILE, 'a') as log:
                log.write(f"\n\n--- Ingestion started at {datetime.now().isoformat()} ---\n")
                log.write(f"Command: {' '.join(cmd)}\n")
                
                process = subprocess.Popen(
                    cmd,
                    cwd=BASE_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1
                )
                
                # Monitor output to update percentage (dumb parsing for now)
                # Ideally the bulk_ingest.py should write partial status to json.
                # For now, we just stay "running" until done.
                
                for line in process.stdout:
                    log.write(line)
                    # Simple heuristic status update
                    if "Indexing" in line:
                         IngestionManager._update_status_message(line.strip())
                    
                process.wait()
                
            # Completion status
            if process.returncode == 0:
                final_status = "completed"
                msg = "Ingestion finished successfully"
            else:
                final_status = "failed"
                msg = f"Ingestion failed with code {process.returncode}"
                
            with open(STATUS_FILE, 'w') as f:
                json.dump({
                    "status": final_status,
                    "message": msg,
                    "timestamp": datetime.now().isoformat()
                }, f)
                
        except Exception as e:
            with open(STATUS_FILE, 'w') as f:
                json.dump({
                    "status": "error",
                    "message": f"Execution error: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }, f)

    @staticmethod
    def _update_status_message(message):
        """Update just the message/timestamp, keep 'running' status."""
        try:
            if STATUS_FILE.exists():
                with open(STATUS_FILE, 'r') as f:
                    data = json.load(f)
            else:
                data = {"status": "running"}
                
            data['message'] = message
            data['timestamp'] = datetime.now().isoformat()
            
            with open(STATUS_FILE, 'w') as f:
                json.dump(data, f)
        except:
            pass
