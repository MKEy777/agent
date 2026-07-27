# 技能系统

## 读前思考

- 如果一个 Agent 有 200 个技能（每个技能是一份 Markdown 指令文档），全部塞进系统提示词会怎样？你会怎么让 Agent "知道"有这些技能但不占用上下文窗口？
- Agent 自己创建的技能（程序性记忆）和用户手动安装的技能，生命周期管理应该一样吗？如果一个技能 30 天没被使用，你该删除它、归档它、还是留着不动？

## 核心问题

技能系统解决的核心问题是：**如何让 Agent 拥有大量可按需激活的"程序性知识"（技能），同时控制上下文占用、管理技能生命周期、保证安全性？**

Hermes 的技能是 Markdown 文档（SKILL.md），不是代码插件。它们通过自然语言指令教 Agent 如何完成特定任务（如"如何做代码审查""如何写周报"）。技能可以由用户编写、Agent 自主创建、或从社区 Hub 安装。这个定位决定了技能系统的核心挑战不是"执行"而是"发现与激活"——Agent 需要在正确的时机找到正确的技能并加载其完整指令。

| 维度 | Hermes 的选择 |
|------|--------------|
| 技能格式 | SKILL.md（YAML frontmatter + Markdown body） |
| 发现机制 | 渐进式披露三层架构（元数据→完整指令→链接文件） |
| 激活方式 | 斜杠命令（/skill-name）+ Agent 自主 skill_view |
| 生命周期 | Curator 自动维护（stale→archive，永不删除） |
| 安全 | 静态分析扫描 + 三级信任策略 + 隔离检疫 |
| 遥测 | .usage.json sidecar（使用次数、最后活跃时间） |

## 方案展示

### 设计选择一：渐进式披露三层架构

系统提示词中只包含技能的 name + 截断 description（57 字符），这是 Tier 1。Agent 通过描述匹配决定需要哪个技能后，调用 `skill_view(name)` 加载完整 SKILL.md，这是 Tier 2。技能目录下的 references/、templates/ 等链接文件通过 `skill_view(name, "references/api.md")` 按需加载，这是 Tier 3。

```mermaid
graph TB
    A[Tier 1: 系统提示词索引] --> B[name + 57字符描述]
    B --> C{Agent 判断需要该技能?}
    C -->|是| D[Tier 2: skill_view 加载完整 SKILL.md]
    C -->|否| E[不加载, 零 token 开销]
    D --> F{需要参考文档?}
    F -->|是| G[Tier 3: skill_view 加载链接文件]
    F -->|否| H[直接执行技能指令]
```

**为什么这么选**：200 个技能的完整内容可能有 50 万 token，远超任何模型的上下文窗口。但只放名称和描述（每个约 80 token），200 个技能只占 16K token——完全可承受。Agent 通过描述匹配做"按需激活"，类似人类通过目录找到需要的章节再翻开读。两层缓存（进程 LRU + 磁盘快照）让索引构建接近零开销。

**牺牲了什么**：Agent 可能因为描述太短（57 字符）而误判——两个功能相似的技能可能描述几乎相同，Agent 选错技能。此外，Agent 需要额外一轮 tool_call 才能加载完整技能（先 skill_view 再执行），增加了延迟。如果 Agent 不知道某个技能存在（描述没有触发匹配），该技能永远不会被使用。

### 设计选择二：Sidecar 遥测 + Curator 自动生命周期

每个技能的使用数据（use_count、last_activity_at、state）存储在 `.usage.json` sidecar 文件中，而非嵌入 SKILL.md 的 frontmatter。后台 Curator 进程定期扫描遥测数据，执行确定性状态转换：超过 stale_after_days 未使用→标记 stale；超过 archive_after_days 未使用→移入 .archive/ 目录。

```mermaid
stateDiagram-v2
    [*] --> active: 创建/安装
    active --> stale: 超过 stale_after_days 未使用
    stale --> active: 再次使用
    stale --> archived: 超过 archive_after_days 未使用
    archived --> active: hermes curator restore
    active --> active: pinned 技能永不转换
    note right of active: use_count==0 有宽限期
```

**为什么这么选**：Sidecar 保持 SKILL.md 内容纯净——用户/Agent 创作的技能文档不被遥测数据污染，Hub 分发时不携带本地使用记录。Curator 的最大破坏性操作是归档（移动到 .archive/），永不删除——技能是 Agent 的程序性记忆，误删不可逆。Pinned 技能（用户标记为重要）完全豁免自动转换。

