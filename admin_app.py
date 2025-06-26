import streamlit as st

# ⚠️ set_page_config 必须最先调用
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


# ---------- 0. 单例事件循环 ----------
@st.cache_resource(show_spinner=False)  # ✅ 新写法
def get_async_loop():
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop.run_forever, daemon=True)
    add_script_run_ctx(t)  # 让 Streamlit 识别后台线程
    t.start()
    return loop


def run_async(coro):
    """在后台事件循环上同步执行协程并返回结果"""
    loop = get_async_loop()
    return asyncio.run_coroutine_threadsafe(coro, loop).result()


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
        df = pd.DataFrame([i.model_dump() for i in invites])
        df["created_at"] = (
            pd.to_datetime(df["created_at"], errors="coerce")
            .dt.strftime("%Y-%m-%d %H:%M:%S")
            .fillna("")
        )
        df["used_at"] = (
            pd.to_datetime(df["used_at"], errors="coerce")
            .dt.strftime("%Y-%m-%d %H:%M:%S")
            .fillna("")
        )
        st.dataframe(df[["code", "status", "activated_by_sys_uuid", "created_at", "used_at"]])
    else:
        st.info("暂无邀请码")

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
