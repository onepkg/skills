# 托管智能体 — 记忆存储

> **公开测试版。** 记忆存储随 `managed-agents-2026-04-01` beta 头发布；SDK 会在所有 `client.beta.memory_stores.*` 调用上自动设置它。如果缺少 `client.beta.memory_stores`，请升级到最新的 SDK 版本。

会话默认是短暂的 — 当会话结束时，智能体学到的任何东西都会消失。**记忆存储**是工作区范围的文本文档集合，会跨会话保留。当存储附加到会话时（通过 `resources[]`），它会作为文件系统目录挂载到容器中；智能体使用普通文件工具读取和写入它，并且系统提示会告诉它挂载点在哪里。

对记忆的每次变更都会产生一个不可变的**记忆版本**（`memver_...`），为您提供审计跟踪和时间点回滚/修订。

## 对象模型

| 对象 | ID 前缀 | 范围 | 注意 |
| --- | --- | --- | --- |
| 记忆存储 | `memstore_...` | 工作区 | 通过 `resources[]` 附加到会话 |
| 记忆 | `mem_...` | 存储 | 一个文本文件，通过 `path` 寻址（每个 ≤ 100KB — 偏好多个小文件） |
| 记忆版本 | `memver_...` | 记忆 | 每次变更的不可变快照；`operation` ∈ `created` / `modified` / `deleted` |

## 创建存储

`description` 会传递给智能体，以便它知道存储包含什么 — 为模型编写，不是为人类。

```python
store = client.beta.memory_stores.create(
    name="用户偏好",
    description="每个用户的偏好和项目上下文。",
)
print(store.id)  # memstore_01Hx...
```

其他 SDK：TypeScript `client.beta.memoryStores.create({...})`；Go `client.Beta.MemoryStores.New(ctx, ...)`。完整的每种语言表格请参阅 `shared/managed-agents-api-reference.md` → SDK 方法参考。

存储支持 `retrieve` / `update` / `list`（带 `include_archived`、`created_at_{gte,lte}` 过滤器） / `delete` / **`archive`**。归档使存储变为只读 — 现有会话附件继续，新会话无法引用它；无法取消归档。

### 用内容播种（可选）

在任何会话运行之前预加载参考材料。`memories.create` 在给定的 `path` 创建记忆；如果路径已存在记忆，调用返回 `409`（`memory_path_conflict_error`，带有 `conflicting_memory_id`）。存储 ID 是第一个位置参数。

```python
client.beta.memory_stores.memories.create(
    store.id,
    path="/formatting_standards.md",
    content="所有报告使用 GAAP 格式。日期为 ISO-8601...",
)
```

## 附加到会话

记忆存储与会话的 `resources[]` 数组中的 `file` 和 `github_repository` 资源一起（请参阅 `shared/managed-agents-environments.md` → 资源）。记忆存储**仅在会话创建时附加** — `sessions.resources.add()` 不接受 `memory_store`。

```python
session = client.beta.sessions.create(
    agent=agent.id,
    environment_id=environment.id,
    resources=[
        {
            "type": "memory_store",
            "memory_store_id": store.id,
            "access": "read_write",  # 或 "read_only"；默认是 "read_write"
            "instructions": "用户偏好和项目上下文。在开始任何任务之前检查。",
        }
    ],
)
```

| 字段 | 必需 | 注意 |
| --- | --- | --- |
| `type` | ✅ | `"memory_store"` |
| `memory_store_id` | ✅ | `memstore_...` |
| `access` | — | `"read_write"`（默认）或 `"read_only"` — 在挂载的文件系统级别强制执行 |
| `instructions` | — | 除了存储的 `name`/`description` 之外，此存储的会话特定指导。≤ 4,096 字符。 |

**每个会话最多 8 个记忆存储。** 当不同切片的记忆具有不同所有者或生命周期时附加多个 — 例如，一个只读的共享参考存储加上每个用户的读-写存储，或每个最终用户/团队/项目共享单个智能体配置的一个存储。

### 智能体如何看到它（FUSE 挂载）

每个附加的存储都在会话容器中的 `/mnt/memory/<store-name>/` 处挂载。智能体使用标准文件工具（`bash`、`read`、`write`、`edit`、`glob`、`grep`）与它交互 — 没有专用的记忆工具。`access: "read_only"` 使挂载在文件系统级别变为只读；`"read_write"` 允许智能体在其下创建、编辑和删除文件。每个挂载的简短描述（名称、路径、`instructions`、访问权限）会自动注入到系统提示中，以便智能体知道存储存在，而您无需提及。

智能体对挂载所做的写入会被持久化回存储并产生记忆版本，就像主机端的 `memories.update` 调用一样。

## 直接管理记忆（主机端）

使用这些进行审查工作流、纠正不良记忆，或带外播种存储。

### 列表

