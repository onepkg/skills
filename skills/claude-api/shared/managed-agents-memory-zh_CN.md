# 托管代理 — 记忆存储

> **公开测试版。** 记忆存储通过 `managed-agents-2026-04-01` 测试版标头发放；SDK 会在所有 `client.beta.memory_stores.*` 调用上自动设置。如果缺少 `client.beta.memory_stores`，请升级到最新的 SDK 版本。

默认情况下，会话是临时的——当一个会话结束时，代理所学到的任何内容都会丢失。**记忆存储**是一个工作区范围的、由小型文本文档组成的集合，能够在会话之间持久保存。当存储被附加到会话（通过 `resources[]`）时，它会被挂载到容器中作为一个文件系统目录；代理使用普通的文件工具进行读写，系统提示中的一条注释会告知代理挂载点的存在。

每次对记忆的变更都会生成一个不可变的**记忆版本**（`memver_...`），为您提供审计追踪和按时间点回滚/编辑的能力。

## 对象模型

| 对象 | ID 前缀 | 范围 | 说明 |
| --- | --- | --- | --- |
| 记忆存储 | `memstore_...` | 工作区 | 通过 `resources[]` 附加到会话 |
| 记忆 | `mem_...` | 存储 | 一个文本文件，通过 `path` 寻址（每个文件 ≤ 100KB——建议使用多个小文件） |
| 记忆版本 | `memver_...` | 记忆 | 每次变更的不可变快照；`operation` ∈ `created` / `modified` / `deleted` |

## 创建存储

`description` 会传递给代理，以便它知道存储中包含什么内容——请为模型编写，而非为人类编写。

```python
store = client.beta.memory_stores.create(
    name="User Preferences",
    description="Per-user preferences and project context.",
)
print(store.id)  # memstore_01Hx...
```

其他 SDK：TypeScript `client.beta.memoryStores.create({...})`；Go `client.Beta.MemoryStores.New(ctx, ...)`。参见 `shared/managed-agents-api-reference.md` → SDK Method Reference 获取完整的各语言表格。

存储支持 `retrieve` / `update` / `list`（支持 `include_archived`、`created_at_{gte,lte}` 过滤器）/ `delete` / **`archive`**。归档使存储变为只读——已有会话的附件继续保留，但新会话无法引用该存储；不可取消归档。

### 预填充内容（可选）

在任何会话运行之前预加载参考材料。`memories.create` 在给定的 `path` 处创建一个记忆；如果该路径上已存在记忆，则调用返回 `409`（`memory_path_conflict_error`，包含 `conflicting_memory_id`）。存储 ID 是第一个位置参数。

```python
client.beta.memory_stores.memories.create(
    store.id,
    path="/formatting_standards.md",
    content="All reports use GAAP formatting. Dates are ISO-8601...",
)
```

## 附加到会话

记忆存储被放入会话的 `resources[]` 数组中，与 `file` 和 `github_repository` 资源并列（参见 `shared/managed-agents-environments.md` → Resources）。记忆存储仅在**创建会话时**附加——`sessions.resources.add()` 不接受 `memory_store`。

```python
session = client.beta.sessions.create(
    agent=agent.id,
    environment_id=environment.id,
    resources=[
        {
            "type": "memory_store",
            "memory_store_id": store.id,
            "access": "read_write",  # 或 "read_only"；默认为 "read_write"
            "instructions": "User preferences and project context. Check before starting any task.",
        }
    ],
)
```

| 字段 | 必需 | 说明 |
| --- | --- | --- |
| `type` | 是 | `"memory_store"` |
| `memory_store_id` | 是 | `memstore_...` |
| `access` | — | `"read_write"`（默认）或 `"read_only"`——在文件系统层面于挂载点强制执行 |
| `instructions` | — | 针对此存储的会话级指导，作为存储的 `name`/`description` 的补充。≤ 4,096 字符。 |

**每个会话最多 8 个记忆存储。** 当不同记忆片段拥有不同所有者或生命周期时，可附加多个存储——例如，一个只读共享参考存储加一个按用户读写存储，或者共享同一代理配置的每个最终用户/团队/项目各一个存储。

### 代理看到的视图（FUSE 挂载）

每个被附加的存储都会挂载到会话容器的 `/mnt/memory/<store-name>/` 目录下。代理使用标准文件工具（`bash`、`read`、`write`、`edit`、`glob`、`grep`）与之交互——没有专用的记忆工具。`access: "read_only"` 使挂载点在文件系统层面变为只读；`"read_write"` 允许代理在目录下创建、编辑和删除文件。每个挂载点的简短描述（名称、路径、`instructions`、访问权限）会自动注入到系统提示中，因此代理无需您提及就知道该存储的存在。

代理在挂载点下进行的写入会被持久化回存储，并生成记忆版本，就像宿主侧的 `memories.update` 调用一样。

## 直接管理记忆（宿主侧）

用于审查工作流、纠正不良记忆或带外填充存储。

