import streamlit as st

st.set_page_config(page_title="Coze Agent 后台管理", layout="wide")

import asyncio
import threading
import pandas as pd
import streamlit_authenticator as stauth
from streamlit.runtime.scriptrunner import add_script_run_ctx

from app.config import settings
from app.database import init_db
from app.services.invitation_service import create_invite, list_invites
from app.models.invitation import InvitationCode
from app.models.user import AuthorizedUser


@st.cache_resource(show_spinner=False)
def get_async_loop():
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop.run_forever, daemon=True)
    add_script_run_ctx(t) 
    t.start()
    return loop


def run_async(coro):
    """在后台事件循环上同步执行协程并返回结果"""
    loop = get_async_loop()
    return asyncio.run_coroutine_threadsafe(coro, loop).result()


async def deactivate_invite_and_user(invite_id: str, user_sys_uuid: str = None):
    st.warning(f"正在停用邀请码 ID: {invite_id}...", icon="⏳")

    try:
        if user_sys_uuid:
            user_to_delete = await AuthorizedUser.find_one(AuthorizedUser.sys_uuid == user_sys_uuid)
            if user_to_delete:
                await user_to_delete.delete()
                st.success(f"✅ 成功删除关联用户授权信息 (UUID: {user_sys_uuid})。", icon="🗑️")
            else:
                st.info(f"ℹ️ 未找到关联的用户授权信息 (UUID: {user_sys_uuid})。", icon="🤷‍♀️")

        invite_to_delete = await InvitationCode.find_one(InvitationCode.id == invite_id)
        if invite_to_delete:
            await invite_to_delete.delete()
            st.success(f"✅ 成功删除邀请码 (Code: {invite_to_delete.code})。", icon="❌")
        else:
            st.error(f"❌ 未找到邀请码 ID: {invite_id}。", icon="🚫")
        st.rerun()
    except Exception as e:
        st.error(f"❌ 停用操作失败: {e}", icon="🚨")


# ---------- 1. 认证配置 ----------
auth_config = {
    "credentials": {
        "usernames": {
            "admin": {
                "email": "admin@yourdomain.com",
                "name": "Administrator",
                "password": settings.admin_password_hash,
            }
        }
    },
    "cookie": {
        "expiry_days": 30,
        "key": settings.cookie_key,
        "name": settings.cookie_name,
    },
}

authenticator = stauth.Authenticate(
    auth_config["credentials"],
    auth_config["cookie"]["name"],
    auth_config["cookie"]["key"],
    auth_config["cookie"]["expiry_days"],
)

# ---------- 2. 登录 ----------
name, auth_status, _ = authenticator.login(location="main")

if auth_status is False:
    st.error("用户名或密码错误")
    st.stop()
elif auth_status is None:
    st.warning("请输入用户名和密码")
    st.stop()

# ---------- 3. 主界面 ----------
if auth_status:
    st.sidebar.title(f"欢迎, {name}!")
    authenticator.logout("退出", "sidebar")

    # 3-1 初始化数据库（只执行一次）
    if "db_ok" not in st.session_state:
        try:
            run_async(init_db())
            st.session_state["db_ok"] = True
            st.sidebar.success("✅ 数据库已连接")
        except Exception as e:
            st.error(f"数据库初始化失败: {e}")
            st.stop()

    st.header("✨ 邀请码管理")

    # 3-2 生成邀请码
    if st.button("生成新邀请码", type="primary"):
        with st.spinner("生成中…"):
            invite: InvitationCode = run_async(create_invite())
            st.success(f"已生成邀请码: {invite.code}")

    # 3-3 显示邀请码列表
    st.subheader("📚 邀请码列表")
    invites = run_async(list_invites())
        if invites:
        cols = st.columns([1, 1, 2, 2, 2, 1])
        with cols[0]:
            st.write("**邀请码**")
        with cols[1]:
            st.write("**状态**")
        with cols[2]:
            st.write("**激活用户UUID**")
        with cols[3]:
            st.write("**创建时间**")
        with cols[4]:
            st.write("**使用时间**")
        with cols[5]:
            st.write("**操作**")
        for invite in invites:
            col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 2, 2, 2, 1])
            with col1:
                st.code(invite.code)  # 使用st.code显示邀请码，使其易于复制
            with col2:
                # 根据状态显示不同颜色
                if invite.status == "active":
                    st.success("🟢 活跃")
                elif invite.status == "used":
                    st.info("🔵 已使用")
                else:
                    st.error("🔴 未知")
            with col3:
                st.write(invite.activated_by_sys_uuid if invite.activated_by_sys_uuid else "N/A")
            with col4:
                st.write(
                    pd.to_datetime(invite.created_at, errors="coerce").strftime("%Y-%m-%d %H:%M:%S")
                    if invite.created_at else ""
                )
            with col5:
                st.write(
                    pd.to_datetime(invite.used_at, errors="coerce").strftime("%Y-%m-%d %H:%M:%S")
                    if invite.used_at else ""
                )
            with col6:
                # 只有在活跃或已使用状态下才显示停用按钮
                if invite.status == "active" or invite.status == "used":
                    if st.button("停用", key=f"deactivate_btn_{invite.id}", help="点击停用此邀请码并删除关联用户",
                                 type="secondary"):
                        # 运行异步删除操作
                        run_async(deactivate_invite_and_user(invite.id, invite.activated_by_sys_uuid))
                else:
                    st.write("已停用")
        else:
            st.info("暂无邀请码", icon="📝")


    # 3-4 已激活用户
    st.header("👥 已激活用户")
    users = run_async(AuthorizedUser.find_all().to_list())
    if users:
        df_u = pd.DataFrame([u.model_dump() for u in users])
        df_u["activated_at"] = (
            pd.to_datetime(df_u["activated_at"], errors="coerce")
            .dt.strftime("%Y-%m-%d %H:%M:%S")
            .fillna("")
        )
        st.dataframe(df_u[["sys_uuid", "activated_via_code", "activated_at"]])
    else:
        st.info("暂无激活用户")
