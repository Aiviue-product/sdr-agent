import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from app.modules.signal_outreach.services.linkedin_outreach_service import LinkedInOutreachService

# Mock data
SAMPLE_SEARCH_RESULTS = {
    "success": True,
    "leads": [
        {
            "full_name": "John Doe",
            "linkedin_url": "https://linkedin.com/JohnDoe",
            "headline": "CEO at TechCorp",
            "post_data": {"text": "Hiring Engineers", "search_keyword": "hiring"}
        },
        {
            "full_name": "Jane Smith",
            "linkedin_url": "https://linkedin.com/JaneSmith",
            "headline": "HR at BuildIt",
            "post_data": {"text": "Looking for developers", "search_keyword": "hiring"}
        }
    ],
    "stats": {"raw_results": 2}
}

@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.get_leads_by_ids = AsyncMock()
    repo.bulk_upsert_leads = AsyncMock()
    repo.update_ai_enrichment = AsyncMock()
    repo.update_dm_sent = AsyncMock()
    return repo

# --- TESTS ---

def test_run_full_outreach_search_logic():
    """
    Test that the orchestrator calls search_by_keywords and bulk_upsert_leads.
    """
    async def test_logic():
        mock_search = AsyncMock(return_value=SAMPLE_SEARCH_RESULTS)
        mock_intel = AsyncMock(return_value={"hiring_signal": True, "linkedin_dm": "Test"})
        
        mock_repo = MagicMock()
        mock_repo.bulk_upsert_leads = AsyncMock(return_value={
            "inserted_count": 2, "updated_count": 0, "skipped_count": 0
        })
        
        service = LinkedInOutreachService(MagicMock())
        service.repo = mock_repo
        
        # Patch the imported instances inside the module
        with patch("app.modules.signal_outreach.services.linkedin_outreach_service.linkedin_search_service.search_by_keywords", mock_search), \
             patch("app.modules.signal_outreach.services.linkedin_outreach_service.linkedin_intelligence_service.analyze_and_generate_dm", mock_intel):
            
            result = await service.run_full_outreach_search(keywords=["hiring"])
            
            assert result["success"] == True
            assert result["leads_found"] == 2
            mock_search.assert_called_once()
            mock_intel.assert_called()
            mock_repo.bulk_upsert_leads.assert_called_once()
            
    asyncio.run(test_logic())

def test_refresh_lead_analysis_logic():
    """
    Test that refreshing analysis calls Intelligence service and updates repo.
    """
    async def test_logic():
        lead_id = 123
        mock_lead = {
            "id": lead_id,
            "full_name": "Test User",
            "headline": "CEO",
            "post_data": [{"text": "Found post", "search_keyword": "hiring"}]
        }
        
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_lead)
        mock_repo.update_ai_enrichment = AsyncMock()
        
        mock_intelligence = AsyncMock(return_value={
            "hiring_signal": True,
            "pain_points": "Hiring",
            "ai_variables": {"key": "val"},
            "linkedin_dm": "Hello"
        })
        
        service = LinkedInOutreachService(MagicMock())
        service.repo = mock_repo
        
        with patch("app.modules.signal_outreach.services.linkedin_outreach_service.linkedin_intelligence_service.analyze_and_generate_dm", mock_intelligence):
            # Also need to mock refresh_lead_analysis manually if we want to test that specific method
            # but here we test the service instance method
            result = await service.refresh_lead_analysis(lead_id)
            
            assert result["success"] == True
            mock_repo.get_by_id.assert_called_once_with(lead_id)
            mock_intelligence.assert_called_once()
            mock_repo.update_ai_enrichment.assert_called_once()
            
    asyncio.run(test_logic())

def test_bulk_refresh_leads_logic():
    """
    Test bulk AI analysis refresh.
    """
    async def test_logic():
        lead_ids = [1, 2]
        mock_leads = [
            {"id": 1, "full_name": "U1", "post_data": [{"text": "P1"}]},
            {"id": 2, "full_name": "U2", "post_data": [{"text": "P2"}]}
        ]
        
        mock_repo = MagicMock()
        mock_repo.get_leads_by_ids = AsyncMock(return_value=mock_leads)
        mock_repo.update_ai_enrichment = AsyncMock()
        
        mock_intelligence = AsyncMock(return_value={"hiring_signal": True})
        
        service = LinkedInOutreachService(MagicMock())
        service.repo = mock_repo
        
        with patch("app.modules.signal_outreach.services.linkedin_outreach_service.linkedin_intelligence_service.analyze_and_generate_dm", mock_intelligence):
            results = await service.bulk_refresh_leads(lead_ids)
            
            assert results["success_count"] == 2
            assert mock_repo.get_leads_by_ids.call_count == 1  # Verify N+1 fix (Batch fetch)
            assert mock_intelligence.call_count == 2
            assert mock_repo.update_ai_enrichment.call_count == 2
            
    asyncio.run(test_logic())
