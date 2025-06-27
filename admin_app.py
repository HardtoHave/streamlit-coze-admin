# ==== admin_app.py ====
import streamlit as st

st.set_page_config(page_title="Coze Agent 后台管理", layout="wide")

import asyncio
import threading
import pandas as pd
import streamlit_authenticator as stauth
from streamlit.runtime.scriptrunner import add_script_run_ctx

from app.config import settings
from app.database import init_db
from app.services.invitation_service import (
    create_invite,
    list_invites,
    delete_invite,
)
from app.models.invitation import InvitationCode
from app.models.user import AuthorizedUser


# ---------- 0. 单例事件循环 ----------
@st.cache_resource(show_spinner=False)
def get_async_loop():
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop.run_forever, daemon=True)
    add_script_run_ctx(t)
    t.start()
    return loop


def run_async(coro):
    loop = get_async_loop()
    return asyncio.run_coroutine_threadsafe(coro, loop).result()


# ---------- 1. 认证 ----------
authenticator = stauth.Authenticate(
    {
        "usernames": {
            "admin": {
                "email": "admin@yourdomain.com",
                "name": "Administrator",
                "password": settings.admin_password_hash,
            }
        }
    },
    settings.cookie_name,
    settings.cookie_key,
    30,
)

name, auth_status, _ = authenticator.login(location="main")
if auth_status is False:
    st.error("用户名或密码错误")
    st.stop()
elif auth_status is None:
    st.warning("请输入用户名和密码")
    st.stop()

# ---------- 2. 主界面 ----------
st.sidebar.title(f"欢迎, {name}!")
authenticator.logout("退出", "sidebar")

# 2-1 连接数据库
if "db_ok" not in st.session_state:
    try:
        run_async(init_db())
        st.session_state["db_ok"] = True
        st.sidebar.success("✅ 数据库已连接")
    except Exception as e:
        st.error(f"数据库初始化失败: {e}")
        st.stop()

st.header("✨ 邀请码管理")

# 2-2 生成邀请码
if st.button("生成新邀请码", type="primary"):
    with st.spinner("生成中…"):
        invite: InvitationCode = run_async(create_invite())
        st.success(f"已生成邀请码: {invite.code}")
        st.rerun()  # 立即刷新列表

# 2-3 显示邀请码列表（含删除按钮）
st.subheader("📚 邀请码列表")
invites = run_async(list_invites())
if invites:
    for inv in invites:
        col_code, col_status, col_user, col_ctime, col_utime, col_btn = st.columns(
            [2, 1.2, 3, 2.2, 2.2, 1]
        )

        col_code.markdown(f"**{inv.code}**")
        col_status.write("✅ 已用" if inv.status == "used" else "🆕 未用")
        col_user.write(inv.activated_by_sys_uuid or "—")
        col_ctime.write(inv.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        col_utime.write(
            inv.used_at.strftime("%Y-%m-%d %H:%M:%S") if inv.used_at else "—"
        )

        if col_btn.button(
                "删除",
                key=f"del_{inv.code}",
                help="删除邀请码并清理绑定用户",
        ):
            run_async(delete_invite(inv.code))
            st.success(f"已删除 {inv.code}")
            st.rerun()  # 刷新页面
else:
    st.info("暂无邀请码")

# 2-4 已激活用户
st.header("👥 已激活用户")
users = run_async(AuthorizedUser.find_all().to_list())
if users:
    df_u = pd.DataFrame([u.model_dump() for u in users])
    df_u["activated_at"] = (
        pd.to_datetime(df_u["activated_at"], errors="coerce")
        .dt.strftime("%Y-%m-%d %H:%M:%S")
        .fillna("")
    )
    st.dataframe(
        df_u[["sys_uuid", "activated_via_code", "activated_at"]],
        use_container_width=True,
    )
else:
    st.info("暂无激活用户")
