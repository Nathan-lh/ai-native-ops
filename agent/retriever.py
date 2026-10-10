# -*- coding: utf-8 -*-
"""
BM25 + 向量混合检索 + RRF 融合 + Rerank 精排 + 兜底检测
"""
import os

# 强制 HuggingFace 离线模式 + 指定缓存目录（模型已下载在本地）
# 必须在 import sentence_transformers 之前设置
os.environ.setdefault("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import json
from pathlib import Path
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from knowledge_base import get_collection, get_model, QUERY_INSTRUCTION, KNOWLEDGE_DIR

# 加载原始手册数据，构建 BM25 索引
MANUALS_PATH = KNOWLEDGE_DIR / "manuals_all.json"


def build_bm25_index():
    """构建 BM25 关键词索引"""
    manuals = json.loads(MANUALS_PATH.read_text(encoding="utf-8"))
    # 简易中文分词：按字符切分（工业界可用 jieba，这里为了轻量先用字符级）
    tokenized_corpus = []
    for m in manuals:
        text = (
            f"{m['device_type']} {m['fault_type']} {m['fault_phenomenon']} "
            f"{' '.join(m.get('possible_causes', []))} "
            f"{' '.join(m.get('troubleshoot_steps', []))} {m['repair_method']}"
        )
        tokenized_corpus.append(list(text))

    bm25 = BM25Okapi(tokenized_corpus)
    return bm25, manuals


def search_vector(query: str, top_k: int = 5):
    """向量检索"""
    collection = get_collection()
    model = get_model()
    query_vec = model.encode(QUERY_INSTRUCTION + query, normalize_embeddings=True)
    res = collection.query(query_embeddings=[query_vec.tolist()], n_results=top_k)

    results = []
    for doc_id, dist in zip(res["ids"][0], res["distances"][0]):
        results.append({"id": doc_id, "score": float(dist), "source": "vector"})
    return results


def search_bm25(query: str, bm25, manuals, top_k: int = 5):
    """BM25 关键词检索"""
    tokenized_query = list(query)
    scores = bm25.get_scores(tokenized_query)

    # 获取得分最高的 top_k 个
    scored_docs = list(zip(range(len(scores)), scores))
    scored_docs.sort(key=lambda x: x[1], reverse=True)

    results = []
    for idx, score in scored_docs[:top_k]:
        if score > 0:  # 过滤掉完全不相关的
            results.append({"id": manuals[idx]["id"], "score": float(score), "source": "bm25"})
    return results


def rrf_fusion(vector_results, bm25_results, k: int = 60):
    """RRF（Reciprocal Rank Fusion）倒数排名融合"""
    fused_scores = {}

    for rank, item in enumerate(vector_results):
        doc_id = item["id"]
        fused_scores[doc_id] = fused_scores.get(doc_id, 0) + 1 / (k + rank + 1)

    for rank, item in enumerate(bm25_results):
        doc_id = item["id"]
        fused_scores[doc_id] = fused_scores.get(doc_id, 0) + 1 / (k + rank + 1)

    # 按融合得分降序排序
    sorted_results = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_results


# ==================== Rerank 精排 ====================
_reranker = None

def get_reranker():
    """懒加载 CrossEncoder 模型"""
    global _reranker
    if _reranker is None:
        # 使用 BGE Reranker Base，约 400MB
        print("[加载 Reranker 模型] 首次运行需从 HuggingFace 下载约 400MB...")
        _reranker = CrossEncoder("BAAI/bge-reranker-base", max_length=512)
    return _reranker


def rerank(query: str, candidates: list, top_k: int = 3):
    """
    用 Cross-Encoder 对 RRF 粗排候选集进行精排
    """
    if not candidates:
        return []

    reranker = get_reranker()
    # 构造 (query, document) 对，这里用故障现象拼接设备类型和故障类型
    pairs = [[query,
              f"{c['device_type']} {c['fault_type']} {c['fault_phenomenon']} "
              f"{c.get('possible_causes', '')} {c.get('troubleshoot_steps', '')}"]
             for c in candidates]

    # 计算相关性得分（得分越高越相关）
    scores = reranker.predict(pairs)

    # 绑回原数据
    for idx, score in enumerate(scores):
        candidates[idx]["rerank_score"] = float(score)

    # 降序排序
    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
    return candidates[:top_k]


def hybrid_search(query: str, bm25, manuals, top_k: int = 3):
    """混合检索 + Rerank 精排 + 兜底检测"""
    # 1. 粗排：各拿 10 个候选
    vec_res = search_vector(query, top_k=10)
    bm25_res = search_bm25(query, bm25, manuals, top_k=10)

    # 2. RRF 融合
    fused = rrf_fusion(vec_res, bm25_res)

    # 3. 组装候选集
    manual_dict = {m["id"]: m for m in manuals}
    candidates = []
    for doc_id, score in fused[:10]:
        m = manual_dict[doc_id]
        candidates.append({
            "id": doc_id,
            "device_type": m["device_type"],
            "fault_type": m["fault_type"],
            "fault_phenomenon": m["fault_phenomenon"],
            "possible_causes": "；".join(m.get("possible_causes", [])),
            "troubleshoot_steps": "；".join(m.get("troubleshoot_steps", [])),
            "repair_method": m["repair_method"],
            "rrf_score": score
        })

    # 4. Rerank 精排，取最终 Top K
    final_results = rerank(query, candidates, top_k=top_k)

    # 5. 兜底检测：如果最高精排得分低于 0.6，认为知识库未命中
    if final_results:
        top_score = final_results[0].get("rerank_score", 0)
        if top_score < 0.6:
            print(f"[兜底触发] 最高 Rerank 得分 {top_score:.4f} < 0.6，返回空结果")
            return []

    return final_results


if __name__ == "__main__":
    print("初始化 BM25 索引...")
    bm25, manuals = build_bm25_index()

    query = "空调温度一直升高是什么原因？"
    print(f"查询：{query}")
    print("-" * 60)

    # 这里会触发首次下载 Reranker 模型
    results = hybrid_search(query, bm25, manuals)
    if not results:
        print("未命中知识库（触发兜底）")
    else:
        for i, r in enumerate(results, 1):
            print(f"Top{i}  id={r['id']}  类型={r['device_type']}/{r['fault_type']}  Rerank得分={r.get('rerank_score', 0):.4f}")