返回 `Memory | MemoryPrefix` 条目 — 分层列出时，`MemoryPrefix`（`type: "memory_prefix"`，仅一个 `path`）是类似目录的节点。使用 `path_prefix` 限定范围（包含尾部斜杠：`"/notes/"` 匹配 `/notes/a.md` 但不匹配 `/notes_backup/old.md`）并使用 `depth` 约束树遍历。`order_by` / `order` 对结果排序。传递 `view="full"` 以在每个条目中包含 `content`；默认 `"basic"` 仅返回元数据。

```python
for m in client.beta.memory_stores.memories.list(store.id, path_prefix="/"):
    if m.type == "memory":
        print(f"{m.path}  ({m.content_size_bytes} 字节，sha={m.content_sha256[:8]})")
    else:  # "memory_prefix"
        print(f"{m.path}/")
```

### 读取

```python
mem = client.beta.memory_stores.memories.retrieve(memory_id, memory_store_id=store.id)
print(mem.content)
```

`retrieve` 默认为 `view="full"`（包含内容）；`view` 主要在列表端点上重要。

### 创建 vs 更新

| 操作 | 寻址方式 | 语义 |
| --- | --- | --- |
| `memories.create(store_id, path=..., content=...)` | **路径** | 在 `path` 创建。如果路径已被占用则返回 `409`（`memory_path_conflict_error`，包含 `conflicting_memory_id`）。 |
| `memories.update(mem_id, memory_store_id=..., path=..., content=...)` | **`mem_...` ID** | 变更现有记忆。更改 `content`、`path`（重命名）或两者。重命名到已占用的路径会返回相同的 `409 memory_path_conflict_error`。 |

```python
mem = client.beta.memory_stores.memories.create(
    store.id,
    path="/preferences/formatting.md",
    content="始终使用制表符，不要空格。",
)

client.beta.memory_stores.memories.update(
    mem.id,
    memory_store_id=store.id,
    path="/archive/2026_q1_formatting.md",  # 重命名
)
```

### 乐观并发（`update` 上的先决条件）

`memories.update` 接受 `precondition`，以便您可以读取 → 修改 → 写回而不会覆盖并发写入器。唯一支持的类型是 `content_sha256`。不匹配时 API 返回 `409`（`memory_precondition_failed_error`）— 重新读取并针对新鲜状态重试。

```python
client.beta.memory_stores.memories.update(
    mem.id,
    memory_store_id=store.id,
    content="已更正：始终使用 2 空格缩进。",
    precondition={"type": "content_sha256", "content_sha256": mem.content_sha256},
)
```

### 删除

```python
client.beta.memory_stores.memories.delete(mem.id, memory_store_id=store.id)
```

传递 `expected_content_sha256` 进行有条件删除。

## 审计和回滚 — 记忆版本

每次突变都会创建一个不可变的 `memver_...` 快照。版本在父记忆的生命周期内累积；`memories.retrieve` 始终返回当前头部，版本端点为您提供历史记录。

| 触发它的操作 | 版本上的 `operation` 字段 |
| --- | --- |
| 在新路径上 `memories.create` | `"created"` |
| `memories.update` 更改 `content`、`path` 或两者（或智能体端对挂载的写入） | `"modified"` |
| `memories.delete` | `"deleted"` |

每个版本还记录 `created_by` — 一个带有 `type` ∈ `session_actor` / `api_actor` / `user_actor` 的参与者对象 — 并且，在修订后，记录 `redacted_at` + `redacted_by`。

### 列出版本

最新优先，分页。通过 `memory_id`、`operation`、`session_id`、`api_key_id` 或 `created_at_gte` / `created_at_lte` 过滤。传递 `view="full"` 以包含 `content`；默认仅元数据。

```python
for v in client.beta.memory_stores.memory_versions.list(store.id, memory_id=mem.id):
    print(f"{v.id}: {v.operation}")
```

### 检索版本

```python
version = client.beta.memory_stores.memory_versions.retrieve(
    version_id, memory_store_id=store.id
)
print(version.content)
```

### 修订版本

从历史版本中擦除内容，同时保留审计跟踪（参与者 + 时间戳）。清除 `content`、`content_sha256`、`content_size_bytes` 和 `path`；其他所有内容保留。用于泄露的机密、PII 或用户删除请求。

```python
client.beta.memory_stores.memory_versions.redact(version_id, memory_store_id=store.id)
```

## 端点参考

完整的 HTTP 方法/路径表请参阅 `shared/managed-agents-api-reference.md` → 记忆存储 / 记忆 / 记忆版本。原始 HTTP 基础路径：

```
POST   /v1/memory_stores
POST   /v1/memory_stores/{memory_store_id}/archive
GET    /v1/memory_stores/{memory_store_id}/memories
PATCH  /v1/memory_stores/{memory_store_id}/memories/{memory_id}
GET    /v1/memory_stores/{memory_store_id}/memory_versions
POST   /v1/memory_stores/{memory_store_id}/memory_versions/{version_id}/redact
```

cURL 示例和 CLI（`ant beta:memory-stores ...`），请 WebFetch `shared/live-sources.md` 中的记忆 URL → 托管智能体。
