"""
Comprehensive Media Processing System for Distributed Workers

This module implements video uniquification and processing capabilities
following SOLID, CLEAN, KISS, DRY, and OOP principles.
"""

from __future__ import annotations
import os
import time
import asyncio
import hashlib
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Protocol
from dataclasses import dataclass
from enum import Enum

# Import uniquifier from main project
from uploader.async_video_uniquifier import AsyncVideoUniquifier


class ProcessingStatus(Enum):
    """Video processing status enumeration"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class VideoProcessingResult:
    """Result of video processing operation"""
    video_id: int
    status: ProcessingStatus
    original_path: str
    processed_path: Optional[str] = None
    processing_time: float = 0.0
    error_message: Optional[str] = None
    worker_id: Optional[str] = None


@dataclass
class ProcessingMetrics:
    """Processing metrics for monitoring"""
    total_videos: int = 0
    processed_videos: int = 0
    failed_videos: int = 0
    skipped_videos: int = 0
    total_processing_time: float = 0.0
    average_processing_time: float = 0.0


class IVideoProcessor(Protocol):
    """Interface for video processing operations"""
    
    async def process_video(
        self, 
        video_path: str, 
        output_path: str,
        worker_id: str
    ) -> bool:
        """Process a single video file"""
        ...
    
    async def validate_video(self, video_path: str) -> bool:
        """Validate video file integrity"""
        ...


class IProcessingStrategy(ABC):
    """Abstract strategy for video processing"""
    
    @abstractmethod
    async def should_process(self, video_id: int, worker_id: str) -> bool:
        """Determine if video should be processed by this worker"""
        pass
    
    @abstractmethod
    async def get_output_path(self, video_id: int, worker_id: str) -> str:
        """Get output path for processed video"""
        pass


class PerWorkerProcessingStrategy(IProcessingStrategy):
    """Strategy that ensures each worker processes videos uniquely"""
    
    def __init__(self, base_output_dir: str):
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
    
    async def should_process(self, video_id: int, worker_id: str) -> bool:
        """Each worker processes videos based on hash distribution"""
        # Use consistent hashing to distribute videos across workers
        video_hash = hashlib.md5(str(video_id).encode()).hexdigest()
        worker_hash = hashlib.md5(worker_id.encode()).hexdigest()
        
        # Simple distribution: video hash modulo should match worker position
        return int(video_hash, 16) % 10 == int(worker_hash, 16) % 10
    
    async def get_output_path(self, video_id: int, worker_id: str) -> str:
        """Get unique output path for this worker and video"""
        worker_dir = self.base_output_dir / f"worker_{worker_id}"
        worker_dir.mkdir(exist_ok=True)
        
        timestamp = int(time.time())
        filename = f"video_{video_id}_{timestamp}.mp4"
        
        return str(worker_dir / filename)


class UniquificationProcessor(IVideoProcessor):
    """Video processor using AsyncVideoUniquifier"""
    
    def __init__(self):
        self.uniquifier = AsyncVideoUniquifier()
    
    async def process_video(
        self, 
        video_path: str, 
        output_path: str,
        worker_id: str
    ) -> bool:
        """Process video using uniquification"""
        try:
            # Create unique suffix based on worker ID
            unique_suffix = f"worker_{worker_id}_{int(time.time())}"
            
            # Use AsyncVideoUniquifier from main project
            result_path = await self.uniquifier.uniquify_video_async(
                video_path, 
                unique_suffix
            )
            
            if result_path and os.path.exists(result_path):
                # Move result to final output path
                os.rename(result_path, output_path)
                return True
            
            return False
            
        except Exception as e:
            print(f"Error processing video {video_path}: {str(e)}")
            return False
    
    async def validate_video(self, video_path: str) -> bool:
        """Validate video file"""
        try:
            return (
                os.path.exists(video_path) and 
                os.path.getsize(video_path) > 0 and
                video_path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))
            )
        except Exception:
            return False


class MediaProcessingOrchestrator:
    """
    Main orchestrator for media processing operations
    Follows Single Responsibility and Dependency Inversion principles
    """
    
    def __init__(
        self,
        processor: IVideoProcessor,
        strategy: IProcessingStrategy,
        worker_id: str
    ):
        self._processor = processor
        self._strategy = strategy
        self._worker_id = worker_id
        self._metrics = ProcessingMetrics()
        self._temp_dir = tempfile.mkdtemp(prefix=f"media_worker_{worker_id}_")
    
    async def process_video_batch(
        self, 
        video_data: List[Dict],
        progress_callback: Optional[callable] = None
    ) -> List[VideoProcessingResult]:
        """Process a batch of videos with worker distribution"""
        results = []
        
        for i, video_info in enumerate(video_data):
            video_id = video_info.get('id')
            video_url = video_info.get('url')
            
            # Check if this worker should process this video
            if not await self._strategy.should_process(video_id, self._worker_id):
                result = VideoProcessingResult(
                    video_id=video_id,
                    status=ProcessingStatus.SKIPPED,
                    original_path="",
                    worker_id=self._worker_id
                )
                results.append(result)
                self._metrics.skipped_videos += 1
                continue
            
            # Process the video
            result = await self._process_single_video(video_info)
            results.append(result)
            
            # Update metrics
            self._update_metrics(result)
            
            # Call progress callback if provided
            if progress_callback:
                await progress_callback(i + 1, len(video_data), result)
        
        return results
    
    async def _process_single_video(self, video_info: Dict) -> VideoProcessingResult:
        """Process a single video with complete error handling"""
        video_id = video_info.get('id')
        video_url = video_info.get('url')
        start_time = time.time()
        
        try:
            # Download video to temp location
            temp_path = await self._download_video(video_id, video_url)
            if not temp_path:
                return VideoProcessingResult(
                    video_id=video_id,
                    status=ProcessingStatus.FAILED,
                    original_path="",
                    error_message="Failed to download video",
                    worker_id=self._worker_id
                )
            
            # Validate video
            if not await self._processor.validate_video(temp_path):
                return VideoProcessingResult(
                    video_id=video_id,
                    status=ProcessingStatus.FAILED,
                    original_path=temp_path,
                    error_message="Video validation failed",
                    worker_id=self._worker_id
                )
            
            # Get output path
            output_path = await self._strategy.get_output_path(video_id, self._worker_id)
            
            # Process video
            success = await self._processor.process_video(
                temp_path, 
                output_path, 
                self._worker_id
            )
            
            processing_time = time.time() - start_time
            
            if success:
                return VideoProcessingResult(
                    video_id=video_id,
                    status=ProcessingStatus.COMPLETED,
                    original_path=temp_path,
                    processed_path=output_path,
                    processing_time=processing_time,
                    worker_id=self._worker_id
                )
            else:
                return VideoProcessingResult(
                    video_id=video_id,
                    status=ProcessingStatus.FAILED,
                    original_path=temp_path,
                    processing_time=processing_time,
                    error_message="Processing failed",
                    worker_id=self._worker_id
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            return VideoProcessingResult(
                video_id=video_id,
                status=ProcessingStatus.FAILED,
                original_path="",
                processing_time=processing_time,
                error_message=str(e),
                worker_id=self._worker_id
            )
    
    async def _download_video(self, video_id: int, video_url: Optional[str]) -> Optional[str]:
        """Download video to temporary location"""
        try:
            # Create temp file path
            temp_path = os.path.join(self._temp_dir, f"video_{video_id}.mp4")
            
            # Placeholder for actual download logic
            # In real implementation, this would download from video_url
            # For now, just return the path if URL exists
            if video_url:
                # TODO: Implement actual video download
                return temp_path
            
            return None
            
        except Exception as e:
            print(f"Error downloading video {video_id}: {str(e)}")
            return None
    
    def _update_metrics(self, result: VideoProcessingResult) -> None:
        """Update processing metrics"""
        self._metrics.total_videos += 1
        
        if result.status == ProcessingStatus.COMPLETED:
            self._metrics.processed_videos += 1
        elif result.status == ProcessingStatus.FAILED:
            self._metrics.failed_videos += 1
        elif result.status == ProcessingStatus.SKIPPED:
            self._metrics.skipped_videos += 1
        
        if result.processing_time > 0:
            self._metrics.total_processing_time += result.processing_time
            
            if self._metrics.processed_videos > 0:
                self._metrics.average_processing_time = (
                    self._metrics.total_processing_time / self._metrics.processed_videos
                )
    
    def get_metrics(self) -> ProcessingMetrics:
        """Get current processing metrics"""
        return self._metrics
    
    async def cleanup(self) -> None:
        """Cleanup temporary files and resources"""
        try:
            import shutil
            if os.path.exists(self._temp_dir):
                shutil.rmtree(self._temp_dir)
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")


class MediaProcessingFactory:
    """Factory for creating media processing components"""
    
    @staticmethod
    def create_orchestrator(
        worker_id: str,
        output_dir: str,
        processing_type: str = "uniquification"
    ) -> MediaProcessingOrchestrator:
        """Create configured media processing orchestrator"""
        
        # Create processor based on type
        if processing_type == "uniquification":
            processor = UniquificationProcessor()
        else:
            raise ValueError(f"Unknown processing type: {processing_type}")
        
        # Create strategy
        strategy = PerWorkerProcessingStrategy(output_dir)
        
        # Create orchestrator
        return MediaProcessingOrchestrator(processor, strategy, worker_id)


# Singleton factory instance
media_factory = MediaProcessingFactory()