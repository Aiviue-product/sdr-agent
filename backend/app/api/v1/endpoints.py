from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from app.services.file_service import process_excel_file
import tempfile
from pathlib import Path 

router = APIRouter()

# Max file size: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024  # bytes


@router.post("/verify-leads/")
async def verify_leads_endpoint(
    file: UploadFile = File(...),
    verification_mode: str = Form("individual")
):
    # 1️ Validate file extension
    if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload Excel (.xlsx, .xls) or CSV."
        )

    # 2 Stream file to temp storage + enforce size limit
    try:
        suffix = Path(file.filename).suffix
        total_size = 0

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_input_path = tmp.name

            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                total_size += len(chunk)

                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File too large. Maximum allowed size is 10MB."
                    )

                tmp.write(chunk)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    # 3 Process file (business logic)
    try:
        processed_file_stream = await process_excel_file( 
            input_file_path=temp_input_path,
            verification_mode=verification_mode 
        )

        return StreamingResponse(
            processed_file_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=verified_leads.xlsx"
            }
        )

    except Exception as e:
        print(f"Processing Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred during processing."
        )
    