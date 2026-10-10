# -*- coding: utf-8 -*-
from retriever import build_bm25_index, hybrid_search

print("正在初始化 BM25 索引...")
bm25, manuals = build_bm25_index()

query = "机房里的服务器主板烧了怎么办？"
print(f"查询：{query}")
print("-" * 60)

results = hybrid_search(query, bm25, manuals)

if not results:
    print("【兜底触发】未命中知识库，返回空结果。")
else:
    for i, r in enumerate(results, 1):
        print(f"Top{i}  id={r['id']}  类型={r['device_type']}/{r['fault_type']}  Rerank得分={r.get('rerank_score', 0):.4f}")