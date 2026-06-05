# Managed Agents — PHP

> **此处未展示的绑定：** 本 README 涵盖了 PHP 最常见的 managed-agents 流程。如果你需要某个未在此展示的类、方法、命名空间、字段或行为，请从 `shared/live-sources.md` 中 WebFetch PHP SDK 仓库**或相关文档页面**，而不是自行猜测。不要根据 cURL 结构或其他语言的 SDK 进行推断。

> **Agent 是持久化的——创建一次，通过 ID 引用。** 存储 `$client->beta->agents->create` 返回的 agent ID，并将其传递给每次后续的 `->sessions->create`；不要在请求路径中调用 `agents->create`。Anthropic CLI 是一种从版本控制的 YAML 创建 agent 和环境的便捷方式——其 URL 见 `shared/live-sources.md`。以下示例为完整起见展示了在代码中创建；在生产环境中，create 调用应属于设置阶段，而非请求路径。

## 安装

```bash
composer require "anthropic-ai/sdk"
```

## 客户端初始化

```php
use Anthropic\Client;

// 默认（使用 ANTHROPIC_API_KEY 环境变量）
$client = new Client();

// 显式指定 API key
$client = new Client(apiKey: 'your-api-key');
```

---

## 创建环境

```php
$environment = $client->beta->environments->create(
    name: 'my-dev-env',
    config: ['type' => 'cloud', 'networking' => ['type' => 'unrestricted']],
);
echo "Environment ID: {$environment->id}\n"; // env_...
```

---

## 创建 Agent（必需的第一步）

> ⚠️ **没有内联 agent 配置。** `model`/`system`/`tools` 位于 agent 对象上，而非 session。始终以 `$client->beta->agents->create()` 开始——session 接受 `agent: $agent->id` 或类型化的 `BetaManagedAgentsAgentParams::with(type: 'agent', id: $agent->id, version: $agent->version)`。

### 最小示例

```php
use Anthropic\Beta\Agents\BetaManagedAgentsAgentToolset20260401Params;

// 1. 创建 agent（可复用，带版本控制）
$agent = $client->beta->agents->create(
    name: 'Coding Assistant',
    model: 'claude-opus-4-8',
    system: 'You are a helpful coding assistant.',
    tools: [
        BetaManagedAgentsAgentToolset20260401Params::with(
            type: 'agent_toolset_20260401',
        ),
    ],
);

// 2. 启动 session
$session = $client->beta->sessions->create(
    agent: ['type' => 'agent', 'id' => $agent->id, 'version' => $agent->version],
    environmentID: $environment->id,
    title: 'Quickstart session',
);
echo "Session ID: {$session->id}\n";
```

### 更新 Agent

更新会创建新版本；agent 对象在每个版本上是不可变的。

```php
$updatedAgent = $client->beta->agents->update(
    $agent->id,
    version: $agent->version,
    system: 'You are a helpful coding agent. Always write tests.',
);
echo "New version: {$updatedAgent->version}\n";

// 列出所有版本
foreach ($client->beta->agents->versions->list($agent->id)->pagingEachItem() as $version) {
    echo "Version {$version->version}: {$version->updatedAt->format(DateTimeInterface::ATOM)}\n";
}

// 归档 agent
$archived = $client->beta->agents->archive($agent->id);
echo "Archived at: {$archived->archivedAt->format(DateTimeInterface::ATOM)}\n";
```

---

## 发送用户消息

```php
$client->beta->sessions->events->send(
    $session->id,
    events: [
        [
            'type' => 'user.message',
            'content' => [['type' => 'text', 'text' => 'Review the auth module']],
        ],
    ],
);
```

