# OpenClaw-Py

OpenClaw-Py 是一个本地 AI Gateway。它把浏览器工作台、飞书机器人、模型供应商和工具调用接在一起，用来观察一条消息从入口到模型、工具、回复的完整执行链路。

当前重点能力：

- 本地 Web 工作台，实时查看运行状态、模型输出、工具调用和消息上下文。
- 飞书机器人私聊和群聊 `@机器人` 文本接入。
- DashScope、OpenAI、Anthropic 模型接入。
- Bocha 网络搜索和公开网页读取。
- 飞书云文档读取、搜索、创建和写入正文。

## 1. 环境要求

- Python 3.11 或更高版本。
- Node.js 18 或更高版本。
- pnpm。
- 至少一个模型 API Key，例如 `DASHSCOPE_API_KEY`。

检查版本：

```bash
python --version
node --version
pnpm --version
```

如果没有 pnpm：

```bash
npm install -g pnpm
```

## 2. 安装依赖

从仓库根目录进入 Python 项目：

```bash
cd openclaw-py
```

安装后端：

```bash
python -m pip install -e ".[dev]"
```

安装前端：

```bash
cd frontend
pnpm install
cd ..
```

## 3. 配置环境变量

复制示例文件：

```bash
cp .env.example .env
```

打开 `.env`，至少填写一个模型 Key：

```text
DASHSCOPE_API_KEY=你的 DashScope Key
```

推荐同时配置 Bocha 搜索：

```text
BOCHA_API_KEY=你的 Bocha Key
```

如果要接飞书，还需要：
具体的申请过程见 [feishurunbook.md](feishurunbook.md)。

```text
FEISHU_APP_ID=你的飞书 App ID
FEISHU_APP_SECRET=你的飞书 App Secret
FEISHU_DOCS_BASE_URL=https://你的企业域名.feishu.cn
OPENCLAW_FEISHU_DOCS_WRITE_ENABLED=true
```

`.env` 会被 Git 忽略，不要把真实密钥提交到仓库。

## 4. 启动后端 Gateway

普通本地启动：

```bash
python -m openclaw.cli.main gateway run --host 127.0.0.1 --port 18789
```

如果要启用飞书长连接配置：

```bash
OPENCLAW_CONFIG_PATH=examples/openclaw.feishu.example.json \
python -m openclaw.cli.main gateway run --host 127.0.0.1 --port 18789
```

看到类似日志说明后端启动成功：

```text
provider_registered
gateway_booted
Uvicorn running on http://127.0.0.1:18789
```

检查接口：

```bash
curl -sS http://127.0.0.1:18789/health
curl -sS http://127.0.0.1:18789/api/models
curl -sS http://127.0.0.1:18789/api/channels/status
```

## 5. 启动前端工作台

另开一个终端：

```bash
cd openclaw-py/frontend
pnpm dev --host 127.0.0.1 --port 3001
```

浏览器打开：

```text
http://127.0.0.1:3001/
```

页面三列含义：

- 左侧：实时会话列表。
- 中间：架构层、执行链路、运行追踪。
- 右侧：最终输出、工具调用详情、当前消息上下文。

## 6. 启动代码走读前端

项目还包含一个面向教学的代码走读页面，用来按链路讲解消息入口、Gateway、Runtime、工具调用和飞书文档写入流程。

如果第 5 步的前端开发服务已经启动，直接打开：

```text
http://127.0.0.1:3001/walkthrough.html
```

也可以单独启动：

```bash
cd openclaw-py/frontend
pnpm dev --host 127.0.0.1 --port 3001
```

生产构建时，`pnpm build` 会同时产出工作台首页和代码走读页：

```text
frontend/dist/index.html
frontend/dist/walkthrough.html
```

## 7. 飞书机器人测试

飞书开放平台需要完成：

1. 创建企业自建应用。
2. 开启机器人能力。
3. 开通消息和文档权限。
4. 使用长连接接收事件。
5. 添加事件 `im.message.receive_v1`。
6. 发布新版本。

启动 Gateway 后，在飞书里给机器人发：

```text
你好，介绍一下你自己
```

创建飞书文档测试：

```text
建一个飞书文档，标题为 OpenClaw 测试，写一段项目说明，最后只回复文档链接
```

联网研究加飞书文档测试：

```text
联网搜索并分析 DeepSeek V4 的技术资料，写一个飞书文档，最后只回复文档链接
```

更详细的飞书配置见 [feishurunbook.md](feishurunbook.md)。

## 8. 常用命令

后端测试：

```bash
pytest
```

后端静态检查：

```bash
python -m ruff check .
python -m mypy backend/src
```

前端构建：

```bash
cd frontend
pnpm build
```

## 9. 项目结构

```text
openclaw-py/
├── backend/src/openclaw/       # Python 后端
│   ├── agents/                 # 模型运行、工具循环、system prompt
│   ├── channels/               # 飞书、WebChat 等消息入口
│   ├── cli/                    # 命令行入口
│   ├── config/                 # 配置加载和环境变量替换
│   ├── contracts/              # Pydantic 协议和配置契约
│   ├── extensions/             # 模型供应商适配
│   ├── gateway/                # FastAPI Gateway 和 WebSocket
│   ├── sessions/               # 会话、transcript、压缩
│   └── tools/                  # 工具注册、策略、内置工具
├── frontend/                   # Vue 运行时工作台和代码走读前端
├── tests/                      # 后端契约和集成测试
├── examples/                   # 示例配置
├── feishurunbook.md            # 飞书配置操作文档
├── .env.example                # 本地环境变量模板
└── pyproject.toml              # Python 包配置
```

## 10. 排查

后端启动但没有模型回复：

- 检查 `.env` 里是否有模型 API Key。
- 检查 `/api/models` 是否返回模型列表。

飞书主动发消息能收到，用户发消息没有回复：

- 检查飞书应用是否发布了最新版本。
- 检查事件订阅是否启用了长连接。
- 检查是否添加了 `im.message.receive_v1`。

飞书文档只返回 ID，没有链接：

- 配置 `FEISHU_DOCS_BASE_URL=https://你的企业域名.feishu.cn`。

网络搜索不稳定：

- 配置 `BOCHA_API_KEY`。
- 搜索后让模型用 `web_fetch` 打开关键来源再写文档。
