# -*- coding: utf-8 -*-
"""
缓存一致性完整验证（带 token 版本，避免放行规则坑）
"""
import requests
import time

BASE = "http://localhost:8080"


def login(username, password):
    r = requests.post(f"{BASE}/api/auth/login", json={"username": username, "password": password})
    r.raise_for_status()
    data = r.json()
    for key in ("token", "accessToken", "access_token", "jwt"):
        if key in data:
            return data[key]
    raise Exception(f"未找到 token: {data}")


def read_cache(device_id, headers):
    r = requests.get(f"{BASE}/api/device/cache/{device_id}", headers=headers)
    return r.json()


def write_cache(device_id, status, headers):
    r = requests.post(f"{BASE}/api/device/cache/{device_id}/test-write",
                      json={"status": status}, headers=headers)
    return r.json()


def main():
    device_id = 1
    print("=" * 70)
    print("缓存一致性完整验证（先更 DB + 删缓存 + 延迟双删）")
    print("=" * 70)

    # 登录拿 token
    token = login("admin", "123456")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[0] 登录成功，token 长度 {len(token)}")

    # 阶段 1
    print("\n[阶段 1] 首次读 → 回源 MySQL，把当前值写入缓存")
    r1 = read_cache(device_id, headers)
    old_status = r1.get("status")
    print(f"  当前缓存值: status={old_status}, deviceId 类型={type(r1.get('deviceId')).__name__}")

    # 阶段 2
    new_status = "FAULT" if old_status != "FAULT" else "NORMAL"
    print(f"\n[阶段 2] 写入新值：{old_status} → {new_status}")
    wr = write_cache(device_id, new_status, headers)
    print(f"  写入响应: {wr}")

    if "newStatus" not in wr:
        print("\n❌ 写入失败，请检查后端日志")
        return

    # 阶段 3
    print("\n[阶段 3] 立即读 → 缓存已被删，回源 MySQL")
    r2 = read_cache(device_id, headers)
    print(f"  status={r2.get('status')}（期望 {new_status}）")
    match3 = r2.get("status") == new_status

    # 阶段 4
    print("\n[阶段 4] 等 600ms 后再读 → 延迟双删已执行，缓存应仍是新值")
    time.sleep(0.6)
    r3 = read_cache(device_id, headers)
    print(f"  status={r3.get('status')}（期望 {new_status}）")
    match4 = r3.get("status") == new_status

    print("\n" + "=" * 70)
    if match3 and match4:
        print("✅ 缓存一致性通过：写入后立即读、延迟后读，都拿到新值")
    else:
        print("❌ 缓存一致性失败")
        print(f"   立即读 match={match3}, 延迟后读 match={match4}")
    print("=" * 70)


if __name__ == "__main__":
    main()