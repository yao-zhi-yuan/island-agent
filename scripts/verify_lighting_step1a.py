from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from uuid import uuid4

import httpx
import jwt

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.lighting.store import close_lighting_store, get_lighting_store, init_lighting_store
from app.main import app


# 这个脚本是 Step 1A 的真实数据库验证脚本。
# 它不新增业务能力，只通过 API 跑一遍“创建 -> 更新状态 -> 查询 -> 跨用户隔离”的闭环。
def _auth_headers(user_id: str) -> dict[str, str]:
    # 通过 JWT 切换 user_id，用来验证 owner 和 outsider 两个用户的数据隔离。
    secret = os.getenv("JWT_SECRET")
    if not secret:
        os.environ.setdefault("JWT_VERIFY", "0")
        secret = "step1a-verification-secret-at-least-32-bytes"
    token = jwt.encode({"user_id": user_id}, key=secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


async def main() -> None:
    if not (os.getenv("LIGHTING_POSTGRES_DSN") or os.getenv("POSTGRES_DSN")):
        # 真实闭环必须连到 Postgres；没有 DSN 时直接失败，避免误以为测试通过。
        raise SystemExit("LIGHTING_POSTGRES_DSN or POSTGRES_DSN is required for real DB verification.")

    project_id: str | None = None
    owner: str | None = None

    await init_lighting_store()
    try:
        # ASGITransport 直接调用 FastAPI app，不需要启动 uvicorn，但仍然走真实 API 路由。
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            owner = f"lighting-owner-{uuid4().hex[:8]}"
            outsider = f"lighting-outsider-{uuid4().hex[:8]}"

            create_resp = await client.post(
                "/api/lighting/projects",
                headers=_auth_headers(owner),
                json={
                    "session_id": "step1a-session",
                    "title": "Step 1A 验证项目",
                    "initial_requirement": "设计一个温馨卧室",
                },
            )
            assert create_resp.status_code == 200, create_resp.text
            created = create_resp.json()
            project_id = created["id"]
            assert created["user_id"] == owner
            assert created["project_state"]["stage"] == "requirement"
            assert created["project_state"]["requirement_spec"]["initial_requirement"] == "设计一个温馨卧室"

            expected_state = {
                "stage": "geometry",
                "requirement_spec": {"space_type": "bedroom", "style": "warm"},
                "geometry_spec": {"width": 4, "length": 3},
                "design_strategy": {},
                "fixture_selection": {},
                "layout_plan": {},
                "quality_report": {},
                "delivery_package": {},
            }
            patch_resp = await client.patch(
                f"/api/lighting/projects/{project_id}/state",
                headers=_auth_headers(owner),
                json={"project_state": expected_state},
            )
            assert patch_resp.status_code == 200, patch_resp.text

            # 读回后和 expected_state 做严格相等比较，验证 ProjectState 是完整持久化的。
            get_resp = await client.get(
                f"/api/lighting/projects/{project_id}",
                headers=_auth_headers(owner),
            )
            assert get_resp.status_code == 200, get_resp.text
            fetched = get_resp.json()
            assert fetched["id"] == project_id
            assert fetched["project_state"] == expected_state

            # 使用另一个 user_id 访问同一 project_id，应该返回 404，证明 user_id 隔离生效。
            outsider_resp = await client.get(
                f"/api/lighting/projects/{project_id}",
                headers=_auth_headers(outsider),
            )
            assert outsider_resp.status_code == 404, outsider_resp.text

            print("lighting Step 1A verification passed")
            print(f"project_id={project_id}")
            print(f"owner_user_id={owner}")
            print("outsider_get_status=404")
    finally:
        if project_id and owner:
            # 验证脚本清理自己创建的测试数据，避免污染真实数据库。
            await get_lighting_store().pool.execute(
                "DELETE FROM lighting_projects WHERE id=$1 AND user_id=$2",
                project_id,
                owner,
            )
        await close_lighting_store()


if __name__ == "__main__":
    asyncio.run(main())
