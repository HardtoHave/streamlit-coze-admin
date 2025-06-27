from datetime import datetime
from typing import Optional, Literal

from beanie import Document, Indexed
from pydantic import Field

class InvitationCode(Document):
    code: Indexed(str, unique=True) 
    status: Literal["unused", "used"] = "unused"
    activated_by_sys_uuid: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    used_at: Optional[datetime] = None

    class Settings:
        name = "invitation_codes"
