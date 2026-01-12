from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
import logging
import tempfile
from pathlib import Path

from app.modules.email_outreach.services.file_service import process_excel_file
from app.shared.core.constants import (
    MAX_FILE_SIZE_BYTES, 
    FILE_CHUNK_SIZE_BYTES, 
    ALLOWED_EXTENSIONS, 
    ALLOWED_MIME_TYPES
)

logger = logging.getLogger("endpoints")

router = APIRouter()


@router.post("/verify-leads/")
async def verify_leads_endpoint(
    file: UploadFile = File(...),
    verification_mode: str = Form("individual")
):
    # 1. Validate file extension
    file_path = Path(file.filename)
    extension = file_path.suffix.lower()
    
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid extension {extension}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 2. Validate MIME Type (Content-Type)
    if file.content_type not in ALLOWED_MIME_TYPES:
        logger.warning(f"Unexpected MIME type: {file.content_type}")
        # We don't block strictly on MIME yet as browsers can be inconsistent, 
        # but we'll do the deep check next.

    # 3. Deep Magic Number Check (First few bytes)
    header = await file.read(4)
    await file.seek(0) # IMPORTANT: Reset file pointer after reading header

    if extension == ".xlsx":
        # .xlsx is a ZIP file, first 4 bytes must be 50 4B 03 04 (PK\x03\x04)
        if header != b'PK\x03\x04':
            raise HTTPException(
                status_code=400, 
                detail="File content does not match .xlsx format (malicious or corrupted)"
            )
    elif extension == ".csv":
        # CSV is text. We'll at least ensure it's not a binary file by checking for null bytes
        if b'\x00' in header:
            raise HTTPException(
                status_code=400,
                detail="CSV file contains binary data (malicious or corrupted)"
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
