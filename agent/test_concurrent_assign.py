# -*- coding: utf-8 -*-
"""
Redisson 分布式锁验证：并发派单同一个工单
预期：50 并发只有 1 个成功派单，49 个被拒
"""
import requests
from concurrent.futures import ThreadPoolExecutor

BASE = "http://localhost:8080"


def login(username, password):
    r = requests.post(f"{BASE}/api/auth/login", json={"username": username, "password": password})
    r.raise_for_status()
    data = r.json()
    for key in ("token", "accessToken", "access_token", "jwt"):
        if key in data:
            return data[key]
    raise Exception(f"未找到 token: {data}")


def main():
    print("=" * 70)
    print("Redisson 分布式锁 · 工单派单并发测试")
    print("=" * 70)

    # 1. 登录
    admin_token = login("admin", "123456")
    h = {"Authorization": f"Bearer {admin_token}"}
    print("[1] admin 登录成功")

    # 2. 创建一个新的 PENDING_REVIEW 工单
    print("\n[2] 创建新工单")
    r = requests.post(f"{BASE}/api/orders", headers=h, json={
        "deviceId": 1,
        "description": "并发测试工单，验证分布式锁",
    })
    r.raise_for_status()
    order_id = r.json()["id"]
    print(f"    工单 id={order_id}，状态=PENDING_REVIEW")

    # 3. 并发 50 个线程同时派单
    print(f"\n[3] 50 个线程同时派单 order_id={order_id}")
    assign_url = f"{BASE}/api/orders/{order_id}/assign"

    def do_assign(i):
        try:
            r = requests.post(assign_url, headers=h, json={
                "repairerId": 5,
                "reviewComment": f"线程{i}的派单请求",
            }, timeout=15)
            return r.status_code, r.text[:120]
        except Exception as e:
            return -1, str(e)[:120]

    with ThreadPoolExecutor(max_workers=50) as pool:
        results = list(pool.map(do_assign, range(50)))

    # 4. 统计
    success = sum(1 for code, _ in results if code == 200)
    failed = len(results) - success
    print(f"\n    成功: {success}")
    print(f"    失败: {failed}")

    # 5. 最终工单状态
    r = requests.get(f"{BASE}/api/orders/{order_id}", headers=h)
    order = r.json()
    print(f"\n[4] 最终工单状态: {order.get('status')}")
    print(f"    reviewer_id={order.get('reviewerId')}")
    print(f"    repairer_id={order.get('repairerId')}")
    print(f"    review_comment={order.get('reviewComment')}")

    print("\n" + "=" * 70)
    if success == 1:
        print("✅ 分布式锁生效：50 并发只有 1 个成功派单")
    else:
        print(f"❌ 预期成功 1 个，实际成功 {success} 个")
    print("=" * 70)


if __name__ == "__main__":
    main()