# Files API — TypeScript

Files API 上传文件以供在 Messages API 请求中使用。通过内容块中的 `file_id` 引用文件，避免在多个 API 调用中重复上传。

**Beta：** 在 API 调用中传递 `betas: ["files-api-2025-04-14"]`（SDK 会自动设置所需的请求头）。

## 关键信息

- 最大文件大小：500 MB
- 总存储空间：每个组织 100 GB
- 文件在删除前持续保留
- 文件操作（上传、列出、删除）免费；消息中使用的内容按输入 token 计费
- 在 Amazon Bedrock 或 Google Vertex AI 上不可用

---

## 上传文件

```typescript
import Anthropic, { toFile } from "@anthropic-ai/sdk";
import fs from "fs";

const client = new Anthropic();

const uploaded = await client.beta.files.upload({
  file: await toFile(fs.createReadStream("report.pdf"), undefined, {
    type: "application/pdf",
  }),
  betas: ["files-api-2025-04-14"],
});

console.log(`File ID: ${uploaded.id}`);
console.log(`Size: ${uploaded.size_bytes} bytes`);
```

---

## 在消息中使用文件

### PDF / 文本文档

```typescript
const response = await client.beta.messages.create({
  model: "claude-opus-4-8",
  max_tokens: 16000,
  messages: [
    {
      role: "user",
      content: [
        { type: "text", text: "Summarize the key findings in this report." },
        {
          type: "document",
          source: { type: "file", file_id: uploaded.id },
          title: "Q4 Report",
          citations: { enabled: true },
        },
      ],
    },
  ],
  betas: ["files-api-2025-04-14"],
});

console.log(response.content[0].text);
```

---

## 管理文件

### 列出文件

```typescript
const files = await client.beta.files.list({
  betas: ["files-api-2025-04-14"],
});
for (const f of files.data) {
  console.log(`${f.id}: ${f.filename} (${f.size_bytes} bytes)`);
}
```

### 删除文件

```typescript
await client.beta.files.delete("file_011CNha8iCJcU1wXNR6q4V8w", {
  betas: ["files-api-2025-04-14"],
});
```

### 下载文件

```typescript
const response = await client.beta.files.download(
  "file_011CNha8iCJcU1wXNR6q4V8w",
  { betas: ["files-api-2025-04-14"] },
);
const content = Buffer.from(await response.arrayBuffer());
await fs.promises.writeFile("output.txt", content);
```
