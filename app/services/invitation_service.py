# ==== app/services/invitation_service.py ====
import secrets
from typing import List, Optional
from pymongo.errors import DuplicateKeyError

from app.models.invitation import InvitationCode
from app.models.user import AuthorizedUser

__all__ = ["create_invite", "list_invites", "delete_invite"]


async def create_invite(length: int = 8) -> InvitationCode:
    while True:
        code = secrets.token_hex(length // 2).upper()
        try:
            invite = InvitationCode(code=code)
            await invite.insert()
            return invite
        except DuplicateKeyError:
            continue  # 冲突则重试


async def list_invites() -> List[InvitationCode]:
    return await InvitationCode.find_all().sort("-created_at").to_list()


async def delete_invite(code: str) -> bool:
    invite: Optional[InvitationCode] = await InvitationCode.find_one(
        InvitationCode.code == code
    )
    if not invite:
        return False

    # 删除绑定用户（如果有）
    users = await AuthorizedUser.find(
        AuthorizedUser.activated_via_code == code
    ).to_list()
    for u in users:
        await u.delete()

    # 删除邀请码
    await invite.delete()
    return True
