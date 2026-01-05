
from typing import Optional, List
from pydantic import BaseModel 

# --- REQUEST MODELS ---
class SendEmailRequest(BaseModel): 
    template_id: int
    email_body: str

class SendSequenceRequest(BaseModel):
    email_1: str
    email_2: str
    email_3: str
    email_1_subject: Optional[str] = None
    email_2_subject: Optional[str] = None
    email_3_subject: Optional[str] = None