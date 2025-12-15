from fastapi import APIRouter, UploadFile, File, Form, HTTPException 
from fastapi.responses import StreamingResponse
from app.services.file_service import process_excel_file 

router = APIRouter()

@router.post("/verify-leads/")
async def verify_leads_endpoint(
    file: UploadFile = File(...), 
    verification_mode: str = Form("individual")
):
    # Validation
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload Excel or CSV.")

    try:
        # Read content asynchronously
        contents = await file.read()
        
        # Hand off to service layer
        processed_file = await process_excel_file(contents, verification_mode)
        
        # Return as a downloadable stream
        return StreamingResponse(
            processed_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=verified_leads.xlsx"}
        )
    except Exception as e:
        print(f"API Error: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred during processing.")