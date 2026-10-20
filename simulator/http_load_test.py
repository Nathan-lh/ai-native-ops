# -*- coding: utf-8 -*-
"""
HTTP 接口 QPS 压测脚本
作用：并发请求指定 URL，测 QPS 与延迟分位数（P50/P90/P99），用于接口性能压测。

用法（在 simulator 目录下、用 .venv 运行）：
  .venv\\Scripts\\python http_load_test.py --url http://localhost:8080/api/health --total 10000 --concurrency 50

说明：
  - 只用 Python 标准库 urllib，无需额外依赖。
  - 输出：成功/失败数、总耗时、QPS、P50/P90/P99 延迟。
"""
import argparse
import time
import urllib.request
import concurrent.futures
import threading


def main():
    parser = argparse.ArgumentParser(description="HTTP QPS 压测")
    parser.add_argument("--url", required=True, help="目标 URL")
    parser.add_argument("--total", type=int, default=10000, help="总请求数")
    parser.add_argument("--concurrency", type=int, default=50, help="并发线程数")
    args = parser.parse_args()

    latencies = []          # 每个成功请求的耗时（毫秒）
    errors = []             # 失败信息
    lock = threading.Lock()

    def request_one(_):
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(args.url, timeout=10) as resp:
                resp.read()
            ms = (time.perf_counter() - start) * 1000.0
            with lock:
                latencies.append(ms)
        except Exception as e:
            with lock:
                errors.append(str(e))

    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        list(pool.map(request_one, range(args.total)))
    elapsed = time.perf_counter() - t0

    ok = len(latencies)
    fail = len(errors)
    latencies.sort()

    def pct(p):
        if not latencies:
            return 0.0
        idx = min(int(p / 100.0 * len(latencies)), len(latencies) - 1)
        return latencies[idx]

    print("=" * 60)
    print(f"[目标] {args.url}")
    print(f"[并发] {args.concurrency} 线程")
    print(f"[结果] 总请求={args.total}  成功={ok}  失败={fail}")
    print(f"[耗时] {elapsed:.2f} 秒")
    print(f"[QPS ] {args.total / elapsed:,.0f} req/s")
    print(f"[延迟] P50={pct(50):.1f}ms  P90={pct(90):.1f}ms  P99={pct(99):.1f}ms  Max={latencies[-1] if latencies else 0:.1f}ms")
    print("=" * 60)


if __name__ == "__main__":
    main()
