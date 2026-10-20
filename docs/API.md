# AI-Native 设备智能运维平台 · 接口文档

> 后端服务：Java Spring Boot 3.2（端口 **8080**），统一前缀 `/api`。
> 本文档与代码同步（`backend/src/main/java/com/aiops/controller`），2026-10-20 更新。

## 一、通用约定

### 1. 基础地址

| 环境 | Base URL |
|---|---|
| 本地 | `http://localhost:8080` |

### 2. 认证方式

采用 **JWT（无状态 Token）**，登录后把 token 放到请求头：

```
Authorization: Bearer <token>
```

- token 有效期 **24 小时**（`JwtUtil`）。
- 单点登录：Redis 存最新 token（`login:token:{userId}`，7 天），重新登录后旧 token 立即失效。

### 3. 哪些接口不需要登录（白名单，`SecurityConfig` 已放开）

| 接口 | 说明 |
|---|---|
| `GET /api/health` | 健康检查 |
| `POST /api/auth/login` / `POST /api/auth/register` | 登录 / 注册 |
| `GET /api/agent/tools/**` | 供 Python Agent 工具调用（`/devices`、`/device-status`、`/telemetry`、`/orders`、`/device-summary`、`/ping`） |
| `GET /api/test/lock` | 分布式锁自测 |
| `GET /api/device/cache/**` | 设备缓存查询（含 `test-write`） |
| `GET /api/knowledge/candidates/approved` | 供 Python 端回流知识库 |

其余接口都需要 `Authorization: Bearer <token>`，未登录返回 `401`：

```json
{"code": 401, "message": "未登录或 Token 无效"}
```

### 4. 角色与权限

| 角色 | 常量 | 说明 |
|---|---|---|
| 学生 | `STUDENT` | 创建工单、查看自己的工单 |
| 教师 | `TEACHER` | 同学生 |
| 维修工 | `REPAIRER` | 接单、完成维修、查看派给自己的工单 |
| 管理员 | `ADMIN` | 派单、驳回、验证、审核知识、查维修工列表 |

---

## 二、认证与用户

### POST `/api/auth/login` 登录

- **无需登录**
- 请求体：

```json
{"username": "admin", "password": "123456"}
```

- 成功 `200`：

```json
{"token": "<JWT>", "username": "admin", "realName": "管理员", "role": "ADMIN"}
```

- 失败：`401` `{"message": "账号不存在"}` 或 `{"message": "密码错误"}`

### POST `/api/auth/register` 注册

- **无需登录**
- 请求体：

```json
{"username": "zhangsan", "password": "123456", "realName": "张三", "phone": "13800000000", "role": "STUDENT", "inviteCode": ""}
```

- 校验规则：
  - `username` 至少 3 位、`password` 至少 6 位、`realName` 必填；
  - 用户名唯一；`role` 只能是 `STUDENT / TEACHER / REPAIRER / ADMIN`；
  - `ADMIN` 需邀请码 `ADMIN2026`，`REPAIRER` 需 `REPAIR2026`（`STUDENT / TEACHER` 不用）。
- 成功 `200`：`{"message": "注册成功", "userId": 1}`

### GET `/api/auth/me` 当前用户信息 🔒

- 返回：`{"userId": 1, "username": "admin", "role": "ADMIN"}`

### GET `/api/users/repairers` 维修工列表 🔒（仅 ADMIN）

- 成功 `200`：数组，每项 `{"id", "username", "realName", "phone"}`（不含密码）
- 非管理员 `403`：`{"message": "只有管理员可以查看维修工列表"}`

---

## 三、健康检查

### GET `/api/health`

- **无需登录**
- 返回：`{"status": "UP", "service": "ai-ops-backend", "time": "..."}`

---

## 四、工单（核心业务）

### POST `/api/orders` 创建工单 🔒（STUDENT / TEACHER）

- 请求体：

```json
{"deviceId": 1, "description": "空调制冷异常", "aiDiagnosisSummary": "疑似制冷剂不足，详见 AI 诊断"}
```

- 成功 `200`：返回完整 `RepairOrder` 对象（含 `id`、`status = PENDING_REVIEW` 等）

### POST `/api/orders/{id}/assign` 审核派单 🔒（仅 ADMIN）

- 请求体：`{"repairerId": 2, "reviewComment": "请优先处理"}`
- 成功 `200`：`{"message": "派单成功"}`
- 失败 `400`：`{"message": "<原因>"}`（如状态不合法、已被并发派单等）

### POST `/api/orders/{id}/reject` 驳回 🔒（仅 ADMIN）

- 请求体：`{"reviewComment": "信息不足，请补充"}`
- 成功 `200`：`{"message": "驳回成功"}`

### POST `/api/orders/{id}/start` 维修工接单 🔒

- 无请求体
- 成功 `200`：`{"message": "接单成功"}`

### POST `/api/orders/{id}/complete` 维修完成 🔒

