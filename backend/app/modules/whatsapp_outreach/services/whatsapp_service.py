"""
WhatsApp Outreach Service
High-level business logic for WhatsApp messaging via WATI.

Orchestrates:
- Lead management
- Message sending (single and bulk)
- Template personalization
- Activity logging
- Import from other modules
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.whatsapp_outreach.services.wati_client import wati_client
from app.modules.whatsapp_outreach.repositories.whatsapp_lead_repository import WhatsAppLeadRepository
from app.modules.whatsapp_outreach.repositories.whatsapp_message_repository import WhatsAppMessageRepository
from app.modules.whatsapp_outreach.repositories.whatsapp_activity_repository import WhatsAppActivityRepository

logger = logging.getLogger("whatsapp_service")

# Rate limiting for bulk operations
BULK_SEND_DELAY_SECONDS = 1.0  # Delay between messages in bulk send


class WhatsAppOutreachService:
    """
    High-level service for WhatsApp outreach operations.
    
    Provides:
    - Send single message
    - Bulk send with rate limiting
    - Template personalization
    - Import leads from email/LinkedIn modules
    - Activity logging
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.lead_repo = WhatsAppLeadRepository(db)
        self.message_repo = WhatsAppMessageRepository(db)
        self.activity_repo = WhatsAppActivityRepository(db)
    
    # ============================================
    # CONFIGURATION CHECK
    # ============================================
    
    def is_configured(self) -> bool:
        """Check if WhatsApp service is properly configured."""
        return wati_client.is_configured()
    
    # ============================================
    # TEMPLATE OPERATIONS
    # ============================================
    
    async def get_available_templates(self) -> Dict[str, Any]:
        """
        Get all approved templates from WATI.
        
        Returns simplified template info for UI display.
        """
        result = await wati_client.get_templates()
        
        if not result.get("success"):
            return result
        
        # Simplify template data for UI
        templates = []
        for t in result.get("templates", []):
            templates.append({
                "id": t.get("id"),
                "name": t.get("elementName"),
                "category": t.get("category"),
                "body": t.get("bodyOriginal"),
                "params": [p.get("paramName") for p in t.get("customParams", [])],
                "has_header": t.get("header") is not None,
                "has_buttons": len(t.get("buttons", [])) > 0
            })
        
        return {
            "success": True,
            "templates": templates,
            "total": len(templates)
        }
    
    def render_template_message(
        self,
        template_body: str,
        params: Dict[str, str]
    ) -> str:
        """
        Render template with parameter values for preview.
        
        Args:
            template_body: Template body with {{param_name}} placeholders
            params: Dict of param_name -> value
            
        Returns:
            Rendered message text
        """
        message = template_body
        for name, value in params.items():
            # Handle both {{name}} and {{1}} style placeholders
            message = message.replace(f"{{{{{name}}}}}", value)
            message = message.replace(f"{{{{name}}}}", value)
        
        return message
    
    # ============================================
    # SINGLE MESSAGE OPERATIONS
    # ============================================
    
    async def send_message_to_lead(
        self,
        lead_id: int,
        template_name: str,
        custom_params: Optional[Dict[str, str]] = None,
        broadcast_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp template message to a single lead.
        
        TRANSACTION: All DB operations (message record, lead status, activity)
        are wrapped in a single transaction for atomicity.
        
        Args:
            lead_id: ID of the WhatsApp lead
            template_name: Name of the WATI template to use
            custom_params: Optional custom parameter values (overrides auto-generated)
            broadcast_name: Optional campaign identifier
            
        Returns:
            Dict with success status and message details
        """
        # Get lead
        lead = await self.lead_repo.get_by_id(lead_id)
        if not lead:
            return {"success": False, "error": "Lead not found"}
        
        phone_number = lead["mobile_number"]
        first_name = lead.get("first_name", "")
        company_name = lead.get("company_name", "")
        
        # Get template for param info
        template_result = await wati_client.get_template_by_name(template_name)
        if not template_result.get("success"):
            return template_result
        
        template = template_result.get("template", {})
        template_params = template_result.get("params", [])
        
        # Build parameters
        default_params = {
            "name": first_name,
            "first_name": first_name,
            "company": company_name,
            "company_name": company_name,
        }
        
        final_params = {**default_params}
        if custom_params:
            final_params.update(custom_params)
        
        parameters = [
            {"name": p, "value": final_params.get(p, "")}
            for p in template_params
        ]
        
        if not broadcast_name:
            broadcast_name = f"sdr_single_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Send via WATI (external API call - NOT in transaction)
        send_result = await wati_client.send_template_message(
            phone_number=phone_number,
            template_name=template_name,
            parameters=parameters,
            broadcast_name=broadcast_name
        )
        
        # Render message for storage
        message_text = self.render_template_message(
            template.get("bodyOriginal", ""),
            final_params
        )
        
        # Determine initial status
        if send_result.get("success"):
            status = "SENT"
            failed_reason = None
        else:
            status = "FAILED"
            failed_reason = send_result.get("error", "Unknown error")
        
        # TRANSACTION: Wrap all DB writes in single atomic operation
        try:
            async with self.db.begin_nested():  # Savepoint for atomicity
                # Create message record
                message = await self.message_repo.create_outbound_message(
                    lead_id=lead_id,
                    template_name=template_name,
                    message_text=message_text,
                    parameters=final_params,
                    broadcast_name=broadcast_name,
                    wati_message_id=send_result.get("message_ids", [None])[0] if send_result.get("message_ids") else None,
                    status=status
                )
                
                # Update lead status
                await self.lead_repo.update_wa_sent_status(
                    lead_id=lead_id,
                    status=status,
                    template_name=template_name,
                    failed_reason=failed_reason
                )
                
                # Log activity
                if status == "SENT":
                    await self.activity_repo.log_message_sent(
                        lead_id=lead_id,
                        lead_name=first_name,
                        lead_mobile=phone_number,
                        template_name=template_name,
                        is_global=True
                    )
                else:
                    await self.activity_repo.log_message_failed(
                        lead_id=lead_id,
                        lead_name=first_name,
                        lead_mobile=phone_number,
                        error=failed_reason,
                        is_global=True
                    )
            
            # Commit transaction
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Transaction failed for lead {lead_id}: {str(e)}")
            return {
                "success": False,
                "lead_id": lead_id,
                "error": f"Database error: {str(e)}"
            }
        
        return {
            "success": send_result.get("success", False),
            "lead_id": lead_id,
            "phone_number": phone_number,
            "template_name": template_name,
            "status": status,
            "message_id": message.get("id"),
            "error": failed_reason
        }
    
    # ============================================
    # BULK MESSAGE OPERATIONS
    # ============================================
    
    async def bulk_check_eligibility(
        self,
        lead_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Check which leads are eligible for WhatsApp messaging.
        
        Returns:
            Dict with eligible and ineligible leads with reasons
        """
        leads = await self.lead_repo.get_leads_by_ids(lead_ids)
        
        eligible = []
        ineligible = []
        
        for lead in leads:
            lead_id = lead.get("id")
            phone = lead.get("mobile_number")
            first_name = lead.get("first_name")
            is_sent = lead.get("is_wa_sent", False)
            
            if not phone:
                ineligible.append({
                    "lead_id": lead_id,
                    "reason": "Missing phone number"
                })
            elif not first_name:
                ineligible.append({
                    "lead_id": lead_id,
                    "reason": "Missing first name"
                })
            elif is_sent:
                ineligible.append({
                    "lead_id": lead_id,
                    "reason": "Already sent"
                })
            else:
                eligible.append({
                    "lead_id": lead_id,
                    "phone_number": phone,
                    "first_name": first_name
                })
        
        return {
            "success": True,
            "eligible": eligible,
            "eligible_count": len(eligible),
            "ineligible": ineligible,
            "ineligible_count": len(ineligible),
            "total_requested": len(lead_ids)
        }
    
    async def bulk_send_messages(
        self,
        lead_ids: List[int],
        template_name: str,
        broadcast_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send WhatsApp messages to multiple leads with rate limiting.
        
        Args:
            lead_ids: List of lead IDs to message
            template_name: Template to use
            broadcast_name: Optional campaign identifier
            
        Returns:
            Dict with success/failed counts and details
        """
        if not broadcast_name:
            broadcast_name = f"sdr_bulk_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Log start activity
        await self.activity_repo.log_bulk_send_started(
            lead_count=len(lead_ids),
            template_name=template_name
        )
        
        results = {
            "success_count": 0,
            "failed_count": 0,
            "results": [],
            "broadcast_name": broadcast_name
        }
        
        for i, lead_id in enumerate(lead_ids):
            # Rate limiting delay (except for first message)
            if i > 0:
                await asyncio.sleep(BULK_SEND_DELAY_SECONDS)
            
            try:
                result = await self.send_message_to_lead(
                    lead_id=lead_id,
                    template_name=template_name,
                    broadcast_name=broadcast_name
                )
                
                if result.get("success"):
                    results["success_count"] += 1
                else:
                    results["failed_count"] += 1
                
                results["results"].append({
                    "lead_id": lead_id,
                    "success": result.get("success"),
                    "error": result.get("error")
                })
                
            except Exception as e:
                results["failed_count"] += 1
                results["results"].append({
                    "lead_id": lead_id,
                    "success": False,
                    "error": str(e)
                })
        
        # Log completion activity
        await self.activity_repo.log_bulk_send_completed(
            success_count=results["success_count"],
            failed_count=results["failed_count"]
        )
        
        results["success"] = results["failed_count"] == 0
        return results
    
    # ============================================
    # MESSAGE STATUS OPERATIONS
    # ============================================
    
    async def sync_message_status(self, lead_id: int) -> Dict[str, Any]:
        """
        Sync message status from WATI for a lead.
        
        Fetches latest status from WATI and updates local records.
        """
        lead = await self.lead_repo.get_by_id(lead_id)
        if not lead:
            return {"success": False, "error": "Lead not found"}
        
        # Also sync full message history while we are at it
        history_result = await self.sync_lead_messages(lead_id)
        
        phone_number = lead["mobile_number"]
        
        # Get status from WATI
        status_result = await wati_client.get_message_status(phone_number)
        
        if not status_result.get("success"):
            return status_result
        
        status = status_result.get("status")
        failed_detail = status_result.get("failed_detail")
        
        if status:
            # Update lead
            await self.lead_repo.update_delivery_status(
                lead_id=lead_id,
                status=status,
                failed_reason=failed_detail
            )
            
            # Log activity for significant status changes
            lead_name = lead.get("first_name", "")
            if status == "DELIVERED":
                await self.activity_repo.log_message_delivered(
                    lead_id=lead_id,
                    lead_name=lead_name,
                    lead_mobile=phone_number
                )
            elif status == "READ":
                await self.activity_repo.log_message_read(
                    lead_id=lead_id,
                    lead_name=lead_name,
                    lead_mobile=phone_number
                )
        
        await self.db.commit()
        
        return {
            "success": True,
            "lead_id": lead_id,
            "status": status,
            "failed_detail": failed_detail,
            "messages_synced": history_result.get("count", 0)
        }

    async def sync_lead_messages(self, lead_id: int) -> Dict[str, Any]:
        """
        Fetch full conversation history from WATI and save to local DB.
        """
        lead = await self.lead_repo.get_by_id(lead_id)
        if not lead:
            return {"success": False, "error": "Lead not found"}
            
        phone_number = lead["mobile_number"]
        
        # 1. Get existing message IDs to avoid duplicates
        existing_ids = await self.message_repo.get_existing_wati_ids(lead_id)
        
        # 2. Get messages from WATI
        wati_result = await wati_client.get_messages(phone_number)
        if not wati_result.get("success"):
            return wati_result
            
        messages = wati_result.get("messages", [])
        new_messages_count = 0
        
        # 3. Process messages
        for msg in messages:
            wati_id = msg.get("id")
            if wati_id in existing_ids:
                # Update status of existing messages if changed
                # (Optional: implement if needed)
                continue
                
            # Create new message record
            # owner=True means outbound, owner=False means inbound
            direction = "outbound" if msg.get("owner") else "inbound"
            
            # Extract text
            text_content = msg.get("text", "")
            
            # Skip empty messages (system events, reactions, or non-text for now)
            if not text_content:
                continue
            
            # Map status
            status = msg.get("statusString", "SENT")
            if direction == "inbound":
                status = "RECEIVED"
                
            try:
                if direction == "outbound":
                    await self.message_repo.create_outbound_message(
                        lead_id=lead_id,
                        template_name=msg.get("templateName"),
                        message_text=text_content,
                        wati_message_id=wati_id,
                        wati_conversation_id=msg.get("conversationId"),
                        status=status
                    )
                else:
                    await self.message_repo.create_inbound_message(
                        lead_id=lead_id,
                        message_text=text_content,
                        wati_message_id=wati_id,
                        wati_conversation_id=msg.get("conversationId")
                    )
                new_messages_count += 1
            except Exception as e:
                logger.error(f"Error saving message {wati_id}: {str(e)}")
                
        # Update lead status to REPLIED if there's an inbound message
        if any(not msg.get("owner") for msg in messages):
            await self.lead_repo.update_delivery_status(lead_id, "REPLIED")
            
        return {"success": True, "count": new_messages_count}

    async def sync_all_wati_data(self) -> Dict[str, Any]:
        """
        Perform a deep sync of all active leads and templates.
        """
        results = {
            "leads_processed": 0,
            "messages_synced": 0,
            "templates_refreshed": 0,
            "success": True
        }
        
        try:
            # 1. Refresh templates (via wati_client directly in most cases, but we can log it)
            templates = await wati_client.get_templates()
            if templates.get("success"):
                results["templates_refreshed"] = len(templates.get("templates", []))
            
            # 2. Fetch leads needing sync
            leads = await self.lead_repo.get_leads_needing_sync(limit=50)
            
            # 3. Process each lead
            for lead in leads:
                lead_id = lead["id"]
                sync_result = await self.sync_message_status(lead_id)
                if sync_result.get("success"):
                    results["leads_processed"] += 1
                    results["messages_synced"] += sync_result.get("messages_synced", 0)
            
            # Final commit
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Global sync failed: {str(e)}")
            results["success"] = False
            results["error"] = str(e)
            
        return results
    
    # ============================================
    # LEAD IMPORT OPERATIONS
    # ============================================
    
    async def import_from_email_leads(
        self,
        db_email: AsyncSession
    ) -> Dict[str, Any]:
        """
        Import leads from email outreach module (where mobile exists).
        
        Returns:
            Dict with import counts
        """
        from app.modules.email_outreach.models.lead import Lead as EmailLead
        from sqlalchemy import select
        
        # Query email leads with mobile numbers
        query = select(
            EmailLead.id,
            EmailLead.first_name,
            EmailLead.last_name,
            EmailLead.mobile_number,
            EmailLead.email,
            EmailLead.company_name,
            EmailLead.designation,
            EmailLead.linkedin_url,
            EmailLead.sector
        ).where(
            EmailLead.mobile_number.isnot(None),
            EmailLead.mobile_number != ""
        )
        
        result = await db_email.execute(query)
        email_leads = result.all()
        
        # Prepare for bulk upsert
        leads_to_import = []
        for lead in email_leads:
            leads_to_import.append({
                "mobile_number": lead.mobile_number,
                "first_name": lead.first_name,
                "last_name": lead.last_name,
                "email": lead.email,
                "company_name": lead.company_name,
                "designation": lead.designation,
                "linkedin_url": lead.linkedin_url,
                "sector": lead.sector,
                "source": "email_import",
                "source_lead_id": lead.id
            })
        
        if not leads_to_import:
            return {
                "success": True,
                "message": "No email leads with mobile numbers found",
                "imported_count": 0
            }
        
        # Bulk upsert
        upsert_result = await self.lead_repo.bulk_upsert_leads(leads_to_import)
        
        # Log activity
        total_imported = upsert_result["inserted_count"] + upsert_result["updated_count"]
        if total_imported > 0:
            await self.activity_repo.log_leads_imported(
                count=total_imported,
                source="email_outreach"
            )
        
        return {
            "success": True,
            "source": "email_outreach",
            "total_with_mobile": len(leads_to_import),
            "inserted": upsert_result["inserted_count"],
            "updated": upsert_result["updated_count"],
            "skipped": upsert_result["skipped_count"],
            "errors": upsert_result.get("errors", [])[:10]  # Limit errors shown
        }
    
    async def import_from_linkedin_leads(
        self,
        db_linkedin: AsyncSession
    ) -> Dict[str, Any]:
        """
        Import leads from LinkedIn outreach module.
        
        Only imports leads that have a mobile number (enriched).
        Uses upsert to avoid duplicates.
        """
        from app.modules.signal_outreach.models.linkedin_lead import LinkedInLead
        from sqlalchemy import select
        
        # Query LinkedIn leads with mobile numbers
        query = select(
            LinkedInLead.id,
            LinkedInLead.first_name,
            LinkedInLead.last_name,
            LinkedInLead.full_name,
            LinkedInLead.mobile_number,
            LinkedInLead.company_name,
            LinkedInLead.headline,
            LinkedInLead.linkedin_url
        ).where(
            LinkedInLead.mobile_number.isnot(None),
            LinkedInLead.mobile_number != ""
        )
        
        result = await db_linkedin.execute(query)
        linkedin_leads = result.all()
        
        # Prepare for bulk upsert
        leads_to_import = []
        for lead in linkedin_leads:
            # Handle names carefully
            fname = lead.first_name
            lname = lead.last_name
            
            # If names are missing but full_name exists, split it
            if not fname and lead.full_name:
                parts = lead.full_name.split(' ', 1)
                fname = parts[0]
                lname = parts[1] if len(parts) > 1 else ""

            leads_to_import.append({
                "mobile_number": lead.mobile_number,
                "first_name": fname or "LinkedIn",
                "last_name": lname or "User",
                "email": None, # LinkedIn leads often don't have email in this table
                "company_name": lead.company_name,
                "designation": lead.headline,
                "linkedin_url": lead.linkedin_url,
                "source": "linkedin_import",
                "source_lead_id": lead.id
            })
        
        if not leads_to_import:
            return {
                "success": True,
                "source": "linkedin_outreach",
                "message": "No LinkedIn leads with mobile numbers found",
                "total_with_mobile": 0,
                "inserted": 0,
                "updated": 0,
                "skipped": 0
            }
        
        # Bulk upsert
        upsert_result = await self.lead_repo.bulk_upsert_leads(leads_to_import)
        
        # Log activity
        total_imported = upsert_result["inserted_count"] + upsert_result["updated_count"]
        if total_imported > 0:
            await self.activity_repo.log_leads_imported(
                count=total_imported,
                source="linkedin_outreach"
            )
        
        return {
            "success": True,
            "source": "linkedin_outreach",
            "total_with_mobile": len(leads_to_import),
            "inserted": upsert_result["inserted_count"],
            "updated": upsert_result["updated_count"],
            "skipped": upsert_result["skipped_count"],
            "errors": upsert_result.get("errors", [])[:10]
        }
    
    # ============================================
    # WEBHOOK HANDLING (Dictionary Dispatch Pattern)
    # ============================================
    
    async def handle_webhook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming WATI webhook event using Dictionary Dispatch.
        
        DESIGN PATTERN: Dictionary Dispatch
        - O(1) lookup vs O(n) elif chain
        - Cleaner, more maintainable code
        - Easy to add new event types
        
        TRANSACTION: All handler operations are wrapped in a single transaction
        to ensure atomicity and avoid race conditions.
        
        Supported events:
        - templateMessageSent
        - messageDelivered
        - messageRead
        - templateMessageFailed
        - message (inbound reply)
        """
        event_type = event_data.get("eventType", "")
        phone_number = event_data.get("waId", "")
        
        logger.info(f"📬 Webhook received: {event_type} for {phone_number}")
        
        # Find lead by phone
        lead = await self.lead_repo.get_by_mobile(phone_number)
        if not lead:
            logger.warning(f"⚠️ No lead found for phone: {phone_number}")
            return {"success": False, "error": "Lead not found"}
        
        # Dictionary Dispatch: Map event types to handler methods
        # Support both standard names and WATI V2 names (_v2)
        event_handlers = {
            # Sent
            "templateMessageSent": self._handle_message_sent,
            "templateMessageSent_v2": self._handle_message_sent,
            
            # Delivered
            "messageDelivered": self._handle_message_delivered,
            "sentMessageDELIVERED_v2": self._handle_message_delivered,
            
            # Read
            "messageRead": self._handle_message_read,
            "sentMessageREAD_v2": self._handle_message_read,
            
            # Failed
            "templateMessageFailed": self._handle_message_failed,
            "templateMessageFAILED_v2": self._handle_message_failed,
            
            # Inbound messages (any message from lead)
            "message": self._handle_inbound_message,
            
            # Replied (lead directly replied to our specific message)
            "sentMessageREPLIED_v2": self._handle_message_replied,
        }
        
        handler = event_handlers.get(event_type)
        if not handler:
            logger.warning(f"⚠️ Unknown event type: {event_type}")
            return {"success": False, "error": f"Unknown event type: {event_type}"}
        
        # Execute handler within transaction for atomicity
        try:
            async with self.db.begin_nested():  # Savepoint for atomicity
                await handler(lead, event_data)
            await self.db.commit()
            
            return {
                "success": True,
                "event_type": event_type,
                "lead_id": lead["id"]
            }
        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Webhook handler error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    # ============================================
    # PRIVATE WEBHOOK HANDLERS
    # ============================================
    
    async def _handle_message_sent(self, lead: dict, event_data: dict) -> None:
        """Handle templateMessageSent event."""
        await self.lead_repo.update_delivery_status(lead["id"], "SENT")
    
    async def _handle_message_delivered(self, lead: dict, event_data: dict) -> None:
        """Handle messageDelivered event - update lead, message, and log activity."""
        lead_id = lead["id"]
        lead_name = lead.get("first_name", "")
        phone_number = lead["mobile_number"]
        wati_msg_id = event_data.get("id", "")
        
        # All updates in single transaction
        await self.lead_repo.update_delivery_status(lead_id, "DELIVERED")
        await self.message_repo.update_status_by_wati_id(wati_msg_id, "DELIVERED")
        await self.activity_repo.log_message_delivered(lead_id, lead_name, phone_number)
    
    async def _handle_message_read(self, lead: dict, event_data: dict) -> None:
        """Handle messageRead event - update lead, message, and log activity."""
        lead_id = lead["id"]
        lead_name = lead.get("first_name", "")
        phone_number = lead["mobile_number"]
        wati_msg_id = event_data.get("id", "")
        
        await self.lead_repo.update_delivery_status(lead_id, "READ")
        await self.message_repo.update_status_by_wati_id(wati_msg_id, "READ")
        await self.activity_repo.log_message_read(lead_id, lead_name, phone_number)
    
    async def _handle_message_failed(self, lead: dict, event_data: dict) -> None:
        """Handle templateMessageFailed event - update status with error reason."""
        lead_id = lead["id"]
        lead_name = lead.get("first_name", "")
        phone_number = lead["mobile_number"]
        wati_msg_id = event_data.get("id", "")
        failed_reason = event_data.get("failedDetail", "Unknown error")
        
        await self.lead_repo.update_delivery_status(lead_id, "FAILED", failed_reason)
        await self.message_repo.update_status_by_wati_id(wati_msg_id, "FAILED", failed_reason)
        await self.activity_repo.log_message_failed(lead_id, lead_name, phone_number, failed_reason)
    
    async def _handle_inbound_message(self, lead: dict, event_data: dict) -> None:
        """Handle inbound message (reply from lead) - create message and log activity."""
        lead_id = lead["id"]
        lead_name = lead.get("first_name", "")
        phone_number = lead["mobile_number"]
        message_text = event_data.get("text", "")
        
        # Create inbound message record
        await self.message_repo.create_inbound_message(
            lead_id=lead_id,
            message_text=message_text,
            wati_message_id=event_data.get("id"),
            wati_conversation_id=event_data.get("conversationId")
        )
        
        # Log reply activity (always global - important!)
        await self.activity_repo.log_reply_received(
            lead_id=lead_id,
            lead_name=lead_name,
            lead_mobile=phone_number,
            reply_text=message_text,
            is_global=True
        )
        
        logger.info(f"💬 Reply received from {lead_name}: {message_text[:50]}...")
    
    async def _handle_message_replied(self, lead: dict, event_data: dict) -> None:
        """
        Handle sentMessageREPLIED_v2 event - lead directly replied to our message.
        
        This is different from 'message' because it includes context about
        which specific message the lead is responding to.
        """
        lead_id = lead["id"]
        lead_name = lead.get("first_name", "")
        phone_number = lead["mobile_number"]
        message_text = event_data.get("text", "")
        original_msg_id = event_data.get("localMessageId", "")
        
        # Update lead status to REPLIED (highest engagement!)
        await self.lead_repo.update_delivery_status(lead_id, "REPLIED")
        
        # Create inbound message record
        await self.message_repo.create_inbound_message(
            lead_id=lead_id,
            message_text=message_text,
            wati_message_id=event_data.get("whatsappMessageId"),
            wati_conversation_id=event_data.get("conversationId")
        )
        
        # Log reply activity with context
        await self.activity_repo.log_reply_received(
            lead_id=lead_id,
            lead_name=lead_name,
            lead_mobile=phone_number,
            reply_text=message_text,
            is_global=True
        )
        
        logger.info(f"💬 Direct reply from {lead_name} to message {original_msg_id}: {message_text[:50]}...")
