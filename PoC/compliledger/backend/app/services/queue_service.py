#!/usr/bin/env python3

import os
import json
import time
import asyncio
import logging
from typing import Dict, Any, Callable, List, Optional
from redis.asyncio import Redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QueueService:
    """Service for managing asynchronous job queues with Redis"""
    
    def __init__(self):
        """Initialize Redis connection"""
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = None
        self.tasks = {}
        self.processors = {}
        self.running = False
        
        # Define queue names
        self.verification_queue = "compliledger:verification"
        self.analysis_queue = "compliledger:analysis"
        self.blockchain_queue = "compliledger:blockchain"
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis = Redis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
            logger.info("Connected to Redis successfully")
            return True
        except Exception as e:
            logger.error(f"Error connecting to Redis: {str(e)}")
            logger.warning("Using fallback in-memory queue for PoC purposes")
            # Initialize in-memory queues as fallback
            self.tasks = {
                self.verification_queue: [],
                self.analysis_queue: [],
                self.blockchain_queue: []
            }
            return False
    
    async def enqueue_verification(self, data: Dict[str, Any]) -> bool:
        """Add a verification job to the queue"""
        return await self.enqueue_task(self.verification_queue, data)
    
    async def enqueue_analysis(self, data: Dict[str, Any]) -> bool:
        """Add an AI analysis job to the queue"""
        return await self.enqueue_task(self.analysis_queue, data)
    
    async def enqueue_blockchain(self, data: Dict[str, Any]) -> bool:
        """Add a blockchain interaction job to the queue"""
        return await self.enqueue_task(self.blockchain_queue, data)
    
    async def enqueue_task(self, queue: str, data: Dict[str, Any]) -> bool:
        """Add a task to the specified queue"""
        try:
            # Add timestamp and job ID
            job_data = data.copy()
            job_data.update({
                "job_id": f"{int(time.time())}-{os.urandom(4).hex()}",
                "created_at": time.time(),
                "status": "queued"
            })
            
            if self.redis:
                try:
                    # Use Redis for queueing
                    await self.redis.rpush(queue, json.dumps(job_data))
                    logger.info(f"Task added to Redis queue '{queue}': {job_data['job_id']}")
                    return True
                except Exception as e:
                    logger.warning(f"Redis error, falling back to in-memory queue: {str(e)}")
                    # Fallback to in-memory queue on Redis error
                    self.tasks.setdefault(queue, []).append(job_data)
                    logger.info(f"Task added to in-memory queue '{queue}': {job_data['job_id']}")
                    return True
            else:
                # Use in-memory fallback
                self.tasks.setdefault(queue, []).append(job_data)
                logger.info(f"Task added to in-memory queue '{queue}': {job_data['job_id']}")
                return True
        except Exception as e:
            logger.error(f"Error adding task to queue {queue}: {str(e)}")
            # Still add to in-memory queue as last resort
            try:
                self.tasks.setdefault(queue, []).append(data)
                return True
            except:
                return False
    
    async def register_processor(self, queue: str, processor: Callable):
        """Register a function to process jobs from a specific queue"""
        self.processors[queue] = processor
        logger.info(f"Registered processor for queue: {queue}")
    
    async def start_processing(self):
        """Start processing jobs from all registered queues"""
        if self.running:
            logger.warning("Queue processor is already running")
            return
        
        self.running = True
        logger.info("Starting queue processor")
        
        # Start consumer tasks for each queue with a registered processor
        consumer_tasks = []
        for queue, processor in self.processors.items():
            task = asyncio.create_task(self._process_queue(queue, processor))
            consumer_tasks.append(task)
        
        # Wait for all consumer tasks to complete (they run indefinitely)
        await asyncio.gather(*consumer_tasks)
    
    async def stop_processing(self):
        """Stop processing jobs"""
        self.running = False
        logger.info("Stopping queue processor")
        # Give time for current jobs to complete
        await asyncio.sleep(2)
    
    async def _process_queue(self, queue: str, processor: Callable):
        """Process jobs from a specific queue"""
        logger.info(f"Starting processor for queue: {queue}")
        
        while self.running:
            try:
                if self.redis:
                    # Use Redis for queue processing
                    # Use blocking pop with timeout to prevent CPU spinning
                    result = await self.redis.blpop(queue, 1)
                    if result:
                        _, job_data_str = result
                        job_data = json.loads(job_data_str)
                        
                        # Process the job
                        logger.info(f"Processing job from Redis queue {queue}: {job_data.get('job_id')}")
                        await processor(job_data)
                else:
                    # Use in-memory fallback
                    if queue in self.tasks and self.tasks[queue]:
                        job_data = self.tasks[queue].pop(0)
                        
                        # Process the job
                        logger.info(f"Processing job from in-memory queue {queue}: {job_data.get('job_id')}")
                        await processor(job_data)
                    else:
                        # No jobs in queue, sleep to prevent CPU spinning
                        await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error processing job from queue {queue}: {str(e)}")
                # Sleep briefly before retrying
                await asyncio.sleep(1)
    
    async def get_queue_stats(self) -> Dict[str, int]:
        """Get statistics about queue lengths"""
        stats = {}
        
        try:
            if self.redis:
                # Get queue lengths from Redis
                for queue in [self.verification_queue, self.analysis_queue, self.blockchain_queue]:
                    stats[queue] = await self.redis.llen(queue)
            else:
                # Get queue lengths from in-memory queues
                for queue in [self.verification_queue, self.analysis_queue, self.blockchain_queue]:
                    stats[queue] = len(self.tasks.get(queue, []))
        except Exception as e:
            logger.error(f"Error getting queue statistics: {str(e)}")
            # Return zeros on error
            for queue in [self.verification_queue, self.analysis_queue, self.blockchain_queue]:
                stats[queue] = 0
        
        return stats


