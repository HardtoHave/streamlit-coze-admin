from functools import lru_cache
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.config import settings
from app.models import InvitationCode, AuthorizedUser

@lru_cache
def _get_client() -> AsyncIOMotorClient:
    return AsyncIOMotorClient(settings.mongodb_url)

async def init_db():
    client = _get_client()
    await init_beanie(
        database=client[settings.database_name],
        document_models=[InvitationCode, AuthorizedUser],
    )