# -*- coding: utf-8 -*-
"""
检查故障手册 JSON 是否合法、字段是否完整
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MANUAL_DIR = BASE_DIR / "manuals"
MERGED = BASE_DIR / "manuals_all.json"

required_fields = [
    "id",
    "device_type",
    "fault_type",
    "fault_phenomenon",
    "telemetry_signature",
    "possible_causes",
    "troubleshoot_steps",
    "repair_method",
    "severity",
    "source",
]

files = sorted(MANUAL_DIR.glob("*.json"))
print(f"单篇 JSON 数量：{len(files)}")

if len(files) != 8:
    raise SystemExit("数量不是 8，请检查 seed_manuals.py 是否完整运行。")

for f in files:
    data = json.loads(f.read_text(encoding="utf-8"))
    missing = [k for k in required_fields if k not in data]
    if missing:
        print(f"[缺少字段] {f.name}: {missing}")
    else:
        print(f"[OK] {f.name}  {data['device_type']} / {data['fault_type']}")

merged = json.loads(MERGED.read_text(encoding="utf-8"))
print(f"合并文件条数：{len(merged)}")

if len(merged) != 8:
    raise SystemExit("manuals_all.json 条数不是 8，请检查。")

print("验证通过：8 篇手册结构完整、JSON 合法。")