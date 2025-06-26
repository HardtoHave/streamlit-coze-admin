import secrets
from pymongo.errors import DuplicateKeyError

from app.models.invitation import InvitationCode

__all__ = ["create_invite", "list_invites"]

async def create_invite(length: int = 8) -> InvitationCode:
    """生成唯一邀请码"""
    while True:
        code = secrets.token_hex(length // 2).upper()
        try:
            invite = InvitationCode(code=code)
            await invite.insert()
            return invite
        except DuplicateKeyError:
            continue  # 冲突则重试

async def list_invites() -> list[InvitationCode]:
    return await InvitationCode.find_all().to_list()