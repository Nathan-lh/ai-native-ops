# -*- coding: utf-8 -*-
"""
知识库向量化 + Chroma 构建
"""
import os

# 强制 HuggingFace 离线模式 + 指定缓存目录（模型已下载在本地）
# 必须在 import sentence_transformers 之前设置
os.environ.setdefault("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import json
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

# ==================== 配置 ====================
BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
MANUALS_PATH = KNOWLEDGE_DIR / "manuals_all.json"
CHROMA_DIR = KNOWLEDGE_DIR / "chroma_db"
COLLECTION_NAME = "manuals"

# 中文 Embedding 模型（BGE-small-zh）
MODEL_NAME = "BAAI/bge-small-zh-v1.5"

# BGE 系列查询侧需要加指令前缀（文档侧不加），这是官方约定
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："

# ==================== 工具函数 ====================
def load_manuals() -> list[dict]:
    if not MANUALS_PATH.exists():
        raise FileNotFoundError(f"未找到 {MANUALS_PATH}，请先运行 knowledge/seed_manuals.py")
    return json.loads(MANUALS_PATH.read_text(encoding="utf-8"))

def manual_to_text(m: dict) -> str:
    """把手册拼成一段可检索的文本"""
    causes = "；".join(m.get("possible_causes", []))
    steps = "；".join(m.get("troubleshoot_steps", []))
    return (
        f"设备类型：{m['device_type']}\n"
        f"故障类型：{m['fault_type']}\n"
        f"故障现象：{m['fault_phenomenon']}\n"
        f"遥测签名：{m['telemetry_signature']}\n"
        f"可能原因：{causes}\n"
        f"排查步骤：{steps}\n"
        f"处理方法：{m['repair_method']}"
    )

def manual_to_metadata(m: dict) -> dict:
    """Chroma metadata 只支持 str/int/float/bool"""
    return {
        "device_type": m["device_type"],
        "fault_type": m["fault_type"],
        "severity": m["severity"],
    }

# ==================== 主流程 ====================
def build_knowledge_base():
    print(f"[1/4] 加载手册：{MANUALS_PATH}")
    manuals = load_manuals()
    print(f"      共 {len(manuals)} 篇")

    print(f"[2/4] 加载 Embedding 模型：{MODEL_NAME}")
    print("      首次运行会从 HuggingFace 下载（约 100MB），请耐心等待...")
    model = SentenceTransformer(MODEL_NAME)

    print("[3/4] 向量化文档 ...")
    texts = [manual_to_text(m) for m in manuals]
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=16,
    )

    print(f"[4/4] 写入 Chroma：{CHROMA_DIR}")
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # 幂等处理：每次重建前先删旧 collection
    try:
        client.delete_collection(COLLECTION_NAME)
        print("      已存在旧 collection，已删除")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # 使用余弦距离
    )

    collection.add(
        ids=[m["id"] for m in manuals],
        documents=texts,
        embeddings=embeddings.tolist(),
        metadatas=[manual_to_metadata(m) for m in manuals],
    )

    print(f"      入库完成，collection 中共 {collection.count()} 条")

def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION_NAME)

def get_model():
    return SentenceTransformer(MODEL_NAME)

if __name__ == "__main__":
    build_knowledge_base()