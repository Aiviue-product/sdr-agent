# backend/tests/conftest.py
"""
Shared fixtures for all test modules.
Simplified version - avoids async fixtures to prevent event loop issues.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Import app
from app.main import app


# --- TEST CLIENT FIXTURE ---
@pytest.fixture(scope="module")
def test_client():
    """Create a FastAPI test client."""
    return TestClient(app)


# --- SAMPLE LEAD DATA FIXTURES ---
@pytest.fixture
def sample_valid_lead():
    """A complete, valid lead ready for campaign."""
    return {
        "email": "test_fixture@example.com",
        "first_name": "Test",
        "last_name": "User",
        "company_name": "Test Corp",
        "linkedin_url": "https://linkedin.com/in/testuser",
        "mobile_number": "+1234567890",
        "designation": "CEO",
        "sector": "Technology",
        "priority": "top",
        "verification_status": "valid",
        "verification_tag": "Verified",
        "lead_stage": "campaign"
    }


@pytest.fixture
def sample_enrichment_lead():
    """A lead with missing data (needs enrichment)."""
    return {
        "email": "enrichment_test@example.com",
        "first_name": "Partial",
        "last_name": None,
        "company_name": None,
        "linkedin_url": None,
        "mobile_number": None,
        "designation": None,
        "sector": None,
        "priority": "top",
        "verification_status": "valid",
        "verification_tag": "Verified",
        "lead_stage": "enrichment"
    }


# --- MOCK FIXTURES FOR EXTERNAL SERVICES ---
@pytest.fixture
def mock_zerobounce_valid():
    """Mock ZeroBounce API returning valid response."""
    with patch("app.services.email_service.requests.get") as mock:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "valid"}
        mock.return_value = mock_response
        yield mock


@pytest.fixture
def mock_zerobounce_invalid():
    """Mock ZeroBounce API returning invalid response."""
    with patch("app.services.email_service.requests.get") as mock:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "catch-all"}
        mock.return_value = mock_response
        yield mock


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini AI response for intelligence service."""
    return {
        "hiring_signal": True,
        "hiring_roles": "Software Engineer, DevOps",
        "key_competencies": "Python, AWS, Docker",
        "pain_points": "Scaling engineering team",
        "standardized_persona": "Tech / Engineering",
        "summary_hook": "Saw you're expanding the engineering team!"
    }


@pytest.fixture
def mock_apify_response():
    """Mock Apify scraper response."""
    return {
        "success": True,
        "profile_url": "https://linkedin.com/in/testuser",
        "username": "testuser",
        "scraped_data": [
            {
                "post_text": "We're hiring 5 engineers to join our team!",
                "date": "2024-12-28",
                "designation": "Head of HR",
                "post_url": "https://linkedin.com/posts/123",
                "author_name": "Test User"
            }
        ]
    }
