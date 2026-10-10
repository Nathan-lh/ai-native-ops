# -*- coding: utf-8 -*-
"""并发测试 Redisson 分布式锁：10 个线程同时请求，只有 1 个能拿到锁"""
import requests
from concurrent.futures import ThreadPoolExecutor

URL = "http://localhost:8080/api/test/lock"


def hit(i):
    r = requests.get(URL, timeout=15)
    return r.json()


def main():
    print("=" * 60)
    print("并发测试：10 个线程同时请求 /api/test/lock")
    print("=" * 60)

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(hit, range(10)))

    success = sum(1 for r in results if r.get("success"))
    failed = sum(1 for r in results if not r.get("success"))
    print(f"\n成功获取锁: {success}")
    print(f"未获取锁:   {failed}")
    print()
    for i, r in enumerate(results, 1):
        print(f"  线程{i}: success={r.get('success')}  msg={r.get('message')}")

    print("\n" + "=" * 60)
    if success == 1:
        print("✅ 分布式锁生效：10 并发只有 1 个成功")
    else:
        print(f"⚠️ 预期成功 1 个，实际 {success} 个")


if __name__ == "__main__":
    main()