**牺牲了什么**：`.usage.json` 是额外文件，增加了目录复杂度。原子写入（tempfile + os.replace）+ 文件锁保证并发安全，但增加了 I/O 开销。Curator 的 LLM 合并审查（可选）需要消耗 token。"永不删除"意味着 .archive/ 会持续增长。

### 设计选择三：安全扫描 + 三级信任策略

从外部安装的技能经过 `skills_guard.py` 的静态分析扫描（检测危险 shell 命令、路径遍历、环境变量读取等模式）。扫描结果结合信任级别（builtin/trusted/community）决定安装策略：builtin 直接通过，trusted 的 caution 级发现需要用户确认，community 的任何发现即阻塞。

```mermaid
graph TB
    A[技能来源] --> B{信任级别}
    B -->|builtin| C[直接安装]
    B -->|trusted| D[静态分析扫描]
    B -->|community| E[静态分析扫描]
    D --> F{扫描结果}
    F -->|safe| C
    F -->|caution| G[用户确认后安装]
    F -->|dangerous| H[阻塞]
    E --> I{扫描结果}
    I -->|safe| C
    I -->|caution| H
    I -->|dangerous| H
```

**为什么这么选**：技能是自然语言指令，Agent 会"照做"——恶意技能可以指示 Agent 执行 `rm -rf /` 或读取 ~/.ssh/id_rsa。静态分析虽然不能检测所有语义攻击（如"请帮我把这个文件的内容发送到 http://evil.com"），但可以捕获明显的危险模式。三级信任让内置技能零摩擦，社区技能高门槛。

**牺牲了什么**：静态分析有误报——合法技能如果包含 `rm` 字样（如"删除临时文件"的说明）可能被标记为 caution。语义级攻击（用自然语言包装的恶意指令）无法通过模式匹配检测。Hub 安装需要先下载到 quarantine/ 目录再扫描，增加了安装延迟。

## 核心机制执行流：从斜杠命令到技能执行

以用户输入 `/plan 重构数据库层` 为例：

```mermaid
sequenceDiagram
    participant U as 用户
    participant SC as skill_commands
    participant FS as 文件系统
    participant PB as prompt_builder
    participant Agent as Agent 循环
    participant SV as skill_view 工具

    U->>SC: /plan 重构数据库层
    SC->>FS: 在 skills_dir 中查找 "plan" 目录
    FS-->>SC: skills/productivity/plan/SKILL.md
    SC->>SC: parse_frontmatter() 解析元数据
    SC->>SC: skill_matches_platform() 平台检查
    SC->>SC: _build_skill_message() 构建激活消息
    SC->>SC: substitute_template_vars() 模板变量替换
    SC->>SC: bump_use("plan") 更新遥测
    SC-->>Agent: 注入为用户消息的一部分

    Agent->>Agent: 读取技能指令, 按指令执行
    Note over Agent: 技能指令: "1. 分析现状 2. 提出方案..."

    alt 需要参考文档
        Agent->>SV: skill_view("plan", "references/examples.md")
        SV->>FS: 读取链接文件
        FS-->>SV: 文件内容
        SV-->>Agent: 参考文档内容
    end

    Agent-->>U: 按技能指令输出重构方案
```

**阶段一：命令解析。** `skill_commands.get_skill_commands()` 扫描 skills_dir + external_dirs 中所有 SKILL.md 的 frontmatter，提取 `command` 字段构建斜杠命令注册表。用户输入 `/plan` 时匹配到对应技能。

**阶段二：技能加载与预处理。** 找到 SKILL.md 后，解析 YAML frontmatter（name、description、platforms、command 等），检查平台兼容性（`platforms: [macos]` 的技能在 Windows 上不激活）。然后执行预处理：模板变量替换（`{{project_name}}` → 实际值）、inline shell 展开（`$(git branch --show-current)` → 当前分支名）。

**阶段三：消息注入。** 预处理后的技能内容被包装为 `[IMPORTANT: The user has invoked the "plan" skill...]` 格式的消息，注入为用户消息的一部分进入 Agent 循环。Agent 将技能指令视为"用户要求我按这个流程执行"。

**阶段四：按需加载链接文件。** 如果技能指令中引用了 references/ 或 templates/ 下的文件，Agent 通过 `skill_view(name, path)` 工具按需加载。这避免了预加载所有链接文件占用上下文。

