# -*- coding: utf-8 -*-
"""命令行测试 Agent：手动输入问题，看 Agent 如何调工具并回答"""
import sys
from agent_core import chat

def main():
    print("=" * 60)
    print("设备运维 Agent 命令行测试（输入 exit 退出）")
    print("=" * 60)
    print("试试问：")
    print("  - 有哪些设备？")
    print("  - 设备 25 现在什么状态？")
    print("  - 设备 1 最近 5 条遥测数据")
    print("  - 有哪些状态异常的设备？")
    print()

    while True:
        try:
            q = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        if q.lower() == "exit":
            break

        try:
            result = chat(q)
            print()
            if result["tool_calls"]:
                print("🔧 调用的工具：")
                for c in result["tool_calls"]:
                    print(f"   - {c['name']}({c['args']})")
            print(f"\n🤖 Agent: {result['answer']}\n")
        except Exception as e:
            print(f"\n❌ 出错: {e}\n")


if __name__ == "__main__":
    main()