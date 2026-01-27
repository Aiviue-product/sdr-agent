"""
WhatsApp Bulk Job Repository
Database operations for bulk send job tracking.

Enables:
- Creating and tracking bulk send jobs
- Resuming failed/paused jobs
- Progress monitoring
"""
from typing import Optional, List, Dict
from sqlalchemy import select, update, func, and_, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.whatsapp_outreach.models.whatsapp_bulk_job import WhatsAppBulkJob, WhatsAppBulkJobItem
from app.modules.whatsapp_outreach.constants import BulkJobStatus, BulkJobItemStatus


class WhatsAppBulkJobRepository:
    """Repository for bulk job CRUD operations."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    # ============================================
    # JOB OPERATIONS
    # ============================================
    
    async def create_job(
        self,
        template_name: str,
        lead_ids: List[int],
        broadcast_name: Optional[str] = None
    ) -> Dict:
        """
        Create a new bulk send job with items.
        
        Args:
            template_name: WATI template to use
            lead_ids: List of lead IDs to message
            broadcast_name: Optional campaign identifier
            
        Returns:
            Created job dict with id
        """
        # Create job
        job = WhatsAppBulkJob(
            template_name=template_name,
            broadcast_name=broadcast_name,
            status=BulkJobStatus.PENDING,
            total_count=len(lead_ids),
            pending_count=len(lead_ids),
            sent_count=0,
            failed_count=0
        )
        
        self.db.add(job)
        await self.db.flush()  # Get job ID
        
        # BATCH INSERT: Create all items in a single query
        # Much faster than individual inserts for large batches
        if lead_ids:
            items_data = [
                {
                    "job_id": job.id,
                    "lead_id": lead_id,
                    "status": BulkJobItemStatus.PENDING
                }
                for lead_id in lead_ids
            ]
            
            # Single INSERT with multiple VALUES - O(1) query instead of O(n)
            await self.db.execute(
                insert(WhatsAppBulkJobItem),
                items_data
            )
        
        await self.db.flush()
        await self.db.refresh(job)
        
        return self._job_to_dict(job)
    
    async def get_job_by_id(self, job_id: int) -> Optional[Dict]:
        """Get a job by ID."""
        query = select(WhatsAppBulkJob).where(WhatsAppBulkJob.id == job_id)
        result = await self.db.execute(query)
        job = result.scalar_one_or_none()
        
        if job:
            return self._job_to_dict(job)
        return None
    
    async def get_all_jobs(
        self,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict]:
        """Get all jobs with optional status filter."""
        query = select(WhatsAppBulkJob)
        
        if status:
            query = query.where(WhatsAppBulkJob.status == status)
        
        query = query.order_by(WhatsAppBulkJob.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        jobs = result.scalars().all()
        
        return [self._job_to_dict(job) for job in jobs]
    
    async def get_jobs_count(self, status: Optional[str] = None) -> int:
        """Get total count of jobs."""
        query = select(func.count()).select_from(WhatsAppBulkJob)
        
        if status:
            query = query.where(WhatsAppBulkJob.status == status)
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def update_job_status(
        self,
        job_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """Update job status."""
        update_values = {
            "status": status,
            "updated_at": func.now()
        }
        
        if status == BulkJobStatus.RUNNING:
            update_values["started_at"] = func.now()
        elif status in [BulkJobStatus.COMPLETED, BulkJobStatus.FAILED, BulkJobStatus.CANCELLED]:
            update_values["completed_at"] = func.now()
        
        if error_message:
            update_values["error_message"] = error_message
        
        stmt = (
            update(WhatsAppBulkJob)
            .where(WhatsAppBulkJob.id == job_id)
            .values(**update_values)
        )
        
        await self.db.execute(stmt)
    
    async def update_job_counts(self, job_id: int) -> Dict:
        """
        Recalculate and update job counts from items.
        Returns updated counts.
        """
        # Count items by status
        query = select(
            WhatsAppBulkJobItem.status,
            func.count().label('count')
        ).where(
            WhatsAppBulkJobItem.job_id == job_id
        ).group_by(WhatsAppBulkJobItem.status)
        
        result = await self.db.execute(query)
        status_counts = {row.status: row.count for row in result.all()}
        
        pending = status_counts.get(BulkJobItemStatus.PENDING, 0) + status_counts.get(BulkJobItemStatus.PROCESSING, 0)
        sent = status_counts.get(BulkJobItemStatus.SENT, 0)
        failed = status_counts.get(BulkJobItemStatus.FAILED, 0)
        skipped = status_counts.get(BulkJobItemStatus.SKIPPED, 0)
        
        # Update job
        stmt = (
            update(WhatsAppBulkJob)
            .where(WhatsAppBulkJob.id == job_id)
            .values(
                pending_count=pending,
                sent_count=sent,
                failed_count=failed + skipped,
                updated_at=func.now()
            )
        )
        
        await self.db.execute(stmt)
        
        return {
            "pending": pending,
            "sent": sent,
            "failed": failed,
            "skipped": skipped
        }
    
    # ============================================
    # ITEM OPERATIONS
    # ============================================
    
    async def get_pending_items(
        self,
        job_id: int,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get pending items for a job.
        Used when processing or resuming a job.
        """
        query = (
            select(WhatsAppBulkJobItem)
            .where(
                and_(
                    WhatsAppBulkJobItem.job_id == job_id,
                    WhatsAppBulkJobItem.status == BulkJobItemStatus.PENDING
                )
            )
            .order_by(WhatsAppBulkJobItem.id)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return [self._item_to_dict(item) for item in items]
    
    async def get_job_items(
        self,
        job_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict]:
        """Get items for a job with optional status filter."""
        query = select(WhatsAppBulkJobItem).where(WhatsAppBulkJobItem.job_id == job_id)
        
        if status:
            query = query.where(WhatsAppBulkJobItem.status == status)
        
        query = query.order_by(WhatsAppBulkJobItem.id).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return [self._item_to_dict(item) for item in items]
    
    async def update_item_status(
        self,
        item_id: int,
        status: str,
        error_message: Optional[str] = None,
        wati_message_id: Optional[str] = None
    ) -> None:
        """Update item status after processing."""
        update_values = {
            "status": status,
            "processed_at": func.now()
        }
        
        if error_message:
            update_values["error_message"] = error_message
        if wati_message_id:
            update_values["wati_message_id"] = wati_message_id
        
        stmt = (
            update(WhatsAppBulkJobItem)
            .where(WhatsAppBulkJobItem.id == item_id)
            .values(**update_values)
        )
        
        await self.db.execute(stmt)
    
    async def mark_item_processing(self, item_id: int) -> None:
        """Mark an item as currently processing."""
        stmt = (
            update(WhatsAppBulkJobItem)
            .where(WhatsAppBulkJobItem.id == item_id)
            .values(status=BulkJobItemStatus.PROCESSING)
        )
        await self.db.execute(stmt)
    
    async def reset_processing_items(self, job_id: int) -> int:
        """
        Reset items stuck in 'processing' back to 'pending'.
        Used when resuming a job after crash.
        Returns count of reset items.
        """
        stmt = (
            update(WhatsAppBulkJobItem)
            .where(
                and_(
                    WhatsAppBulkJobItem.job_id == job_id,
                    WhatsAppBulkJobItem.status == BulkJobItemStatus.PROCESSING
                )
            )
            .values(status=BulkJobItemStatus.PENDING)
        )
        
        result = await self.db.execute(stmt)
        return result.rowcount
    
    # ============================================
    # HELPER METHODS
    # ============================================
    
    def _job_to_dict(self, job: WhatsAppBulkJob) -> Dict:
        """Convert job model to dict."""
        return {
            "id": job.id,
            "template_name": job.template_name,
            "broadcast_name": job.broadcast_name,
            "status": job.status,
            "total_count": job.total_count,
            "pending_count": job.pending_count,
            "sent_count": job.sent_count,
            "failed_count": job.failed_count,
            "error_message": job.error_message,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "updated_at": job.updated_at,
            "progress_percent": round((job.sent_count + job.failed_count) / job.total_count * 100, 1) if job.total_count > 0 else 0
        }
    
    def _item_to_dict(self, item: WhatsAppBulkJobItem) -> Dict:
        """Convert item model to dict."""
        return {
            "id": item.id,
            "job_id": item.job_id,
            "lead_id": item.lead_id,
            "status": item.status,
            "error_message": item.error_message,
            "wati_message_id": item.wati_message_id,
            "processed_at": item.processed_at,
            "created_at": item.created_at
        }
