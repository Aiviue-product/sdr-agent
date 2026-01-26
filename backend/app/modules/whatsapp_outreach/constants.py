"""
WhatsApp Outreach Constants
Centralized enums and constants for the WhatsApp module.

Using Enums instead of magic strings provides:
- Type safety (IDE autocomplete, typo prevention)
- Single source of truth
- Easy refactoring
- Better documentation
"""
from enum import Enum


class DeliveryStatus(str, Enum):
    """
    Message delivery status enum.
    
    Inherits from str so it can be used directly in JSON responses
    and database queries without .value conversion.
    
    Status Flow:
    PENDING → SENT → DELIVERED → READ
                 ↘ FAILED
                         ↘ REPLIED (lead responded)
    """
    PENDING = "PENDING"      # Message created but not yet sent to WATI
    SENT = "SENT"            # Sent to WATI, awaiting delivery confirmation
    DELIVERED = "DELIVERED"  # Delivered to recipient's device
    READ = "READ"            # Read by recipient (blue ticks)
    FAILED = "FAILED"        # Delivery failed
    REPLIED = "REPLIED"      # Lead replied to the message
    RECEIVED = "RECEIVED"    # Inbound message received from lead
    UNKNOWN = "UNKNOWN"      # Status unknown/not tracked
    
    @classmethod
    def is_success_status(cls, status: str) -> bool:
        """Check if status indicates successful delivery."""
        return status in [cls.SENT, cls.DELIVERED, cls.READ, cls.REPLIED]
    
    @classmethod
    def is_engagement_status(cls, status: str) -> bool:
        """Check if status indicates lead engagement (read or replied)."""
        return status in [cls.READ, cls.REPLIED]
    
    @classmethod
    def is_final_status(cls, status: str) -> bool:
        """Check if status is final (no more updates expected)."""
        return status in [cls.READ, cls.FAILED, cls.REPLIED]


class MessageDirection(str, Enum):
    """Direction of a WhatsApp message."""
    OUTBOUND = "outbound"  # We sent it
    INBOUND = "inbound"    # Lead sent it


class ActivityType(str, Enum):
    """Types of activities logged in the system."""
    # Message events
    MESSAGE_SENT = "message_sent"
    MESSAGE_DELIVERED = "message_delivered"
    MESSAGE_READ = "message_read"
    MESSAGE_FAILED = "message_failed"
    REPLY_RECEIVED = "reply_received"
    
    # Lead events
    LEAD_CREATED = "lead_created"
    LEADS_IMPORTED = "leads_imported"
    
    # Bulk operations
    BULK_SEND_STARTED = "bulk_send_started"
    BULK_SEND_COMPLETED = "bulk_send_completed"


class LeadSource(str, Enum):
    """Source of a WhatsApp lead."""
    MANUAL = "manual"              # Manually created via UI
    EMAIL_IMPORT = "email_import"  # Imported from email outreach
    LINKEDIN_IMPORT = "linkedin_import"  # Imported from LinkedIn outreach
    CSV_IMPORT = "csv_import"      # Imported from CSV file
    API = "api"                    # Created via API


class BulkJobStatus(str, Enum):
    """
    Status of a bulk send job.
    
    Flow: PENDING → RUNNING → COMPLETED
                  ↘ PAUSED (can resume)
                  ↘ FAILED (can retry)
                  ↘ CANCELLED (terminal)
    """
    PENDING = "pending"        # Job created, not yet started
    RUNNING = "running"        # Currently processing
    PAUSED = "paused"          # Manually paused, can resume
    COMPLETED = "completed"    # All items processed successfully
    FAILED = "failed"          # Job failed (can retry remaining)
    CANCELLED = "cancelled"    # Manually cancelled
    
    @classmethod
    def is_terminal(cls, status: str) -> bool:
        """Check if status is terminal (job won't continue)."""
        return status in [cls.COMPLETED, cls.CANCELLED]
    
    @classmethod
    def can_resume(cls, status: str) -> bool:
        """Check if job can be resumed."""
        return status in [cls.PAUSED, cls.FAILED, cls.PENDING]


class BulkJobItemStatus(str, Enum):
    """Status of an individual item in a bulk job."""
    PENDING = "pending"        # Not yet processed
    PROCESSING = "processing"  # Currently being sent
    SENT = "sent"              # Successfully sent
    FAILED = "failed"          # Failed to send
    SKIPPED = "skipped"        # Skipped (e.g., already sent before)


class WebhookEventType(str, Enum):
    """WATI webhook event types."""
    # Standard events
    TEMPLATE_MESSAGE_SENT = "templateMessageSent"
    MESSAGE_DELIVERED = "messageDelivered"
    MESSAGE_READ = "messageRead"
    TEMPLATE_MESSAGE_FAILED = "templateMessageFailed"
    MESSAGE = "message"  # Inbound message
    
    # V2 events (WATI API v2)
    TEMPLATE_MESSAGE_SENT_V2 = "templateMessageSent_v2"
    SENT_MESSAGE_DELIVERED_V2 = "sentMessageDELIVERED_v2"
    SENT_MESSAGE_READ_V2 = "sentMessageREAD_v2"
    TEMPLATE_MESSAGE_FAILED_V2 = "templateMessageFAILED_v2"
    SENT_MESSAGE_REPLIED_V2 = "sentMessageREPLIED_v2"
