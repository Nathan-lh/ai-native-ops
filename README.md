# AI-Native 设备智能运维平台

> 设备遥测数据经 **MQTT 高并发接入** Java 后端并实时评估健康状态；**Python Agent** 提供自然语言观测、基于「遥测趋势 + 维修知识库 + 历史工单」的**有证据智能诊断**并引导建单、前端一键生成工单；工单完成后设备状态**自动恢复**、维修结论**回流知识库**，形成"越用越准"的闭环。

## 架构

```mermaid
flowchart LR
    SIM[设备模拟器] -->|MQTT| EMQX[EMQX Broker]
    EMQX -->|订阅 telemetry/#| JAVA[Java 后端<br/>Spring Boot 3]
    JAVA -->|攒批入库 + 健康评估| DB[(MySQL 8.0)]
    JAVA -->|状态快照 / 分布式锁 / SSO| RD[(Redis 7)]
    JAVA -->|设备缓存一致性| RD
    UI[Vue3 前端] -->|REST + SSE| JAVA
    UI -->|SSE 对话| AGENT[Python Agent<br/>FastAPI + LangGraph]
    AGENT -->|HTTP 工具调用| JAVA
    AGENT -->|混合检索| CHROMA[(Chroma 向量库)]
    AGENT -->|Rerank| RERANK[BGE Reranker]
    LLM[DeepSeek / Ollama] --> AGENT
```

**双语言分工**：Java 管有状态业务 / 事务 / 并发（MySQL + Redis）；Python 管 LangGraph / RAG 推理编排（Chroma 向量库）。业务数据只由 Java 持有，知识库数据由 Python 管理，边界清晰。

## 技术栈

| 层 | 选型 |
|---|---|
| JDK / 后端框架 | JDK 17 / Spring Boot 3.2 + MyBatis-Plus |
| 数据库 / 缓存 | MySQL 8.0 / Redis 7 |
| MQTT | EMQX 5 + Eclipse Paho（异步 + 攒批） |
| 认证 | Spring Security + JWT（单点登录） |
| 分布式锁 | Redisson |
| Agent | Python 3.11 + FastAPI + LangGraph（ReAct） |
| LLM | DeepSeek API（生产）/ Ollama（本地） |
| 向量库 / Embedding / Rerank | Chroma / BGE-small-zh-v1.5 / BGE-Reranker |
| 前端 | Vue 3 + Vite + Element Plus + Pinia + ECharts |

## 核心闭环

```
设备上报遥测 → MQTT → Java 接入 + 健康评估 → 状态(正常/预警/故障)
自然语言提问 → Agent 诊断(遥测趋势 + RAG 手册 + 历史工单) → 有证据给结论
解决不了 → 生成工单 → 状态机流转
  PENDING_REVIEW → ASSIGNED → REPAIRING → VERIFYING → COMPLETED
COMPLETED 后 → 遥测连续 N 次正常 → 设备状态自动恢复 NORMAL
维修记录(真实原因) → 人工审核 → 回流知识库 → 越用越准
```

## 快速启动

### 1. 中间件（MySQL + Redis + EMQX）

```bash
docker compose up -d
```

### 2. Java 后端（端口 8080）

```bash
cd backend
mvn spring-boot:run
```

### 3. Python 设备模拟器

```bash
cd simulator
pip install -r requirements.txt
python device_simulator.py
```

### 4. Python Agent（端口 8000）

```bash
cd agent
pip install -r requirements.txt
# 复制 .env.example 为 .env，填入你的 DEEPSEEK_API_KEY
cp .env.example .env
python main.py
```

> 模型已本地缓存时可离线运行，避免 HuggingFace 联网检查卡顿：
> `export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`（Windows 用 `set`）

### 5. Vue3 前端（端口 5173）

```bash
cd frontend
npm install
npm run dev
```

### 6. 压测脚本（可选）

