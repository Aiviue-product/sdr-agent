import pandas as pd
import io
import time
from app.services.email_service import verify_individual, verify_bulk_batch

async def process_excel_file(file_content: bytes, mode: str) -> io.BytesIO:
    # 1. Load Data
    try:
        df = pd.read_excel(io.BytesIO(file_content))
    except:
        df = pd.read_csv(io.BytesIO(file_content))

    df.columns = df.columns.str.strip()
    
    if 'status' not in df.columns:
        df['status'] = 'unverified'
    if 'tag' not in df.columns:
        df['tag'] = ''

    # 2. Process based on Mode
    if mode.lower() == 'bulk':
        await _process_bulk_logic(df)
    else:
        await _process_individual_logic(df)

    # 3. Save
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    
    output.seek(0)
    return output

async def _process_bulk_logic(df):
    if 'Priority' in df.columns:
        mask = df['Priority'].astype(str).str.lower().str.strip() == 'top'
        rows_to_process = df[mask]
    else:
        rows_to_process = df

    emails_to_check = rows_to_process['email'].dropna().unique().tolist()
    
    CHUNK_SIZE = 100
    verification_results = {}
    
    for i in range(0, len(emails_to_check), CHUNK_SIZE):
        chunk = emails_to_check[i:i + CHUNK_SIZE]
        batch_results = verify_bulk_batch(chunk)
        verification_results.update(batch_results)
    
    # Update DataFrame with STRICT logic
    for index, row in rows_to_process.iterrows():
        email = row.get('email')
        if email in verification_results:
            raw_status = verification_results[email]
            
            # --- STRICT MAPPING FOR BULK ---
            if raw_status == 'valid':
                df.at[index, 'status'] = 'valid'
                df.at[index, 'tag'] = 'Verified'
            else:
                # Map everything else (do_not_mail, unknown, etc.) to 'invalid'
                df.at[index, 'status'] = 'invalid'
                df.at[index, 'tag'] = 'Review Required'

async def _process_individual_logic(df):
    for index, row in df.iterrows():
        priority = str(row.get('Priority', '')).lower().strip()
        email = row.get('email', '')
        
        if priority == 'top':
            # verify_individual now handles the strict mapping internally
            status, tag = verify_individual(email)
            df.at[index, 'status'] = status
            df.at[index, 'tag'] = tag
            time.sleep(1)
        else:
            current_status = df.at[index, 'status']
            if pd.isna(current_status) or current_status == 'unverified':
                df.at[index, 'status'] = 'skipped_low_priority' 