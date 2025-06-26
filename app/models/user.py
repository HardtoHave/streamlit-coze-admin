from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field

class AuthorizedUser(Document):
    sys_uuid: str
    activated_via_code: Optional[str] = None
    activated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "authorized_users"