```bash
cd simulator
# MQTT 洪峰压测（--rate 限速 / 0 不限速打洪峰两模式）
python mqtt_load_test.py --total 50000 --rate 1000
# HTTP 接口 QPS 压测
python http_load_test.py --url http://localhost:8080/api/health --total 10000 --concurrency 50
```

### 测试账号

| 用户名 | 角色 | 密码 |
|---|---|---|
| admin | ADMIN | 123456 |
| repairer | REPAIRER | 123456 |
| repairer2 | REPAIRER | 123456 |
| student | STUDENT | 123456 |

## 核心设计亮点

### 1. 高并发遥测接入
- `MqttAsyncClient` 异步订阅 + **有界队列（容量 10000）背压** + **攒批入库（每批 100 条）**
- 消息洪峰下不阻塞 MQTT 消费，队列满时按背压策略丢弃，保证核心链路稳定

### 2. 有证据的 RAG 智能诊断（四层）
```
结构化知识库(25 篇故障手册，4 类设备、9 类故障)
  → BM25 关键词 + 向量语义召回 → RRF 倒数排名融合(k=60)
  → Cross-Encoder(BGE-Reranker) 精排
  → 低分兜底(< 0.6 判未命中 → 引导建工单)
```
- 自建 70 条评估集（50 正 / 12 负 / 8 模糊），**Recall@1 达 100%**
- 诊断结论附维修依据（现象 / 可能原因 / 排查步骤 / 维修方法），而非凭空生成

### 3. 工单状态机 + 三重并发保障
- 全生命周期状态机：`PENDING_REVIEW → ASSIGNED → REPAIRING → VERIFYING → COMPLETED`
- 三道防线：**Redisson 分布式锁**（`tryLock(3,10,SECONDS)`）+ **状态前置校验** + **乐观锁 version**
- 并发测试：50 线程抢派同一工单，**仅 1 个成功、0 误派**

### 4. 状态恢复 + 知识闭环
- 遥测连续 N 次正常去抖判定 → `VERIFYING` 工单自动 `COMPLETED`、设备恢复 `NORMAL`
- 维修结论经**人工审核**后回流知识库，实现"越用越准"

### 5. 缓存一致性 + 单点登录
- **Cache-Aside + 延迟双删**：写先更 DB → 删缓存 → 延迟再删一次，保证缓存强一致
- Redis 存储 token 版本，旧 token 秒级失效，实现单点登录

### 6. 性能压测与优化

- **MQTT 高并发入库压测**（50 台设备洪峰上报，端到端测入库吞吐）
  - 优化前 **75 条/s** → 优化后 **400 条/s**，**5.3 倍**提升
  - 优化手段：真批量 INSERT（一条 SQL 多 VALUES，取代逐条 insert）+ 设备类型本地缓存（`ConcurrentHashMap` 取代每条查库）+ 状态快照 `upsert`（`ON DUPLICATE KEY UPDATE` 取代"先查再写"）+ 热路径日志降级（`log.info` → `log.debug`）
- **背压保护**：有界队列（容量 10000），队列满非阻塞丢弃并告警，保证洪峰下核心链路不被打垮
- **HTTP 接口 QPS**（50 并发，`http_load_test.py`）

| 接口 | QPS | P99 | 说明 |
|---|---|---|---|
| `/api/health` | ~3087 req/s | 39ms | 无依赖探活 |
| `/api/devices/cache`（命中 Redis） | ~2905 req/s | — | 约 6 倍于回源 DB |
| `/api/devices`（回源 MySQL） | ~469 req/s | — | 验证缓存收益 |

## 文档

- [接口文档](./docs/API.md)：全部 REST 接口说明（鉴权白名单、角色权限、工单状态机）

## 目录结构

```
├── backend/      Java 后端（Spring Boot 3）
├── agent/        Python Agent（FastAPI + LangGraph + RAG）
├── simulator/    设备遥测模拟器 + 压测脚本
├── frontend/     Vue3 前端
├── docs/         数据库脚本 / 设计文档 / 接口文档（API.md）
├── LICENSE       MIT 开源协议
└── docker-compose.yml
```

