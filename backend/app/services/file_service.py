
import pandas as pd
import io
import time
import logging
from app.services.email_service import verify_individual, verify_bulk_batch
from app.services.lead_service import save_verified_leads_to_db

# Setup Logger
logger = logging.getLogger("file_service")

async def process_excel_file(input_file_path: str, verification_mode: str) -> io.BytesIO:
    """
    Robust file processor that finds the correct header row, normalizes columns,
    and enforces strict priority/status logic.
    """
    # 1. Load Data (Initial Raw Load)
    try:
        # Load without headers first to inspect the structure
        df_raw = pd.read_excel(input_file_path, header=None)
    except Exception:
        df_raw = pd.read_csv(input_file_path, header=None)

    # --- SMART HEADER SEARCH ---
    # Many files have title rows (e.g. "Leads 2025") in Row 1.
    # We scan the first 10 rows to find the row that actually looks like a header (contains 'email').
    header_row_index = 0
    found_header = False
    
    # Iterate through first 10 rows to find the "email" column
    for i, row in df_raw.head(10).iterrows():
        # Convert entire row to string, lowercase, and list for searching
        row_values = row.astype(str).str.lower().tolist()
        
        # Check for key indicators of a header row
        if 'email' in row_values or 'e-mail' in row_values or 'email id' in row_values:
            header_row_index = i
            found_header = True
            logger.info(f"✅ Found Header at Row {i+1}")
            break
    
    # Reload dataframe with the correct header row
    if found_header:
        try:
            df = pd.read_excel(input_file_path, header=header_row_index)
        except:
            df = pd.read_csv(input_file_path, header=header_row_index)
    else:
        # Fallback: Treat the first row as header if no "email" found
        df = df_raw.rename(columns=df_raw.iloc[0]).drop(df_raw.index[0])

    # STEP A: Clean Headers (Aggressive Normalization)
    df.columns = df.columns.astype(str).str.strip().str.lower().str.replace(' ', '_', regex=False)
    
    # --- Dynamic Priority Column Finder ---
    # Fixes the issue where columns like "Priority Level" or "Lead Priority" were ignored
    if 'priority' not in df.columns:
        for col in df.columns:
            if 'priority' in col:
                logger.info(f"⚠️ Renaming found column '{col}' to 'priority'")
                df.rename(columns={col: 'priority'}, inplace=True)
                break
    
    # STEP B: Master Column Mapping (Standardize to Lowercase Keys)
    column_mapping = {
        # Fix Typos / Variations
        'deignation':     'designation',   # Typo fix
        'first_name':     'firstname',     # Variation (handles "First Name" -> "first_name")
        'last_name':      'lastname',      # Variation (handles "Last Name" -> "last_name")
        'mobile':         'mobile_number', # Variation
        'phone':          'mobile_number', 
        'mobile_no':      'mobile_number',
        'company':        'company_name',  
        'linkedin':       'linkedin_url',  
        'email_id':       'email',         
        'e-mail':         'email',         
        'industry':       'sector',
        'priority':       'priority',
        'sector':         'sector',
        'email':          'email',
        'status':         'status',
        'tag':            'tag'      # Map 'Industry' to 'Sector'
    }

    # Apply the renaming
    df.rename(columns=column_mapping, inplace=True)

    # Log found columns for debugging
    logger.info(f"📂 Detected & Normalized Columns: {df.columns.tolist()}")

    # Initialize status columns if missing
    if 'status' not in df.columns:
        df['status'] = 'unverified'
    if 'tag' not in df.columns:
        df['tag'] = ''

    # 2. Process based on Mode
    if verification_mode.lower() == 'bulk':
        await _process_bulk_logic(df)
    else:
        await _process_individual_logic(df)

    # 3. Save Verified Leads to Database
    await save_verified_leads_to_db(df)

    # 4. Save to BytesIO
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    
    output.seek(0)
    return output

# --- Helper Functions (Strict Logic) ---

