# -*- coding: utf-8 -*-
"""
知识回流 · 端到端测试
创建工单 → 派单 → 接单 → 完成 → 验证 → 查候选
"""
import requests
import json

BASE = "http://localhost:8080"


def get_token(resp_json):
    """兼容不同字段名的 token 提取"""
    for key in ("token", "accessToken", "access_token", "jwt"):
        if key in resp_json:
            return resp_json[key]
    raise Exception(f"未找到 token 字段，响应：{resp_json}")


def login(username, password):
    r = requests.post(f"{BASE}/api/auth/login", json={"username": username, "password": password})
    r.raise_for_status()
    data = r.json()
    return get_token(data), data


def main():
    print("=" * 70)
    print("知识回流 · 端到端测试")
    print("=" * 70)

    # 1. 登录 admin 和 repairer
    print("\n[1] 登录 admin / repairer")
    admin_token, admin_data = login("admin", "123456")
    admin_h = {"Authorization": f"Bearer {admin_token}"}
    print(f"    admin 登录成功: {admin_data}")

    repairer_token, repairer_data = login("repairer", "123456")
    repairer_h = {"Authorization": f"Bearer {repairer_token}"}
    print(f"    repairer 登录成功: {repairer_data}")

    # 2. 创建工单
    print("\n[2] 创建工单（deviceId=1）")
    r = requests.post(f"{BASE}/api/orders", headers=admin_h, json={
        "deviceId": 1,
        "description": "DEV-空调-001 温度持续升高，疑似散热故障",
        "aiDiagnosisSummary": "Agent 诊断：结合知识库手册，疑似散热故障"
    })
    print(f"    状态码: {r.status_code}  响应: {r.text[:200]}")
    r.raise_for_status()
    order_id = r.json()["id"]
    print(f"    ✅ 工单 id={order_id}")

    # 3. 派单
    print(f"\n[3] 派单给 repairer (id=5)")
    r = requests.post(f"{BASE}/api/orders/{order_id}/assign", headers=admin_h, json={
        "repairerId": 5,
        "reviewComment": "同意派单"
    })
    print(f"    状态码: {r.status_code}  响应: {r.text[:200]}")
    r.raise_for_status()
    print("    ✅ 派单成功")

    # 4. 接单
    print(f"\n[4] repairer 接单")
    r = requests.post(f"{BASE}/api/orders/{order_id}/start", headers=repairer_h)
    print(f"    状态码: {r.status_code}  响应: {r.text[:200]}")
    r.raise_for_status()
    print("    ✅ 接单成功")

    # 5. 完成维修
    print(f"\n[5] 维修完成（VERIFYING）")
    r = requests.post(f"{BASE}/api/orders/{order_id}/complete", headers=repairer_h, json={
        "repairComment": "清洗冷凝器，更换风扇",
        "repairReason": "冷凝器积尘严重导致散热不良"
    })
    print(f"    状态码: {r.status_code}  响应: {r.text[:200]}")
    r.raise_for_status()
    print("    ✅ 维修完成，进入待验证")

    # 6. 验证通过（COMPLETED → 触发知识回流）
    print(f"\n[6] 管理员验证通过（应该触发知识回流）")
    r = requests.post(f"{BASE}/api/orders/{order_id}/verify", headers=admin_h)
    print(f"    状态码: {r.status_code}  响应: {r.text[:200]}")
    r.raise_for_status()
    print("    ✅ 验证通过，工单完成")

    # 7. 查询候选列表
    print(f"\n[7] 查询 knowledge_candidate（PENDING）")
    r = requests.get(f"{BASE}/api/knowledge/candidates", headers=admin_h, params={"status": "PENDING"})
    print(f"    状态码: {r.status_code}")
    r.raise_for_status()
    data = r.json()
    print(f"    total = {data.get('total')}")
    for c in data.get("list", []):
        print(f"    - id={c['id']}  order_id={c['orderId']}  device_type={c.get('deviceType')}")
        print(f"      status={c.get('status')}  来源={c.get('source')}")
        print(f"      fault_phenomenon={c.get('faultPhenomenon')}")
        print(f"      repair_method={c.get('repairMethod')}")
        print(f"      repair_reason={c.get('repairReason')}")

    print("\n" + "=" * 70)
    print(f"测试完成！本次工单 id = {order_id}")
    print("=" * 70)


if __name__ == "__main__":
    main()