> 💡 **流式优先：** 在发送消息*之前*（或同时）打开流。流只传递打开之后发生的事件——先发送后流式意味着早期事件会以缓冲批次到达。参见 [Steering Patterns](../../shared/managed-agents-events.md#steering-patterns)。

---

## 流式事件（SSE）

> ℹ️ **流式传输器：** PHP 默认的缓冲 PSR-18 客户端对于开放式 session 事件流永远不会返回。对于 `streamStream()` 调用，请使用流式 Guzzle 传输器——其他调用则保留默认客户端。

```php
$streamingClient = new GuzzleHttp\Client(['stream' => true]);

// 先打开流，再发送用户消息
$stream = $client->beta->sessions->events->streamStream(
    $session->id,
    requestOptions: ['transporter' => $streamingClient],
);
$client->beta->sessions->events->send(
    $session->id,
    events: [
        [
            'type' => 'user.message',
            'content' => [['type' => 'text', 'text' => 'Summarize the repo README']],
        ],
    ],
);

foreach ($stream as $event) {
    match ($event->type) {
        'agent.message' => array_walk(
            $event->content,
            static fn($block) => $block->type === 'text' ? print($block->text) : null,
        ),
        'agent.tool_use' => print("\n[Using tool: {$event->name}]\n"),
        'session.error' => printf("\n[Error: %s]", $event->error?->message ?? 'unknown'),
        default => null,
    };
    if ($event->type === 'session.status_idle' || $event->type === 'session.error') {
        break;
    }
}
$stream->close();
```

### 重新连接与尾部跟踪

在 session 中途重新连接时，先列出过去的事件以去重，然后跟踪实时事件：

```php
$stream = $client->beta->sessions->events->streamStream(
    $session->id,
    requestOptions: ['transporter' => $streamingClient],
);

// 流已打开并缓冲。在跟踪实时事件之前先列出历史记录。
$seenEventIds = [];
foreach ($client->beta->sessions->events->list($session->id)->pagingEachItem() as $event) {
    $seenEventIds[$event->id] = true;
}

// 跟踪实时事件，跳过已见过的
foreach ($stream as $event) {
    if (isset($seenEventIds[$event->id])) {
        continue;
    }
    $seenEventIds[$event->id] = true;
    match ($event->type) {
        'agent.message' => array_walk(
            $event->content,
            static fn($block) => $block->type === 'text' ? print($block->text) : null,
        ),
        default => null,
    };
    if ($event->type === 'session.status_idle') {
        break;
    }
}
$stream->close();
```

---

## 提供自定义工具结果

> ℹ️ 用于 `user.custom_tool_result` 的 PHP managed-agents 绑定尚未在此 skill 或 apps 源码示例中记录。请参阅 `shared/managed-agents-events.md` 了解 wire 格式，并参考 `anthropic-ai/sdk` PHP 仓库了解相应的参数。

---

## 轮询事件

```php
foreach ($client->beta->sessions->events->list($session->id)->pagingEachItem() as $event) {
    echo "{$event->type}: {$event->id}\n";
}
```

---

## 上传文件

> ℹ️ **PHP 文件上传：** PHP SDK 的 beta managed-agents 文件上传绑定未在 apps 源码示例中展示；规范的 PHP 示例使用原始 cURL 调用 `POST /v1/files`。如果你的代码库更倾向于使用 SDK，请在编写代码前 WebFetch `anthropic-ai/sdk` PHP 仓库以获取最新的绑定。

```php
use Anthropic\Beta\Sessions\BetaManagedAgentsFileResourceParams;

// 原始 cURL 上传（来自 apps 源码的规范示例）
$csvPath = 'data.csv';
$ch = curl_init('https://api.anthropic.com/v1/files');
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST => true,
    CURLOPT_HTTPHEADER => [
        'x-api-key: ' . getenv('ANTHROPIC_API_KEY'),
        'anthropic-version: 2023-06-01',
        'anthropic-beta: files-api-2025-04-14',
    ],
    CURLOPT_POSTFIELDS => ['file' => new CURLFile($csvPath, 'text/csv', 'data.csv')],
]);
$file = json_decode(curl_exec($ch));
echo "File ID: {$file->id}\n";

// 挂载到 session
$session = $client->beta->sessions->create(
    agent: $agent->id,
    environmentID: $environment->id,
    resources: [
        BetaManagedAgentsFileResourceParams::with(
            type: 'file',
            fileID: $file->id,
            mountPath: '/workspace/data.csv',
        ),
    ],
);
```

### 在现有 Session 上添加和管理资源

```php
// 向打开的 session 附加一个文件
$resource = $client->beta->sessions->resources->add(
    $session->id,
    type: 'file',
    fileID: $file->id,
);
echo "{$resource->id}\n"; // "sesrsc_01ABC..."

// 列出 session 上的资源
$listed = $client->beta->sessions->resources->list($session->id);
foreach ($listed->data as $entry) {
    echo "{$entry->id} {$entry->type}\n";
}

// 分离资源
$client->beta->sessions->resources->delete($resource->id, sessionID: $session->id);
```

---

## 列出和下载 Session 文件

> ℹ️ 列出和下载 agent 在 session 期间写入的文件尚未在此 skill 或 apps 源码示例中针对 PHP 进行记录。请参见 `shared/managed-agents-events.md` 和 `anthropic-ai/sdk` PHP 仓库了解文件列表/下载绑定。

---

## Session 管理

```php
// 列出环境
$environments = $client->beta->environments->list();

// 获取特定环境
$env = $client->beta->environments->retrieve($environment->id);

// 归档环境（只读，现有 session 继续运行）
$client->beta->environments->archive($environment->id);

// 删除环境（仅当没有 session 引用它时）
$client->beta->environments->delete($environment->id);

// 删除 session
$client->beta->sessions->delete($session->id);
```

---

## MCP 服务器集成

```php
use Anthropic\Beta\Agents\BetaManagedAgentsAgentToolset20260401Params;
use Anthropic\Beta\Agents\BetaManagedAgentsMCPToolsetParams;
use Anthropic\Beta\Agents\BetaManagedAgentsUrlmcpServerParams;
use Anthropic\Beta\Sessions\BetaManagedAgentsAgentParams;

// Agent 声明 MCP 服务器（此处不涉及认证——认证放在 vault 中）
$agent = $client->beta->agents->create(
    name: 'GitHub Assistant',
    model: 'claude-opus-4-8',
    mcpServers: [
        BetaManagedAgentsUrlmcpServerParams::with(
            type: 'url',
            name: 'github',
            url: 'https://api.githubcopilot.com/mcp/',
        ),
    ],
    tools: [
        BetaManagedAgentsAgentToolset20260401Params::with(type: 'agent_toolset_20260401'),
        BetaManagedAgentsMCPToolsetParams::with(
            type: 'mcp_toolset',
            mcpServerName: 'github',
        ),
    ],
);

// Session 附加包含这些 MCP 服务器 URL 凭证的 vault
$session = $client->beta->sessions->create(
    agent: BetaManagedAgentsAgentParams::with(
        type: 'agent',
        id: $agent->id,
        version: $agent->version,
    ),
    environmentID: $environment->id,
    vaultIDs: [$vault->id],
);
```

参见 `shared/managed-agents-tools.md` 第 §Vaults 节，了解创建 vault 和添加凭证的方法。

---

## Vaults

```php
// 创建 vault
$vault = $client->beta->vaults->create(
    displayName: 'Alice',
    metadata: ['external_user_id' => 'usr_abc123'],
);
echo $vault->id . "\n"; // "vlt_01ABC..."

// 添加 OAuth 凭证
$credential = $client->beta->vaults->credentials->create(
    vaultID: $vault->id,
    displayName: "Alice's Slack",
    auth: [
        'type' => 'mcp_oauth',
        'mcp_server_url' => 'https://mcp.slack.com/mcp',
        'access_token' => 'xoxp-...',
        'expires_at' => '2026-04-15T00:00:00Z',
        'refresh' => [
            'token_endpoint' => 'https://slack.com/api/oauth.v2.access',
            'client_id' => '1234567890.0987654321',
            'scope' => 'channels:read chat:write',
            'refresh_token' => 'xoxe-1-...',
            'token_endpoint_auth' => [
                'type' => 'client_secret_post',
                'client_secret' => 'abc123...',
            ],
        ],
    ],
);

// 轮换凭证（例如，在 token 刷新后）
$client->beta->vaults->credentials->update(
    $credential->id,
    vaultID: $vault->id,
    auth: [
        'type' => 'mcp_oauth',
        'access_token' => 'xoxp-new-...',
        'expires_at' => '2026-05-15T00:00:00Z',
        'refresh' => ['refresh_token' => 'xoxe-1-new-...'],
    ],
);

// 归档 vault
$client->beta->vaults->archive($vault->id);
```

---

## GitHub 仓库集成

将 GitHub 仓库挂载为 session 资源（vault 持有 GitHub MCP 凭证）：

```php
$session = $client->beta->sessions->create(
    agent: $agent->id,
    environmentID: $environment->id,
    vaultIDs: [$vault->id],
    resources: [
        [
            'type' => 'github_repository',
            'url' => 'https://github.com/org/repo',
            'mountPath' => '/workspace/repo',
            'authorizationToken' => 'ghp_your_github_token',
        ],
    ],
);
```

同一 session 上的多个仓库：

```php
$resources = [
    [
        'type' => 'github_repository',
        'url' => 'https://github.com/org/frontend',
        'mountPath' => '/workspace/frontend',
        'authorizationToken' => 'ghp_your_github_token',
    ],
    [
        'type' => 'github_repository',
        'url' => 'https://github.com/org/backend',
        'mountPath' => '/workspace/backend',
        'authorizationToken' => 'ghp_your_github_token',
    ],
];
```

轮换仓库的授权 token：

```php
$listed = $client->beta->sessions->resources->list($session->id);
$repoResourceId = $listed->data[0]->id;

$client->beta->sessions->resources->update(
    $repoResourceId,
    sessionID: $session->id,
    authorizationToken: 'ghp_your_new_github_token',
);
```
