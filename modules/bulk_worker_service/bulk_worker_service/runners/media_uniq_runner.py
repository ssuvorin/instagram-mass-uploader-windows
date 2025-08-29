"""Comprehensive Media Uniquification Runner for Distributed Workers

Implements per-worker video uniquification with full SOLID principles compliance.
"""

from __future__ import annotations
import os
import asyncio
from typing import Tuple, Optional

from ..ui_client import UiClient
from ..domain import MediaUniqAggregate
from ..media_processing import (
    media_factory, ProcessingStatus, MediaProcessingOrchestrator
)
from ..config import settings


class MediaUniquificationRunner:
    """Runner for media uniquification tasks following Single Responsibility Principle"""
    
    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self.orchestrator: Optional[MediaProcessingOrchestrator] = None
    
    async def initialize(self) -> None:
        """Initialize the processing orchestrator"""
        output_dir = getattr(settings, 'MEDIA_OUTPUT_DIR', '/tmp/processed_media')
        self.orchestrator = media_factory.create_orchestrator(
            worker_id=self.worker_id,
            output_dir=output_dir,
            processing_type="uniquification"
        )
    
    async def run_job(self, ui: UiClient, task_id: int) -> Tuple[int, int]:
        """Execute media uniquification job with comprehensive error handling"""
        if not self.orchestrator:
            await self.initialize()
        
        try:
            # Update task status
            await ui.update_task_status_generic('media_uniq', task_id, status="RUNNING")
            
            # Get task aggregate data
            agg_json = await ui.get_aggregate('media_uniq', task_id)
            agg = MediaUniqAggregate.model_validate(agg_json)
            
            # Prepare video data for processing
            video_data = [
                {
                    'id': v.id,
                    'url': getattr(v, 'url', None) or await ui.get_video_download_url(v.id)
                }
                for v in agg.videos
            ]
            
            # Process videos with progress tracking
            results = await self.orchestrator.process_video_batch(
                video_data,
                progress_callback=self._create_progress_callback(ui, task_id)
            )
            
            # Calculate success/failure counts
            success_count = sum(1 for r in results if r.status == ProcessingStatus.COMPLETED)
            failure_count = sum(1 for r in results if r.status == ProcessingStatus.FAILED)
            skipped_count = sum(1 for r in results if r.status == ProcessingStatus.SKIPPED)
            
            # Update final task status
            final_status = self._determine_final_status(success_count, failure_count, skipped_count)
            await ui.update_task_status_generic('media_uniq', task_id, status=final_status)
            
            # Log processing metrics
            metrics = self.orchestrator.get_metrics()
            await ui.update_task_status_generic(
                'media_uniq', 
                task_id, 
                log_append=f"Processing completed: {success_count} successful, "
                          f"{failure_count} failed, {skipped_count} skipped. "
                          f"Average processing time: {metrics.average_processing_time:.2f}s\n"
            )
            
            return success_count, failure_count
            
        except Exception as e:
            await ui.update_task_status_generic(
                'media_uniq', 
                task_id, 
                status="FAILED",
                log_append=f"Critical error in media uniquification: {str(e)}\n"
            )
            return 0, len(agg.videos) if 'agg' in locals() else 1
        
        finally:
            # Cleanup resources
            if self.orchestrator:
                await self.orchestrator.cleanup()
    
    def _create_progress_callback(self, ui: UiClient, task_id: int):
        """Create progress callback for real-time updates"""
        async def progress_callback(current: int, total: int, result):
            percentage = int((current / total) * 100) if total > 0 else 0
            
            await ui.update_task_status_generic(
                'media_uniq',
                task_id,
                log_append=f"[{percentage}%] Processed video {result.video_id}: "
                          f"{result.status.value} ({self.worker_id})\n"
            )
        
        return progress_callback
    
    def _determine_final_status(self, success: int, failed: int, skipped: int) -> str:
        """Determine final task status based on results"""
        if failed == 0 and success > 0:
            return "COMPLETED"
        elif success > 0:
            return "PARTIALLY_COMPLETED"
        elif failed > 0:
            return "FAILED"
        else:
            return "COMPLETED"  # All skipped (no work for this worker)


# Global runner instance
_runner_instance: Optional[MediaUniquificationRunner] = None


def get_runner(worker_id: str) -> MediaUniquificationRunner:
    """Get or create runner instance (Singleton pattern)"""
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = MediaUniquificationRunner(worker_id)
    return _runner_instance


async def run_media_uniq_job(ui: UiClient, task_id: int) -> Tuple[int, int]:
    """Legacy interface for backward compatibility"""
    # Get worker ID from settings or generate one
    worker_id = getattr(settings, 'WORKER_ID', f"worker_{os.getpid()}")
    
    runner = get_runner(worker_id)
    return await runner.run_job(ui, task_id) 