async def _process_bulk_logic(df):
    """Chunks data and calls Bulk API with STRICT Filtering and Status Checks"""
    
    # 1. STRICT PRIORITY FILTERING
    if 'priority' in df.columns:
        # Force column to string, lowercase, strip whitespace (Handles " Top " or "TOP")
        df['priority'] = df['priority'].astype(str).str.lower().str.strip()
        mask = df['priority'] == 'top'
        rows_to_process = df[mask]
        logger.info(f"🔍 Bulk Filter: Found {len(rows_to_process)} 'top' rows out of {len(df)} total.")
    else:
        logger.warning("⚠️ No 'priority' column found. Processing ALL rows.")
        rows_to_process = df
        mask = None

    # 2. Extract Emails (Cleaned & Lowercase)
    emails_to_check = rows_to_process['email'].dropna().astype(str).str.strip().str.lower().unique().tolist()
    
    if not emails_to_check:
        logger.warning("⚠️ No emails found to verify in Bulk Logic.")
        return

    CHUNK_SIZE = 100
    verification_results = {}
    api_failed = False

    # 3. Batch Process
    for i in range(0, len(emails_to_check), CHUNK_SIZE):
        chunk = emails_to_check[i:i + CHUNK_SIZE]
        batch_results = verify_bulk_batch(chunk)
        
        if not batch_results and chunk: 
            logger.error(f"❌ Batch Verification Failed for chunk starting index {i}")
            api_failed = True
        
        verification_results.update(batch_results)

    # 4. Map Results Back to DataFrame (Strict Loop)
    for index, row in rows_to_process.iterrows():
        email = str(row.get('email', '')).strip().lower()
        
        if email in verification_results:
            raw_status = str(verification_results[email]).lower().strip()
            
            # STRICT STATUS LOGIC
            if raw_status == 'valid':
                df.at[index, 'status'] = 'valid'
                df.at[index, 'tag'] = 'Verified'
            elif raw_status == 'catch-all':
                df.at[index, 'status'] = 'catch-all'
                df.at[index, 'tag'] = 'Risky / Review'
            elif raw_status in ['do_not_mail', 'spamtrap', 'abuse']:
                df.at[index, 'status'] = 'invalid'
                df.at[index, 'tag'] = 'Do Not Mail'
            else:
                df.at[index, 'status'] = 'invalid'
                df.at[index, 'tag'] = 'Review Required'
                
        elif api_failed:
            df.at[index, 'status'] = 'api_error'
            df.at[index, 'tag'] = 'Check API Key/Credits'

    # 5. Handle Skipped Rows
    if mask is not None:
        df.loc[~mask, 'status'] = 'skipped_low_priority'
        df.loc[~mask, 'tag'] = 'Review Required'



async def _process_individual_logic(df):
    """
    Process row-by-row with STRICT input cleaning and status handling. 
    Matches the logic structure of _process_bulk_logic exactly.
    """
    
    # 1. STRICT PRIORITY FILTERING (Global Clean)
    # We clean the whole column once, just like in Bulk logic
    if 'priority' in df.columns:
        df['priority'] = df['priority'].astype(str).str.lower().str.strip()
    else:
        logger.warning("⚠️ Individual Logic: 'priority' column missing. Will default to processing ALL or handling logic.")

    # 2. Iterate Row-by-Row
    for index, row in df.iterrows():
        
        # Get cleaned priority (defaults to empty string if missing)
        priority = row.get('priority', '')
        
        # Get and clean email
        email_raw = str(row.get('email', ''))
        email = email_raw.lower().strip()

        # SKIP EMPTY EMAILS
        if not email or email == 'nan':
            continue

        # 3. Check Priority
        if priority == 'top':
            try:
                # Call Individual API
                # NOTE: Assuming verify_individual returns a tuple or just the raw_status. 
                # We need the RAW status (e.g., 'valid', 'catch-all') to run the logic below.
                # If verify_individual returns (status, tag), take index [0] as raw_status.
                
                raw_response = verify_individual(email) 
                
                # Handle if function returns tuple (status, tag) or just status
                if isinstance(raw_response, (tuple, list)):
                    raw_status = str(raw_response[0]).lower().strip()
                else:
                    raw_status = str(raw_response).lower().strip()

                # --- STRICT STATUS LOGIC (COPIED FROM BULK) ---
                if raw_status == 'valid':
                    df.at[index, 'status'] = 'valid'
                    df.at[index, 'tag'] = 'Verified'
                
                elif raw_status == 'catch-all':
                    df.at[index, 'status'] = 'catch-all'
                    df.at[index, 'tag'] = 'Risky / Review'
                
                elif raw_status in ['do_not_mail', 'spamtrap', 'abuse']:
                    df.at[index, 'status'] = 'invalid'
                    df.at[index, 'tag'] = 'Do Not Mail'
                
                else:
                    # Default for 'invalid', 'unknown', or unexpected responses
                    df.at[index, 'status'] = 'invalid'
                    df.at[index, 'tag'] = 'Review Required'
                
                # Rate limit protection (Crucial for individual loops)
                time.sleep(1) 

            except Exception as e:
                # Handle API Errors exactly like 'api_failed' in bulk
                logger.error(f"❌ Individual API Error for {email}: {str(e)}")
                df.at[index, 'status'] = 'api_error'
                df.at[index, 'tag'] = 'Check API Key/Credits'

        else:
            # 4. Handle Skipped Rows (Low/Medium/Empty)
            # Only mark as skipped if it wasn't already processed
            current_status = df.at[index, 'status']
            
            if pd.isna(current_status) or current_status == 'unverified':
                df.at[index, 'status'] = 'skipped_low_priority'
                df.at[index, 'tag'] = 'Review Required'