import time
import threading
import uuid
from typing import Dict, Any, Optional

class JobStore:
    """
    Simple in-memory store for tracking asynchronous job status and results.
    Jobs are stored in memory and will be lost if the server restarts.
    """
    def __init__(self):
        self.jobs = {}
        self.lock = threading.Lock()
    
    def create_job(self, job_id: str = None, **job_data) -> str:
        """
        Create a new job with optional initial data.
        
        Args:
            job_id: Optional job ID (will generate UUID if not provided)
            **job_data: Additional job metadata
            
        Returns:
            job_id: The ID of the created job
        """
        if job_id is None:
            job_id = str(uuid.uuid4())
            
        now = time.time()
        job = {
            "job_id": job_id,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
            **job_data
        }
        
        with self.lock:
            self.jobs[job_id] = job
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job information by ID.
        
        Args:
            job_id: The job ID to retrieve
            
        Returns:
            Dict containing job information or None if not found
        """
        with self.lock:
            return self.jobs.get(job_id)
    
    def update_job(self, job_id: str, **updates) -> Optional[Dict[str, Any]]:
        """
        Update job information.
        
        Args:
            job_id: The job ID to update
            **updates: Fields to update
            
        Returns:
            Updated job dict or None if job not found
        """
        with self.lock:
            if job_id not in self.jobs:
                return None
            
            self.jobs[job_id].update({
                "updated_at": time.time(),
                **updates
            })
            
            return self.jobs[job_id]
