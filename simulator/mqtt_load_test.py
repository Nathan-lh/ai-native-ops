# -*- coding: utf-8 -*-
"""
MQTT 遥测压测脚本（对照方案文档 8.1「高并发 MQTT 接入（真做）」）

作用：向 EMQX 的 telemetry/# 主题高并发发布遥测消息，测「发布吞吐 / 后端入库吞吐 / 背压丢弃」。

用法（在 simulator 目录下、用本项目的 .venv 运行）：
  # 洪峰压测：不限速狂发，打满后端 10000 有界队列，触发背压丢弃
  .venv\\Scripts\\python mqtt_load_test.py --total 30000 --rate 0 --threads 8

  # 温和压测：限速稳发，后端能跟上、不丢，测稳态入库 TPS
  .venv\\Scripts\\python mqtt_load_test.py --total 10000 --rate 1000

说明：
  - 脚本只负责「发消息 + 计时」，入库条数用 docker exec 查 MySQL 前后对比得到。
  - payload 与 device_simulator.py 完全一致，保证后端能正确解析、不触发额外动态注册。
"""
import argparse
import json
import random
import threading
import time
from datetime import datetime

import paho.mqtt.client as mqtt

# ================= 配置区 =================
BROKER = "localhost"
PORT = 1883
TOPIC_PREFIX = "telemetry/"
DEVICE_TYPES = ["空调", "电机", "配电柜", "温湿度传感器"]

# 复用模拟器的 50 台设备编码（避免压测时大量动态注册新设备）
DEVICE_CODES = []
for _i in range(1, 51):
    _t = DEVICE_TYPES[(_i - 1) % 4]
    DEVICE_CODES.append(f"DEV-{_t}-{_i:03d}")
# =========================================

published = 0          # 已发布总条数（多线程共享）
pub_lock = threading.Lock()


def make_payload(device_code):
    """生成与设备模拟器格式一致的遥测 payload（正常范围内随机，健康评估大多判 NORMAL）"""
    device_type = None
    for t in DEVICE_TYPES:
        if t in device_code:
            device_type = t
            break
    if device_type is None:
        device_type = "空调"

    return {
        "device_code": device_code,
        "device_type": device_type,
        "temperature": round(random.uniform(25.0, 30.0), 2),
        "humidity": round(random.uniform(40.0, 60.0), 2),
        "current": round(random.uniform(5.0, 10.0), 2),
        "voltage": round(random.uniform(220.0, 230.0), 2),
        "vibration": round(random.uniform(1.0, 3.0), 2),
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def publish_worker(client, device_code, count):
    """单个发布线程：连续发 count 条（不限速模式）"""
    global published
    for _ in range(count):
        payload = make_payload(device_code)
        topic = f"{TOPIC_PREFIX}{device_code}"
        # QoS 0：fire-and-forget，最快
        client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=0)
        with pub_lock:
            published += 1


def publish_limited(client, total, rate):
    """限速模式：单线程按固定速率发 total 条"""
    global published
    interval = 1.0 / rate
    for i in range(total):
        device_code = DEVICE_CODES[i % len(DEVICE_CODES)]
        payload = make_payload(device_code)
        topic = f"{TOPIC_PREFIX}{device_code}"
        client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=0)
        published += 1
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="MQTT 遥测压测")
    parser.add_argument("--total", type=int, default=20000, help="总消息条数")
    parser.add_argument("--rate", type=int, default=0, help="目标 msg/s，0 表示不限速")
    parser.add_argument("--threads", type=int, default=8, help="不限速模式下的发布线程数")
    args = parser.parse_args()

    client = mqtt.Client()
    client.connect(BROKER, PORT, 60)
    client.loop_start()
    time.sleep(0.5)  # 等连接稳定

    total = args.total
    print("=" * 60)
    print(f"[压测开始] 总条数={total}  模式={'不限速' if args.rate == 0 else f'限速 {args.rate} msg/s'}")
    print("=" * 60)

    start = time.time()

    if args.rate > 0:
        # 温和模式：单线程限速
        publish_limited(client, total, args.rate)
    else:
        # 洪峰模式：多线程不限速
        threads = []
        per_thread = total // args.threads
        for t in range(args.threads):
            code = DEVICE_CODES[t % len(DEVICE_CODES)]
            th = threading.Thread(target=publish_worker, args=(client, code, per_thread))
            threads.append(th)
            th.start()
        for th in threads:
            th.join()

    elapsed = time.time() - start
    throughput = published / elapsed if elapsed > 0 else 0

    print("-" * 60)
    print(f"[压测完成] 已发布 {published} 条")
    print(f"[发布吞吐] {throughput:,.0f} msg/s")
    print(f"[发布耗时] {elapsed:.2f} 秒")
    print("-" * 60)
    print("下一步：用下面命令查 MySQL 前后对比，得到「入库 TPS / 背压丢弃条数」：")
    print('  docker exec mysql mysql -uroot -proot123456 ai_ops -e "SELECT COUNT(*) AS cnt FROM telemetry"')
    print("  （压测前先记一次 count，压测后等后端消费完再记一次）")

    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
