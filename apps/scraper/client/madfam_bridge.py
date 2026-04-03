"""
Madfam Crawler Bridge Client

An asynchronous wrapper allowing Tezca scrapers to securely delegate
heavy headless browser DOM processing to the central `madfam-crawler` architecture.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

class MadfamBridge:
    def __init__(self, endpoint: str = "http://madfam-crawler:8000/v1/crawl"):
        self.endpoint = endpoint
        self.poll_interval = 5.0  # seconds
    
    def extract_sync(
        self, 
        url: str, 
        extraction_prompt: str, 
        schema_definition: Dict[str, Any],
        timeout: float = 60.0
    ) -> Optional[Dict[str, Any]]:
        """Synchronous extraction method for legacy block-based scrapers."""
        payload = {
            "url": url,
            "extraction_prompt": extraction_prompt,
            "schema_definition": schema_definition,
            "source_app": "tezca"
        }
        
        with httpx.Client(timeout=10.0) as client:
            try:
                logger.info(f"[MadfamBridge] Enqueueing scrape for {url}")
                response = client.post(self.endpoint, json=payload)
                if response.status_code != 202:
                    logger.error(f"[MadfamBridge] Broker rejected task. HTTP {response.status_code}")
                    return None
                    
                task_id = response.json().get("task_id")
                logger.info(f"[MadfamBridge] Task {task_id} received. Polling...")
                
                elapsed = 0.0
                while elapsed < timeout:
                    status_resp = client.get(f"{self.endpoint}/{task_id}")
                    if status_resp.status_code == 200:
                        data = status_resp.json()
                        status = data.get("status")
                        
                        if status == "SUCCESS":
                            return data.get("result", {}).get("structured_data", {})
                        elif status == "FAILURE":
                            return None
                    
                    time.sleep(self.poll_interval)
                    elapsed += self.poll_interval
                    
                return None
            except Exception as e:
                logger.error(f"[MadfamBridge] Communication error: {e}", exc_info=True)
                return None

    async def extract(
        self, 
        url: str, 
        extraction_prompt: str, 
        schema_definition: Dict[str, Any],
        timeout: float = 60.0
    ) -> Optional[Dict[str, Any]]:
        """Delegates LLM extraction to madfam-crawler."""
        payload = {
            "url": url,
            "extraction_prompt": extraction_prompt,
            "schema_definition": schema_definition,
            "source_app": "tezca"
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # 1. Dispatch
                logger.info(f"[MadfamBridge] Enqueueing scrape for {url}")
                response = await client.post(self.endpoint, json=payload)
                if response.status_code != 202:
                    logger.error(f"[MadfamBridge] Broker rejected task. HTTP {response.status_code} - {response.text}")
                    return None
                    
                task_id = response.json().get("task_id")
                
                # 2. Poll
                logger.info(f"[MadfamBridge] Task {task_id} received. Polling...")
                
                elapsed = 0.0
                while elapsed < timeout:
                    status_resp = await client.get(f"{self.endpoint}/{task_id}")
                    if status_resp.status_code == 200:
                        data = status_resp.json()
                        status = data.get("status")
                        
                        if status == "SUCCESS":
                            logger.info(f"[MadfamBridge] Scrape completed for {url}")
                            return data.get("result", {}).get("structured_data", {})
                        elif status == "FAILURE":
                            logger.error(f"[MadfamBridge] Worker failed task {task_id}: {data.get('error')}")
                            return None
                    
                    await asyncio.sleep(self.poll_interval)
                    elapsed += self.poll_interval
                    
                logger.error(f"[MadfamBridge] Task {task_id} timed out after {timeout}s.")
                return None
                
            except Exception as e:
                logger.error(f"[MadfamBridge] Communication error: {e}", exc_info=True)
                return None
