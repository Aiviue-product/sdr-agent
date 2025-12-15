# backend/tests/test_main.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
import pandas as pd
import io

# Create a test client (acts like a fake browser/frontend) 
client = TestClient(app)

# --- 1. UNIT TEST: Test the Logic without API ---
def test_verify_individual_valid_logic():
    """
    Test that 'valid' from API maps to 'Verified'.
    We MOCK requests.get so we don't actually call ZeroBounce.
    """
    from app.services.email_service import verify_individual

    # Setup the Mock
    with patch("app.services.email_service.requests.get") as mock_get:
        # Define what the fake API returns
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "valid"}
        mock_get.return_value = mock_response

        # Run the function
        status, tag = verify_individual("good@example.com")

        # Assertions (Check if result is what we expect)
        assert status == "valid"
        assert tag == "Verified"

def test_verify_individual_invalid_logic():
    """
    Test that 'catch-all' (or anything else) maps to 'invalid' / 'Review Required'.
    """
    from app.services.email_service import verify_individual

    with patch("app.services.email_service.requests.get") as mock_get:
        # Fake a "catch-all" response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "catch-all"}
        mock_get.return_value = mock_response

        status, tag = verify_individual("risky@example.com")

        # STRICT LOGIC CHECK: catch-all should become invalid
        assert status == "invalid" 
        assert tag == "Review Required"

# --- 2. INTEGRATION TEST: Test the File Upload Endpoint ---
def test_upload_endpoint():
    """
    Test uploading a real Excel file to the FastAPI endpoint.
    """
    # 1. Create a dummy Excel file in memory
    df = pd.DataFrame({
        "email": ["test@example.com"],
        "Priority": ["top"]
    })
    
    file_buffer = io.BytesIO()
    with pd.ExcelWriter(file_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    file_buffer.seek(0) # Rewind buffer to start

    # 2. Mock the service layer (so we don't hit API during file process)
    # We force verify_individual to always return 'valid' for this test
    with patch("app.services.file_service.verify_individual") as mock_verify:
        mock_verify.return_value = ("valid", "Verified")

        # 3. Send POST request to your API
        response = client.post(
            "/api/v1/verify-leads/",
            files={"file": ("test.xlsx", file_buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"verification_mode": "individual"}
        )

        # 4. Check results
        assert response.status_code == 200
        # Check if we got an excel file back
        assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"