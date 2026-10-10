# -*- coding: utf-8 -*-
"""
知识回流：Java 端 APPROVED 候选 → 本地知识库 JSON
运行后需手动执行 knowledge_base.py 重建向量库。
"""

import json
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
MANUAL_DIR = KNOWLEDGE_DIR / "manuals"
MERGED_PATH = KNOWLEDGE_DIR / "manuals_all.json"

JAVA_BACKEND = "http://localhost:8080"


def fetch_approved():
    """从 Java 后端拉取所有 APPROVED 候选"""
    url = f"{JAVA_BACKEND}/api/knowledge/candidates/approved"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


def candidate_to_manual(c: dict) -> dict:
    """把 Java 候选对象转成本地手册 JSON 结构"""
    manual = {
        "id": f"reflow_{c['id']}",
        "device_type": c.get("deviceType") or "通用",
        "fault_type": c.get("faultType") or "未分类",
        "fault_phenomenon": c.get("faultPhenomenon") or "",
        "telemetry_signature": c.get("telemetrySignature") or "",
        "possible_causes": _split_json_array(c.get("possibleCauses")),
        "troubleshoot_steps": _split_json_array(c.get("troubleshootSteps")),
        "repair_method": c.get("repairMethod") or "",
        "severity": c.get("severity") or "中",
        "source": f"工单回流 order_id={c.get('orderId')}",
        "_repair_reason": c.get("repairReason") or "",
        "_order_id": c.get("orderId"),
    }
    return manual


def _split_json_array(s):
    """如果字段是 JSON 数组字符串，尝试解析；否则按分号切分"""
    if not s:
        return []
    try:
        v = json.loads(s)
        if isinstance(v, list):
            return v
    except Exception:
        pass
    return [x.strip() for x in s.split("；") if x.strip()]


def main():
    print("=" * 70)
    print("知识回流：拉取 APPROVED 候选 → 写入本地知识库")
    print("=" * 70)

    print(f"\n[1] 调用 Java 后端: {JAVA_BACKEND}/api/knowledge/candidates/approved")
    try:
        approved = fetch_approved()
    except Exception as e:
        print(f"    ❌ 调用失败：{e}")
        print("    请确认后端正在运行 (http://localhost:8080)")
        return

    print(f"    获取到 {len(approved)} 条 APPROVED 候选")
    if not approved:
        print("    无新增候选，直接退出。")
        return

    print(f"\n[2] 写入 {MANUAL_DIR}")
    written = []
    for c in approved:
        manual = candidate_to_manual(c)
        file_path = MANUAL_DIR / f"{manual['id']}.json"
        file_path.write_text(
            json.dumps(manual, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        written.append(manual)
        print(f"    ✅ {file_path.name}  ({manual['device_type']} / {manual['fault_type']})")

    print(f"\n[3] 更新合并文件：{MERGED_PATH}")
    existing = []
    if MERGED_PATH.exists():
        existing = json.loads(MERGED_PATH.read_text(encoding="utf-8"))

    reflow_ids = {m["id"] for m in written}
    existing = [m for m in existing if m["id"] not in reflow_ids]

    merged = existing + written
    MERGED_PATH.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"    合并后共 {len(merged)} 篇手册（原 {len(existing)} + 新 {len(written)}）")

    print("\n" + "=" * 70)
    print("回流完成！下一步请执行：")
    print("    python knowledge_base.py    # 重建向量库")
    print("=" * 70)


if __name__ == "__main__":
    main()