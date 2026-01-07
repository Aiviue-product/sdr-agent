from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
import logging
import tempfile
from pathlib import Path

from app.services.file_service import process_excel_file
from app.core.constants import MAX_FILE_SIZE_BYTES, FILE_CHUNK_SIZE_BYTES

logger = logging.getLogger("endpoints")

router = APIRouter()


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

            while chunk := await file.read(FILE_CHUNK_SIZE_BYTES):
                total_size += len(chunk)

                if total_size > MAX_FILE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE_BYTES // (1024*1024)}MB."
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
        logger.error(f"Processing Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred during processing."
        )
    