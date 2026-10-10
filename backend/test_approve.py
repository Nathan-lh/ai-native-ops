# -*- coding: utf-8 -*-
"""审核通过：把 id=1 的候选改成 APPROVED"""
import requests

BASE = "http://localhost:8080"


def login(username, password):
    r = requests.post(f"{BASE}/api/auth/login", json={"username": username, "password": password})
    r.raise_for_status()
    data = r.json()
    for key in ("token", "accessToken", "access_token", "jwt"):
        if key in data:
            return data[key]
    raise Exception(f"未找到 token 字段：{data}")


def main():
    admin_token = login("admin", "123456")
    h = {"Authorization": f"Bearer {admin_token}"}

    # 查一下当前 PENDING
    print("[1] 查询 PENDING 候选")
    r = requests.get(f"{BASE}/api/knowledge/candidates", headers=h, params={"status": "PENDING"})
    r.raise_for_status()
    data = r.json()
    print(f"    total = {data['total']}")
    for c in data["list"]:
        print(f"    - id={c['id']}  order_id={c['orderId']}")

    if data["total"] == 0:
        print("没有 PENDING 候选，无需审核。")
        return

    # 审核通过第一条
    target_id = data["list"][0]["id"]
    print(f"\n[2] 审核通过 id={target_id}")
    r = requests.post(
        f"{BASE}/api/knowledge/candidates/{target_id}/approve",
        headers=h,
        json={"comment": "证据充分，同意入库"},
    )
    print(f"    状态码: {r.status_code}  响应: {r.text}")

    # 再查一次 APPROVED
    print("\n[3] 查询 APPROVED 候选")
    r = requests.get(f"{BASE}/api/knowledge/candidates/approved")
    r.raise_for_status()
    approved = r.json()
    print(f"    共 {len(approved)} 条 APPROVED")
    for c in approved:
        print(f"    - id={c['id']}  order_id={c['orderId']}  device_type={c.get('deviceType')}")


if __name__ == "__main__":
    main()