# Example processors
async def verification_processor(job_data: Dict[str, Any]):
    """Example processor for verification jobs"""
    artifact_hash = job_data.get("artifact_hash")
    logger.info(f"Processing verification for artifact: {artifact_hash}")
    # Simulate processing time
    await asyncio.sleep(1)
    logger.info(f"Verification processed for artifact: {artifact_hash}")

async def analysis_processor(job_data: Dict[str, Any]):
    """Example processor for AI analysis jobs"""
    artifact_hash = job_data.get("artifact_hash")
    logger.info(f"Running AI analysis for artifact: {artifact_hash}")
    # Simulate processing time
    await asyncio.sleep(2)
    logger.info(f"Analysis completed for artifact: {artifact_hash}")

async def blockchain_processor(job_data: Dict[str, Any]):
    """Example processor for blockchain interaction jobs"""
    tx_type = job_data.get("tx_type")
    logger.info(f"Processing blockchain transaction: {tx_type}")
    # Simulate processing time
    await asyncio.sleep(0.5)
    logger.info(f"Blockchain transaction processed: {tx_type}")


# Example usage
async def test_queue():
    """Test queue service"""
    queue_service = QueueService()
    await queue_service.initialize()
    
    # Register processors
    await queue_service.register_processor(
        queue_service.verification_queue,
        verification_processor
    )
    await queue_service.register_processor(
        queue_service.analysis_queue,
        analysis_processor
    )
    await queue_service.register_processor(
        queue_service.blockchain_queue,
        blockchain_processor
    )
    
    # Enqueue some test jobs
    await queue_service.enqueue_verification({
        "artifact_hash": "4efbe4768fa2182cf72a93cdab95f8a7b5637b6233302cfc2775228eab3c1ac0",
        "profile_id": "default"
    })
    
    await queue_service.enqueue_analysis({
        "artifact_hash": "4efbe4768fa2182cf72a93cdab95f8a7b5637b6233302cfc2775228eab3c1ac0",
        "oscal_cid": "QmTestCID123"
    })
    
    await queue_service.enqueue_blockchain({
        "tx_type": "register_artifact",
        "artifact_hash": "4efbe4768fa2182cf72a93cdab95f8a7b5637b6233302cfc2775228eab3c1ac0",
        "oscal_cid": "QmTestCID123"
    })
    
    # Get queue stats before processing
    stats = await queue_service.get_queue_stats()
    print("\n===== Queue Stats Before Processing =====")
    print(json.dumps(stats, indent=2))
    
    # Start processing in background
    process_task = asyncio.create_task(queue_service.start_processing())
    
    # Let the processors run for a few seconds
    await asyncio.sleep(5)
    
    # Stop processing
    await queue_service.stop_processing()
    
    # Get queue stats after processing
    stats = await queue_service.get_queue_stats()
    print("\n===== Queue Stats After Processing =====")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    asyncio.run(test_queue())
