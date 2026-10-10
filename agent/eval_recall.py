# -*- coding: utf-8 -*-
"""
评估集测 Recall@k
"""
import json
import time
from pathlib import Path

from retriever import build_bm25_index, hybrid_search

# 评估集路径
BASE_DIR = Path(__file__).resolve().parent
EVAL_SET_PATH = BASE_DIR / "knowledge" / "eval_set.json"

# 评估指标
K_LIST = [1, 3, 5]


def evaluate():
    print("=" * 70)
    print("RAG 检索质量评估")
    print("=" * 70)

    # 加载评估集
    eval_set = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))
    print(f"评估集规模：{len(eval_set)} 条查询\n")

    # 构建 BM25 索引
    print("初始化 BM25 索引...")
    bm25, manuals = build_bm25_index()

    # 统计命中情况
    hits = {k: 0 for k in K_LIST}
    total = len(eval_set)

    print("-" * 70)
    print(f"{'查询':<40}{'期望':<18}{'命中':<6}")
    print("-" * 70)

    for i, item in enumerate(eval_set, 1):
        query = item["query"]
        expected = set(item["expected_ids"])

        # 用 top_k=5，这样能一次评估 @1/@3/@5
        start = time.time()
        results = hybrid_search(query, bm25, manuals, top_k=5)
        elapsed = time.time() - start

        result_ids = [r["id"] for r in results]

        # 计算 Recall@k
        mark = ""
        for k in K_LIST:
            top_k_ids = set(result_ids[:k])
            if expected & top_k_ids:
                hits[k] += 1
                if k == 1:
                    mark = "✅"

        short_q = query[:36] + ".." if len(query) > 38 else query
        expected_str = ",".join(expected)[:16]
        print(f"{short_q:<40}{expected_str:<18}{mark:<6}  ({elapsed:.2f}s)")

    print("-" * 70)
    print("\n【Recall 指标】")
    for k in K_LIST:
        recall = hits[k] / total * 100
        print(f"  Recall@{k} = {hits[k]}/{total} = {recall:.1f}%")

    print("\n【说明】")
    print("  Recall@k 表示：期望命中的手册是否出现在 Top-k 结果中。")
    print("  如果 Recall@1 高，说明首条结果就很准；Recall@3 高，说明给大模型的候选集质量好。")


if __name__ == "__main__":
    evaluate()