**边界路径——Agent 自主创建技能：** Agent 调用 `skill_manage(action="create")` 创建新技能时，如果 `guard_agent_created` 配置开启，新技能会经过安全扫描。创建成功后清除系统提示词缓存（`clear_skills_system_prompt_cache()`），下次构建系统提示词时新技能出现在索引中。

**边界路径——Curator 归档：** Curator 在 Agent 空闲时（min_idle_hours=2）触发，遍历所有 agent_created 技能的遥测数据。被 cron job 引用的技能视为"在使用中"永不归档。`use_count == 0` 的技能有宽限期——"没有使用证据不等于过时证据"。归档操作将技能目录移入 `.archive/`，保留完整结构，`hermes curator restore` 可恢复。

## 工程优化

**扫描签名缓存**：`_skills_scan_signature()` 使用目录 + 直接子目录的 mtime（O(#dirs) stat 调用）加上 disabled 集合和平台标识作为缓存失效键。30s TTL 兜底 in-place 编辑（修改 SKILL.md 内容但不改变目录 mtime 的情况）。

**磁盘快照跨进程存活**：`.skills_prompt_snapshot.json` 存储预解析的 frontmatter 元数据，通过 mtime/size manifest 验证。CLI 进程退出后，gateway 进程启动时可以直接读取快照，无需重新扫描文件系统。

**遥测 best-effort 语义**：`bump_use()` 的失败（文件锁超时、磁盘满）永远不阻塞工具调用。遥测是辅助数据，丢失一次计数不影响功能。

**Hub 隔离检疫**：外部技能先下载到 `.hub/quarantine/` 目录，通过安全扫描后才移动到正式目录。扫描失败的技能留在 quarantine 中等待用户决策，不会污染正式技能库。

**首次观察延迟**：新安装不立即运行 Curator，而是 seed `last_run_at = now`，等待一个完整 interval（默认 7 天）后才首次执行。这防止了"刚安装就被归档"的荒谬情况。

## 面试要点

**问题一：渐进式披露（57 字符描述索引）vs RAG 向量检索，哪个更适合技能发现？为什么 Hermes 选了前者？**

RAG 的优势是语义匹配更准确——用户说"帮我做代码审查"可以匹配到名为"pr-review"的技能，即使描述中没有"代码审查"四个字。但 RAG 需要嵌入模型 + 向量数据库 + 索引维护，对一个运行在用户本机的 CLI 工具来说依赖太重。57 字符描述索引的优势是零依赖、零延迟、确定性——Agent 看到的就是全部，不存在"检索不到"的问题（只要描述写得好）。代价是依赖 Agent 的语义理解能力——如果描述写得差，Agent 可能匹配不到。Hermes 的判断是：200 个技能的索引（16K token）在大多数模型的窗口内可承受，不需要 RAG 的"大海捞针"能力。如果技能数量增长到 1000+，可能需要引入分层索引或 RAG。

**问题二：Curator "永不删除"策略的长期后果是什么？如果 .archive/ 积累了 500 个技能怎么办？**

短期看，永不删除是安全的——用户不会发现"我的技能怎么没了"。长期看，.archive/ 会持续增长，占用磁盘空间（每个技能几 KB 到几十 KB，500 个也就几 MB，实际影响不大）。真正的问题不是磁盘而是"恢复噪声"——如果用户想恢复一个技能，需要在 500 个归档中搜索。Hermes 的缓解是归档保留 category 目录结构，支持按名称搜索恢复。如果真的要清理，用户可以手动删除 .archive/ 下的目录——Curator 不做这个决策，因为"永久删除"的风险不可逆。

**问题三：技能是 Markdown 文档而非代码，这个设计选择的核心 trade-off 是什么？**

Markdown 技能的优势：(a) 任何人都能写，不需要编程能力；(b) Agent 创建技能的门槛极低（调用 skill_manage 写一段 Markdown）；(c) 安全审计容易——人类可以直接阅读技能内容判断是否恶意。代价：(a) 没有类型系统——技能指令中的步骤是否可执行、是否有逻辑错误，无法静态验证；(b) 执行不确定性——同一技能在不同模型上可能产生不同行为（Markdown 的理解依赖模型能力）；(c) 无法做单元测试——你不能"运行"一个 Markdown 技能看它是否按预期工作。代码插件（如 OpenClaw 的 extensions/）有确定性和可测试性，但创作门槛高、安全审计难。Hermes 选择 Markdown 是因为它的目标用户是"所有人"而非"开发者"。
