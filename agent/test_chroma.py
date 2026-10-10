# -*- coding: utf-8 -*-
"""最小验证：向量库能否按查询返回结果"""
from knowledge_base import get_collection, get_model, QUERY_INSTRUCTION

collection = get_collection()
model = get_model()

query = "空调温度一直升高是什么原因？"
query_vec = model.encode(QUERY_INSTRUCTION + query, normalize_embeddings=True)

res = collection.query(
    query_embeddings=[query_vec.tolist()],
    n_results=3,
)

print("查询：", query)
print("-" * 60)
for i, (doc_id, meta, dist) in enumerate(zip(
    res["ids"][0], res["metadatas"][0], res["distances"][0]
), 1):
    print(f"Top{i}  id={doc_id}  类型={meta['device_type']}/{meta['fault_type']}  距离={dist:.4f}")