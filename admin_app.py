# ==== admin_app.py ====
import streamlit as st
st.set_page_config(page_title="Coze Agent 后台管理", layout="wide")

import asyncio, threading, math
import pandas as pd
import streamlit_authenticator as stauth
from streamlit.runtime.scriptrunner import add_script_run_ctx

from app.config import settings
from app.database import init_db
from app.services.invitation_service import (
    create_invite, list_invites, delete_invite
)
from app.models.user import AuthorizedUser


# ---------- 0. 统一事件循环 ----------
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


# ---------- 1. 登录 ----------
authenticator = stauth.Authenticate(
    {"usernames": {
        "admin": {
            "email": "admin@yourdomain.com",
            "name": "Administrator",
            "password": settings.admin_password_hash,
        }
    }},
    settings.cookie_name,
    settings.cookie_key,
    30,
)
name, auth_status, _ = authenticator.login(location="main")
if auth_status is False:
    st.error("用户名或密码错误"); st.stop()
elif auth_status is None:
    st.warning("请输入用户名和密码"); st.stop()

# ---------- 2. 主界面 ----------
st.sidebar.title(f"欢迎, {name}!")
authenticator.logout("退出", "sidebar")

# 2-1 连接 Mongo
if "db_ok" not in st.session_state:
    run_async(init_db()); st.session_state["db_ok"] = True
    st.sidebar.success("✅ 数据库已连接")

st.header("✨ 邀请码管理")

# 2-2 生成邀请码
if st.button("生成新邀请码", type="primary"):
    code = run_async(create_invite()).code
    st.success(f"已生成邀请码: {code}")
    st.rerun()

# ============ 表格 + 分页 ============
PAGE_SIZE = 20

df_inv = pd.DataFrame([i.model_dump() for i in run_async(list_invites())])
if df_inv.empty:
    st.info("暂无邀请码")
else:
    # 时间格式化
    for col in ("created_at", "used_at"):
        df_inv[col] = (
            pd.to_datetime(df_inv[col], errors="coerce")
            .dt.strftime("%Y-%m-%d %H:%M:%S")
            .fillna("")
        )
    # 分页
    total_pages = math.ceil(len(df_inv) / PAGE_SIZE)
    page = st.number_input("页码", 1, max(1, total_pages), 1, key="inv_page")
    start, end = (page - 1) * PAGE_SIZE, page * PAGE_SIZE
    df_page = df_inv.iloc[start:end]

    st.dataframe(
        df_page[["code", "status", "activated_by_sys_uuid", "created_at", "used_at"]],
        use_container_width=True,
    )

    # 选择 + 删除
    del_codes = st.multiselect(
        "勾选需要删除的邀请码（只显示当前页）",
        options=df_page["code"].tolist(),
        key="del_codes",
    )
    if st.button("删除选中邀请码"):
        if del_codes:
            for c in del_codes:
                run_async(delete_invite(c))
            st.success(f"已删除 {len(del_codes)} 条邀请码")
            st.rerun()
        else:
            st.warning("请先选择要删除的条目")

# ============ 已激活用户 ============
st.header("👥 已激活用户")
df_user = pd.DataFrame([u.model_dump() for u in run_async(AuthorizedUser.find_all().to_list())])
if df_user.empty:
    st.info("暂无激活用户")
else:
    df_user["activated_at"] = (
        pd.to_datetime(df_user["activated_at"], errors="coerce")
        .dt.strftime("%Y-%m-%d %H:%M:%S")
        .fillna("")
    )
    # 分页
    total_pages_u = math.ceil(len(df_user) / PAGE_SIZE)
    page_u = st.number_input("用户表页码", 1, max(1, total_pages_u), 1, key="user_page")
    start_u, end_u = (page_u - 1) * PAGE_SIZE, page_u * PAGE_SIZE
    st.dataframe(
        df_user.iloc[start_u:end_u][["sys_uuid", "activated_via_code", "activated_at"]],
        use_container_width=True,
    )
