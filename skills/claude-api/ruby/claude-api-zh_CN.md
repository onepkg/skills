# Claude API — Ruby

> **注意：** Ruby SDK 支持 Claude API。工具运行器可通过 `client.beta.messages.tool_runner()` 以测试版形式使用。Agent SDK 尚不适用于 Ruby。

## 安装

```bash
gem install anthropic
```

## 客户端初始化

```ruby
require "anthropic"

# 默认（使用 ANTHROPIC_API_KEY 环境变量）
client = Anthropic::Client.new

# 显式指定 API 密钥
client = Anthropic::Client.new(api_key: "your-api-key")
```

---

## 基础消息请求

```ruby
message = client.messages.create(
  model: :"claude-opus-4-8",
  max_tokens: 16000,
  messages: [
    { role: "user", content: "What is the capital of France?" }
  ]
)
# content is an array of polymorphic block objects (TextBlock, ThinkingBlock,
# ToolUseBlock, ...). .type is a Symbol — compare with :text, not "text".
# .text raises NoMethodError on non-TextBlock entries.
message.content.each do |block|
  puts block.text if block.type == :text
end
```

---

## 流式传输

```ruby
stream = client.messages.stream(
  model: :"claude-opus-4-8",
  max_tokens: 64000,
  messages: [{ role: "user", content: "Write a haiku" }]
)

stream.text.each { |text| print(text) }
```

---

## 工具调用

Ruby SDK 支持通过原始 JSON Schema 定义进行工具调用，同时还提供了测试版的工具运行器用于自动执行工具。

### 工具运行器（测试版）

```ruby
class GetWeatherInput < Anthropic::BaseModel
  required :location, String, doc: "City and state, e.g. San Francisco, CA"
end

class GetWeather < Anthropic::BaseTool
  doc "Get the current weather for a location"

  input_schema GetWeatherInput

  def call(input)
    "The weather in #{input.location} is sunny and 72°F."
  end
end

client.beta.messages.tool_runner(
  model: :"claude-opus-4-8",
  max_tokens: 16000,
  tools: [GetWeather.new],
  messages: [{ role: "user", content: "What's the weather in San Francisco?" }]
).each_message do |message|
  puts message.content
end
```

### 手动循环

工具定义格式和智能体循环模式请参阅[共享的工具调用概念](../shared/tool-use-concepts.md)。

---

## 提示缓存

`system_:`（尾部下划线——避免遮蔽 `Kernel#system`）接受文本块数组；在最后一个块上设置 `cache_control`。可通过 `OrHash` 类型别名使用普通哈希。关于放置模式和静默失效审计清单，请参阅 `shared/prompt-caching.md`。

```ruby
message = client.messages.create(
  model: :"claude-opus-4-8",
  max_tokens: 16000,
  system_: [
    { type: "text", text: long_system_prompt, cache_control: { type: "ephemeral" } }
  ],
  messages: [{ role: "user", content: "Summarize the key points" }]
)
```

对于 1 小时 TTL：`cache_control: { type: "ephemeral", ttl: "1h" }`。`messages.create` 上还有一个顶层 `cache_control:`，会自动放置在最后一个可缓存块上。

通过 `message.usage.cache_creation_input_tokens` / `message.usage.cache_read_input_tokens` 验证缓存命中。
