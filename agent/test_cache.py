# -*- coding: utf-8 -*-
"""验证 Cache-Aside：首次未命中回源，第二次命中"""
import requests

URL = "http://localhost:8080/api/device/cache/1"


def main():
    print("=" * 60)
    print("Cache-Aside 验证：GET " + URL)
    print("=" * 60)

    for i in range(1, 4):
        r = requests.get(URL)
        print(f"\n[调用 {i}]")
        print(f"  状态码: {r.status_code}")
        print(f"  响应: {r.text[:200]}")


if __name__ == "__main__":
    main()