- 请求体：`{"repairComment": "已更换滤网", "repairReason": "滤网堵塞导致过热"}`
- 成功 `200`：`{"message": "维修完成，待验证"}`（状态 → `VERIFYING`）

### POST `/api/orders/{id}/verify` 验证通过 🔒（仅 ADMIN）

- 无请求体
- 成功 `200`：`{"message": "验证通过，工单已完成"}`（状态 → `COMPLETED`，触发状态恢复 + 知识回流）

### GET `/api/orders` 工单列表 🔒

- 查询参数：`status`（可选，按状态过滤）
- 按角色过滤：学生看自己的、维修工看派给自己的、管理员看全部

### GET `/api/orders/{id}` 工单详情 🔒

- 成功 `200`：返回 `RepairOrder` 对象；不存在 `404` `{"message": "工单不存在"}`

> 状态机：`PENDING_REVIEW → ASSIGNED → REPAIRING → VERIFYING → COMPLETED`（另有 `REJECTED`）。
> 并发保障：Redisson 分布式锁 + 状态前置校验 + 乐观锁 `version` 三道防线。

---

## 五、知识候选（知识回流）

### GET `/api/knowledge/candidates` 候选分页 🔒（仅 ADMIN）

- 查询参数：`status`（可选）、`page`（默认 1）、`size`（默认 10）
- 返回：`{"total": 3, "page": 1, "size": 10, "list": [...]}`

### POST `/api/knowledge/candidates/{id}/approve` 审核通过 🔒（仅 ADMIN）

- 请求体（可选）：`{"comment": "同意回流"}`
- 成功 `200`：`{"message": "审核通过"}`

### POST `/api/knowledge/candidates/{id}/reject` 审核驳回 🔒（仅 ADMIN）

- 请求体（可选）：`{"comment": "依据不足"}`
- 成功 `200`：`{"message": "已驳回"}`

### GET `/api/knowledge/candidates/approved` 已通过候选

- **无需登录**（供 Python 端回流知识库）
- 返回：`KnowledgeCandidate` 数组

---

## 六、设备缓存（缓存一致性）

### GET `/api/device/cache/{deviceId}` 查询设备最新状态

- **无需登录**
- 成功 `200`：返回缓存中的设备状态快照；不存在 `404` `{"message": "设备状态不存在"}`

### POST `/api/device/cache/{deviceId}/test-write` 测试写入

- **无需登录**（测试用）
- 请求体：`{"status": "FAULT"}`
- 逻辑：先更 DB → 删缓存 → 延迟双删（500ms），用于验证缓存一致性
- 成功 `200`：`{"message": "写入完成", "newStatus": "FAULT"}`

---

## 七、Agent 工具接口（供 Python Agent 调用，均无需登录）

> 这些接口是 LangGraph Agent 的 5 个查询工具的底层实现，统一前缀 `/api/agent/tools`。

### GET `/api/agent/tools/devices` 设备列表

- 查询参数：`status`、`deviceType`、`keyword`（模糊匹配设备名/编号）、`limit`（默认 200，上限 500）
- 返回：`{"total": 50, "returned": 50, "truncated": false, "devices": [...]}`

### GET `/api/agent/tools/device-status` 单台设备实时状态

- 查询参数：`deviceId`（必填）
- 返回：`{"device": {...}, "currentStatus": "NORMAL", "lastSeen": "...", "latestTelemetry": {...}}`
- 不存在 `404`：`{"message": "设备不存在: id=..."}`

### GET `/api/agent/tools/telemetry` 遥测趋势

- 查询参数：`deviceId`（必填）、`limit`（默认 50，上限 200）
- 返回：`{"deviceId": 1, "total": 2000, "returned": 50, "truncated": true, "telemetryList": [...]}`

### GET `/api/agent/tools/orders` 工单列表

- 查询参数：`status`、`deviceId`、`limit`（默认 100，上限 300）
- 返回：`{"total": 5, "returned": 5, "truncated": false, "orders": [...]}`

### GET `/api/agent/tools/device-summary` 设备总览统计

- 返回：`{"total": 50, "byStatus": {"NORMAL": 45, ...}, "byType": {"空调": 13, ...}, "byStatusAndType": {"WARNING": {"空调": 4, ...}}}`

### GET `/api/agent/tools/ping` 探活

- 返回：`{"status": "UP", "service": "java-backend-tools"}`

---

## 八、测试 / 调试接口

### GET `/api/test/lock` 分布式锁自测

- **无需登录**
- 逻辑：`tryLock(0, 10, SECONDS)` 抢 `test:lock:demo` 锁，抢到后 sleep 3 秒再释放
- 返回：抢到 `{"success": true, "message": "获取锁成功，业务处理完成"}`；抢不到 `{"success": false, "message": "获取锁失败，说明有其他线程正在执行"}`
- ⚠️ 生产环境建议删除（代码注释已标注）

### GET `/api/auth/debug/hash` 密码加密调试 🔒

- 查询参数：`raw`
- 返回：BCrypt 加密后的字符串
