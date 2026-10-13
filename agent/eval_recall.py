# -*- coding: utf-8 -*-
"""
评估集测 Recall@k + 兜底准确率
支持三种样本类型：
  - positive：期望命中某篇手册（算 Recall@k）
  - negative：知识库外，期望触发兜底（算兜底准确率）
  - vague：模糊问题，期望命中任意一篇相关手册
"""
import os

# HuggingFace 离线模式（模型已缓存，跳过联网检查）
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import json
import time
from pathlib import Path
from retriever import build_bm25_index, hybrid_search

BASE_DIR = Path(__file__).resolve().parent
EVAL_SET_PATH = BASE_DIR / "knowledge" / "eval_set.json"

K_LIST = [1, 3, 5]
FALLBACK_THRESHOLD = 0.6


def evaluate():
    print("=" * 80)
    print("RAG 检索质量评估（三类样本：positive / negative / vague）")
    print("=" * 80)

    eval_set = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))
    total = len(eval_set)
    n_pos = sum(1 for x in eval_set if x.get("type") == "positive")
    n_neg = sum(1 for x in eval_set if x.get("type") == "negative")
    n_vague = sum(1 for x in eval_set if x.get("type") == "vague")
    print(f"样本总数：{total}（positive={n_pos}, negative={n_neg}, vague={n_vague}）\n")

    print("初始化 BM25 索引...")
    bm25, manuals = build_bm25_index()

    hits = {k: 0 for k in K_LIST}
    fallback_correct = 0
    vague_hits = 0
    total_time = 0.0
    details = []

    print("-" * 80)
    for i, item in enumerate(eval_set, 1):
        query = item["query"]
        expected = set(item.get("expected_ids", []))
        stype = item.get("type", "positive")

        start = time.time()
        results = hybrid_search(query, bm25, manuals, top_k=5)
        elapsed = time.time() - start
        total_time += elapsed

        result_ids = [r["id"] for r in results]
        top_score = results[0].get("rerank_score", 0) if results else 0.0

        if stype == "positive":
            mark = "✅" if expected & set(result_ids[:1]) else ("🔸" if expected & set(result_ids[:3]) else "❌")
            for k in K_LIST:
                if expected & set(result_ids[:k]):
                    hits[k] += 1
        elif stype == "negative":
            # 期望：结果为空 或 Top1 得分 < 阈值
            if not results or top_score < FALLBACK_THRESHOLD:
                fallback_correct += 1
                mark = "✅"
            else:
                mark = "❌"
        elif stype == "vague":
            if expected & set(result_ids[:3]):
                vague_hits += 1
                mark = "✅"
            else:
                mark = "❌"
        else:
            mark = "?"

        details.append((stype, query, result_ids[:3], top_score, mark, elapsed))

    print("-" * 80)
    for stype, q, ids, score, mark, t in details:
        short_q = q[:34] + ".." if len(q) > 36 else q
        print(f"{mark} [{stype:<8}] {short_q:<38} top1={score:.3f}  ({t:.2f}s)")

    print("-" * 80)
    print("\n【positive 样本 · Recall 指标】")
    for k in K_LIST:
        recall = hits[k] / n_pos * 100 if n_pos else 0
        print(f"  Recall@{k} = {hits[k]}/{n_pos} = {recall:.1f}%")

    print("\n【negative 样本 · 兜底准确率】")
    fb = fallback_correct / n_neg * 100 if n_neg else 0
    print(f"  兜底正确 = {fallback_correct}/{n_neg} = {fb:.1f}%")
    print(f"  （阈值 {FALLBACK_THRESHOLD}：Top1 Rerank 得分低于该值即触发兜底）")

    print("\n【vague 样本 · 模糊问题命中率】")
    vg = vague_hits / n_vague * 100 if n_vague else 0
    print(f"  命中 = {vague_hits}/{n_vague} = {vg:.1f}%")

    print(f"\n【性能】平均单次检索 {total_time/total:.2f}s")

    print("\n【说明】")
    print("  Recall@k：positive 样本的期望手册出现在 Top-k 结果中。")
    print("  兜底准确率：negative 样本正确触发低分兜底（不误答）。")
    print("  模糊命中率：vague 样本至少命中一篇相关手册。")


if __name__ == "__main__":
    evaluate()