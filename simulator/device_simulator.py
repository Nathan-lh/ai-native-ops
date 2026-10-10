# -*- coding: utf-8 -*-
import json
import time
import random
import threading
import paho.mqtt.client as mqtt
from datetime import datetime

# ================= 配置区 =================
BROKER = 'localhost'
PORT = 1883
TOPIC_PREFIX = 'telemetry/'
DEVICE_COUNT = 50
REPORT_INTERVAL = 5  # 秒
# =========================================

DEVICE_TYPES = ['空调', '电机', '配电柜', '温湿度传感器']
FAULT_TYPES = ['散热故障', '电压不稳', '过载', '机械磨损', '湿度过高']

# 设备状态字典（保存每台设备的基准值和当前故障状态）
devices = {}


def init_devices():
    """初始化设备列表"""
    for i in range(1, DEVICE_COUNT + 1):
        dev_type = random.choice(DEVICE_TYPES)
        dev_code = f"DEV-{dev_type}-{i:03d}"
        devices[dev_code] = {
            "device_type": dev_type,
            "base_temp": random.uniform(25.0, 30.0),
            "base_hum": random.uniform(40.0, 60.0),
            "base_current": random.uniform(5.0, 10.0),
            "base_voltage": random.uniform(220.0, 230.0),
            "base_vibration": random.uniform(1.0, 3.0),
            "fault": None,  # 无故障
            "fault_step": 0
        }


def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] 连接结果: {rc} (0 表示成功)")


def generate_telemetry(dev_code, dev_info):
    """根据设备状态生成遥测数据（带故障注入）"""
    # 基础值 + 随机噪声
    temp = dev_info["base_temp"] + random.uniform(-1.0, 1.0)
    hum = dev_info["base_hum"] + random.uniform(-2.0, 2.0)
    cur = dev_info["base_current"] + random.uniform(-0.5, 0.5)
    vol = dev_info["base_voltage"] + random.uniform(-2.0, 2.0)
    vib = dev_info["base_vibration"] + random.uniform(-0.2, 0.2)

    # 故障剧本注入
    fault = dev_info["fault"]
    if fault:
        dev_info["fault_step"] += 1
        step = dev_info["fault_step"]
        if fault == '散热故障':
            temp = dev_info["base_temp"] + (step * 2.0)  # 温度线性爬升
        elif fault == '电压不稳':
            vol = dev_info["base_voltage"] + (15.0 * random.choice([-1, 1]))  # 电压抖动
        elif fault == '过载':
            cur = dev_info["base_current"] + 20.0  # 电流突增
        elif fault == '机械磨损':
            vib = dev_info["base_vibration"] + (step * 1.5)  # 振动增大
        elif fault == '湿度过高':
            hum = dev_info["base_hum"] + 30.0  # 湿度超标

    return {
        "device_code": dev_code,
        "device_type": dev_info["device_type"],
        "temperature": round(temp, 2),
        "humidity": round(hum, 2),
        "current": round(cur, 2),
        "voltage": round(vol, 2),
        "vibration": round(vib, 2),
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def inject_fault_thread():
    """自动故障注入线程（每 30 秒随机挑一台设备注入故障）"""
    while True:
        time.sleep(30)
        dev_code = random.choice(list(devices.keys()))
        fault = random.choice(FAULT_TYPES)
        devices[dev_code]["fault"] = fault
        devices[dev_code]["fault_step"] = 0
        print(f"\n[故障注入] 设备 {dev_code} 触发 -> {fault}\n")


def main():
    init_devices()
    client = mqtt.Client()
    client.on_connect = on_connect
    client.connect(BROKER, PORT, 60)

    # 开启自动故障注入线程
    t = threading.Thread(target=inject_fault_thread, daemon=True)
    t.start()

    client.loop_start()

    print(f"[启动] {DEVICE_COUNT} 台设备模拟器已启动，每 {REPORT_INTERVAL} 秒上报一次...")
    print("按 Ctrl+C 停止。\n")

    try:
        while True:
            for dev_code, dev_info in devices.items():
                payload = generate_telemetry(dev_code, dev_info)
                topic = f"{TOPIC_PREFIX}{dev_code}"
                client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=0)

            # 每轮打印一条样例数据，防止屏幕刷屏
            sample_dev = list(devices.keys())[0]
            sample_payload = generate_telemetry(sample_dev, devices[sample_dev])
            print(f"[上报] {json.dumps(sample_payload, ensure_ascii=False)}")

            time.sleep(REPORT_INTERVAL)
    except KeyboardInterrupt:
        print("\n[停止] 模拟器已手动停止。")
        client.loop_stop()


if __name__ == '__main__':
    main()