### 列出

返回 `Memory | MemoryPrefix` 条目——`MemoryPrefix`（`type: "memory_prefix"`，仅包含 `path`）是在分层列出时的类似目录的节点。使用 `path_prefix` 限定范围（包括尾部斜杠：`"/notes/"` 匹配 `/notes/a.md` 但不匹配 `/notes_backup/old.md`），使用 `depth` 限制树遍历深度。`order_by` / `order` 对结果排序。传入 `view="full"` 以包含每个条目的 `content`；默认的 `"basic"` 仅返回元数据。

```python
for m in client.beta.memory_stores.memories.list(store.id, path_prefix="/"):
    if m.type == "memory":
        print(f"{m.path}  ({m.content_size_bytes} bytes, sha={m.content_sha256[:8]})")
    else:  # "memory_prefix"
        print(f"{m.path}/")
```

### 读取

```python
mem = client.beta.memory_stores.memories.retrieve(memory_id, memory_store_id=store.id)
print(mem.content)
```

`retrieve` 默认 `view="full"`（包含内容）；`view` 主要在列表端点上起作用。

### 创建与更新

| 操作 | 寻址方式 | 语义 |
| --- | --- | --- |
| `memories.create(store_id, path=..., content=...)` | **Path** | 在 `path` 处创建。如果路径已被占用，返回 `409`（`memory_path_conflict_error`，包含 `conflicting_memory_id`）。 |
| `memories.update(mem_id, memory_store_id=..., path=..., content=...)` | **`mem_...` ID** | 变更已有记忆。可更改 `content`、`path`（重命名）或两者。重命名到已被占用的路径时返回同样的 `409 memory_path_conflict_error`。 |

```python
mem = client.beta.memory_stores.memories.create(
    store.id,
    path="/preferences/formatting.md",
    content="Always use tabs, not spaces.",
)

client.beta.memory_stores.memories.update(
    mem.id,
    memory_store_id=store.id,
    path="/archive/2026_q1_formatting.md",  # 重命名
)
```

### 乐观并发控制（`update` 的前提条件）

`memories.update` 接受 `precondition` 参数，使您可以执行读取→修改→写回操作而不覆盖并发写入。唯一支持的类型是 `content_sha256`。不匹配时 API 返回 `409`（`memory_precondition_failed_error`）——请重新读取并基于最新状态重试。

```python
client.beta.memory_stores.memories.update(
    mem.id,
    memory_store_id=store.id,
    content="CORRECTED: Always use 2-space indentation.",
    precondition={"type": "content_sha256", "content_sha256": mem.content_sha256},
)
```

### 删除

```python
client.beta.memory_stores.memories.delete(mem.id, memory_store_id=store.id)
```

传入 `expected_content_sha256` 可实现条件删除。

## 审计与回滚——记忆版本

每次变更都会创建一个不可变的 `memver_...` 快照。版本在父级记忆的整个生命周期中累积；`memories.retrieve` 始终返回当前头版本，版本端点则提供历史记录。

| 触发变更的操作 | 版本上的 `operation` 字段 |
| --- | --- |
| 在新路径上执行 `memories.create` | `"created"` |
| 通过 `memories.update` 更改 `content`、`path` 或两者（或代理侧向挂载点写入） | `"modified"` |
| `memories.delete` | `"deleted"` |

每个版本还会记录 `created_by`——一个 `type` ∈ `session_actor` / `api_actor` / `user_actor` 的执行者对象——以及在编辑后记录 `redacted_at` + `redacted_by`。

### 列出版本

最新的在前，分页返回。可按 `memory_id`、`operation`、`session_id`、`api_key_id` 或 `created_at_gte` / `created_at_lte` 进行筛选。传入 `view="full"` 以包含 `content`；默认为仅元数据。

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

### 编辑版本

从历史版本中擦除内容，同时保留审计追踪（执行者 + 时间戳）。清除 `content`、`content_sha256`、`content_size_bytes` 和 `path`；其余所有字段保持不变。用于泄漏的密钥、个人身份信息 (PII) 或用户删除请求。

```python
client.beta.memory_stores.memory_versions.redact(version_id, memory_store_id=store.id)
```

## 端点参考

参见 `shared/managed-agents-api-reference.md` → Memory Stores / Memories / Memory Versions 获取完整的 HTTP 方法/路径表。原始 HTTP 基础路径：

```
POST   /v1/memory_stores
POST   /v1/memory_stores/{memory_store_id}/archive
GET    /v1/memory_stores/{memory_store_id}/memories
PATCH  /v1/memory_stores/{memory_store_id}/memories/{memory_id}
GET    /v1/memory_stores/{memory_store_id}/memory_versions
POST   /v1/memory_stores/{memory_store_id}/memory_versions/{version_id}/redact
```

有关 cURL 示例和 CLI（`ant beta:memory-stores ...`），请通过 WebFetch 获取 `shared/live-sources.md` → Managed Agents 中的 Memory URL。
