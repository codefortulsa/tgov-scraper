from datetime import datetime
from pydantic import BaseModel


class Minutes(BaseModel):
    file: str
    meeting_date: datetime
    doc_id: str
