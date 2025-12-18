import pandas as pd 
import io
import time
from pathlib import Path
from app.services.email_service import verify_individual, verify_bulk_batch


async def process_excel_file(input_file_path: str, verification_mode: str) -> io.BytesIO: 
    # 1. Load Data (NOW FROM FILE PATH)
    print("TYPE:", type(input_file_path))

    try:
        df = pd.read_excel(input_file_path)
    except Exception:
        df = pd.read_csv(input_file_path)

    df.columns = df.columns.str.strip() 
     
    if 'status' not in df.columns:
        df['status'] = 'unverified'  
    if 'tag' not in df.columns:
        df['tag'] = ''

    # 2. Process based on Mode
    if verification_mode.lower() == 'bulk': 
        await _process_bulk_logic(df)
    else:
        await _process_individual_logic(df)

    # 3. Save to BytesIO (NO CHANGE)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)

    output.seek(0)
    return output


async def _process_bulk_logic(df):
    """Chunks data and calls Bulk API"""

    # 1. Create a mask for Top Priority
    if 'Priority' in df.columns:
        mask = df['Priority'].astype(str).str.lower().str.strip() == 'top'
        rows_to_process = df[mask]
    else:
        rows_to_process = df
        mask = None

    # 2. Extract Emails
    emails_to_check = rows_to_process['email'].dropna().unique().tolist()

    # 3. Call Bulk API in Chunks
    CHUNK_SIZE = 100
    verification_results = {}  

    for i in range(0, len(emails_to_check), CHUNK_SIZE):
        chunk = emails_to_check[i:i + CHUNK_SIZE]
        batch_results = verify_bulk_batch(chunk)
        verification_results.update(batch_results)

    # 4. Update verified rows
    for index, row in rows_to_process.iterrows():
        email = row.get('email')
        if email in verification_results:
            raw_status = verification_results[email]

            if raw_status == 'valid':
                df.at[index, 'status'] = 'valid'
                df.at[index, 'tag'] = 'Verified'
            else:
                df.at[index, 'status'] = 'invalid'
                df.at[index, 'tag'] = 'Review Required'

    # 5. Handle skipped rows
    if mask is not None:
        df.loc[~mask, 'status'] = 'skipped_low_priority'


async def _process_individual_logic(df):
    for index, row in df.iterrows():
        priority = str(row.get('Priority', '')).lower().strip()
        email = row.get('email', '')

        if priority == 'top':
            status, tag = verify_individual(email)
            df.at[index, 'status'] = status
            df.at[index, 'tag'] = tag
            time.sleep(1)
        else:
            current_status = df.at[index, 'status']
            if pd.isna(current_status) or current_status == 'unverified':
                df.at[index, 'status'] = 'skipped_low_priority'