## 截图

> 系统演示视频关键帧，按时间顺序排列（截图名即视频时间点）。

<table>
<tr><td align="center"><img src="docs/screenshots/00m20s.jpg" width="95%" alt="00:20" /><br/><b>00:20</b></td><td align="center"><img src="docs/screenshots/00m25s.jpg" width="95%" alt="00:25" /><br/><b>00:25</b></td><td align="center"><img src="docs/screenshots/00m40s.jpg" width="95%" alt="00:40" /><br/><b>00:40</b></td></tr>
<tr><td align="center"><img src="docs/screenshots/00m50s.jpg" width="95%" alt="00:50" /><br/><b>00:50</b></td><td align="center"><img src="docs/screenshots/01m05s.jpg" width="95%" alt="01:05" /><br/><b>01:05</b></td><td align="center"><img src="docs/screenshots/01m10s.jpg" width="95%" alt="01:10" /><br/><b>01:10</b></td></tr>
<tr><td align="center"><img src="docs/screenshots/01m15s.jpg" width="95%" alt="01:15" /><br/><b>01:15</b></td><td align="center"><img src="docs/screenshots/01m40s.jpg" width="95%" alt="01:40" /><br/><b>01:40</b></td><td align="center"><img src="docs/screenshots/01m45s.jpg" width="95%" alt="01:45" /><br/><b>01:45</b></td></tr>
<tr><td align="center"><img src="docs/screenshots/02m00s.jpg" width="95%" alt="02:00" /><br/><b>02:00</b></td><td align="center"><img src="docs/screenshots/02m20s.jpg" width="95%" alt="02:20" /><br/><b>02:20</b></td><td align="center"><img src="docs/screenshots/02m40s.jpg" width="95%" alt="02:40" /><br/><b>02:40</b></td></tr>
<tr><td align="center"><img src="docs/screenshots/02m50s.jpg" width="95%" alt="02:50" /><br/><b>02:50</b></td><td align="center"><img src="docs/screenshots/02m55s.jpg" width="95%" alt="02:55" /><br/><b>02:55</b></td><td align="center"><img src="docs/screenshots/03m00s.jpg" width="95%" alt="03:00" /><br/><b>03:00</b></td></tr>
<tr><td align="center"><img src="docs/screenshots/03m05s.jpg" width="95%" alt="03:05" /><br/><b>03:05</b></td><td align="center"><img src="docs/screenshots/03m10s.jpg" width="95%" alt="03:10" /><br/><b>03:10</b></td><td align="center"><img src="docs/screenshots/03m20s.jpg" width="95%" alt="03:20" /><br/><b>03:20</b></td></tr>
<tr><td align="center"><img src="docs/screenshots/03m25s.jpg" width="95%" alt="03:25" /><br/><b>03:25</b></td><td align="center"><img src="docs/screenshots/03m30s.jpg" width="95%" alt="03:30" /><br/><b>03:30</b></td><td align="center"><img src="docs/screenshots/03m35s.jpg" width="95%" alt="03:35" /><br/><b>03:35</b></td></tr>
<tr><td align="center"><img src="docs/screenshots/03m40s.jpg" width="95%" alt="03:40" /><br/><b>03:40</b></td><td align="center"><img src="docs/screenshots/03m45s.jpg" width="95%" alt="03:45" /><br/><b>03:45</b></td><td align="center"><img src="docs/screenshots/04m10s.jpg" width="95%" alt="04:10" /><br/><b>04:10</b></td></tr>
<tr><td align="center"><img src="docs/screenshots/04m55s.jpg" width="95%" alt="04:55" /><br/><b>04:55</b><br/><sub>同一账号二次登录提示（单点登录互斥）</sub></td><td align="center"><img src="docs/screenshots/05m20s.jpg" width="95%" alt="05:20" /><br/><b>05:20</b></td><td></td></tr>
</table>

## 许可

[MIT](./LICENSE) · Copyright (c) 2026 刘欢 (Nathan-lh)
