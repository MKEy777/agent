# 记忆系统

## 读前思考

- 大多数 Agent 在对话结束后就忘掉一切。如果要实现跨 session 的长期记忆，你会怎么从对话中提取"值得记住"的信息？用规则匹配（"记住我喜欢 Python"）还是用 LLM 语义分析？前者只能捕获显式标记，后者每轮都要额外花一次 API 调用。
- 记忆提取后存在哪里、怎么检索、何时注入？如果全部塞进 system prompt 会占满上下文，如果完全不加载又等于没记。四个项目在"记住一切"和"不浪费 token"之间走了不同的路——有的用冻结快照换 prompt cache 命中率，有的用三阶段"做梦"模拟人类睡眠记忆整合。

## 核心问题

记忆系统解决的核心问题是：**如何从对话中自动提取持久化事实，跨 session 精准检索并注入 Agent 上下文，同时处理去重、冲突、容量管理和 token 成本控制。**

| 维度 | deer-flow | hermes-agent | openclaw-TS | claudecode |
|------|-----------|--------------|-------------|------------|
| 提取方式 | 防抖队列 + LLM（信号检测） | 对话后异步 LLM | 对话中产生 + 做梦整合 | 后台 LLM + 四类分类 |
| 存储后端 | 文件系统（memory.json + facts/） | FTS5 SQLite（默认）+ 向量（可选） | SQLite + FTS5 + 向量 / QMD | 文件系统（.md 文件） |
| 检索方式 | tiktoken 预算截断 | FTS5 BM25 + 实时工具查询 | FTS5 + 向量混合排序 | MEMORY.md 索引注入 |
| 注入时机 | 中间件 before_agent | 冻结快照 + 实时查询 | 检索后注入 prompt | system prompt 索引 |
| 生命周期 | 容量上限 100 条 | 无自动过期 | 三阶段做梦整合 | 无自动过期 |
| 并发控制 | 防抖窗口 30s | SQLite WAL | cron 调度 | Coalescing 状态机 |

## 方案展示

### deer-flow：防抖队列 + 信号检测 + 分层存储

deer-flow 的记忆提取不是立即处理，而是入队后 30 秒防抖批量处理。入队前检测纠正信号（用户说"不对""我改主意了"）和强化信号（"对""没错"），这些信号传递给 LLM 提取器以提高事实更新精度——如果用户纠正了之前的偏好，提取器知道要覆盖旧事实而非新建。

存储分两层：memory.json 是用户级摘要（跨 agent 共享），facts/ 是 per-agent 的 canonical Markdown 文件（每个事实一个文件，SHA-256 分片）。注入时 tiktoken 精确计算 2000 token 预算，guaranteed_categories（如 correction）优先保证配额。

关键协调点：当 SummarizationMiddleware 准备压缩旧消息时，memory_flush_hook 先调用 add_nowait() 绕过防抖立即入队，确保即将被摘要删除的对话不丢失。

```mermaid
sequenceDiagram
    participant Agent as Agent 完成
    participant Queue as 防抖队列 30s
    participant LLM as 提取 LLM
    participant Storage as 文件存储

    Agent->>Queue: add(messages) + 信号检测
    Note over Queue: 30秒防抖窗口
    Queue->>LLM: 批量提取事实(含信号标注)
    LLM-->>Queue: 事实列表 + 置信度
    Queue->>Queue: 去重 + 合并(偏好变更覆盖)
    Queue->>Storage: 原子写入 memory.json + facts/
```

**为什么这么选**：防抖批量处理降低了 LLM 调用频率（30 秒内多轮对话合并为一次提取）。信号检测让偏好变更能被正确识别（"我转到 Rust 了"覆盖"我喜欢 Python"）。代价是 30 秒内的提取延迟，以及 LLM 提取的 API 成本。

### hermes-agent：冻结快照 + 异步提取 + FTS5

hermes-agent 的记忆通过两个通道进入 Agent 感知：系统提示词中的冻结快照（对话开始时检索 top-N 相关记忆注入，整个会话期间不变）和 memory_tool 实时查询（Agent 随时可以搜索/写入记忆）。冻结的核心收益是 prompt cache 命中率——Anthropic 的 cache 节省 90% 输入 token 计费。

提取在 turn 结束后由辅助 LLM 异步完成，不影响响应速度。存储默认 FTS5 SQLite（零依赖、确定性），可选向量数据库做语义检索。FTS5 的 BM25 排序对关键词匹配场景效果已经很好，个人助手场景的记忆通常几百到几千条。

```mermaid
graph TB
    A[对话开始] --> B[检索 top-N 相关记忆]
    B --> C[注入系统提示词 - 冻结快照]
    C --> D[会话进行中]
    D --> E{Agent 需要更多记忆?}
    E -->|是| F[memory_tool 实时查询]
    E -->|否| G[继续对话]
    D --> H{发现值得记住的?}
    H -->|是| I[memory_tool 写入]
    I --> J[下次对话可见]
```

**为什么这么选**：冻结快照保证了 prefix cache 命中（节省 90% 输入 token 计费），对高频使用的个人助手是显著的成本差异。FTS5 零依赖（SQLite 随 Python 标准库），确定性（相同查询总是返回相同结果）。代价是会话中写入的新记忆不出现在系统提示词中（最终一致性），FTS5 对语义相似但关键词不同的查询效果差。

### openclaw-TS：三阶段"做梦" + 混合检索

openclaw TS 版的核心创新是模拟人类睡眠记忆整合的三阶段"做梦"机制：Light Dreaming（每 6 小时）去重近期记忆（相似度 0.9 合并）；Deep Dreaming（每日凌晨 3 点）提升高频召回的短期记忆为持久记忆（recallCount≥3 且 score≥0.8）；REM Dreaming（每周）发现跨记忆的模式（minPatternStrength=0.75）。

检索用 FTS5 全文 + 向量嵌入双通道混合排序：FTS5 处理精确关键词匹配（函数名、错误码），向量处理语义匹配（"部署问题"匹配"上线失败"），两路结果按加权分数合并。所有记忆操作追加到 JSONL 审计日志，整个过程可审计可回滚。

Python 版无跨会话记忆，只有上下文压缩（结构化摘要，非聊天摘要）。

```mermaid
stateDiagram-v2
    [*] --> 短期记忆: 对话中产生
    短期记忆 --> Light去重: 每6小时
    Light去重 --> 短期记忆: 合并重复
    短期记忆 --> Deep提升: 每日
    Deep提升 --> 持久记忆: recallCount>=3
    持久记忆 --> REM模式: 每周
    REM模式 --> 模式知识: 跨记忆关联
    短期记忆 --> 淘汰: 长期未召回
```

**为什么这么选**：记忆整合不是删除旧数据——需要判断什么值得保留、什么应该合并、什么模式值得提取。三阶段分离让每阶段有独立的调度频率和质量标准。混合检索解决了"关键词精确但缺语义理解 vs 向量有语义理解但丢精确关键词"的经典矛盾。代价是做梦消耗 LLM token，且做梦期间可能影响服务性能。

### claudecode：后台 LLM 提取 + 项目隔离 + Coalescing

claudecode 每轮对话结束后用一次独立 LLM 调用分析最近对话，按四类分类提取记忆（user/feedback/project/reference）。提取 prompt 同样重要的是"什么不该保存"的负面清单（代码模式、git 历史、调试方案、CLAUDE.md 已有内容）。大多数轮次返回空列表是常态。

记忆按项目隔离（cwd 路径 SHA-256 前 12 字符），以独立 .md 文件存储，MEMORY.md 作为索引注入 system prompt。ExtractionCoordinator 用 coalescing 状态机解决并发：同一时刻只允许一个提取运行，运行期间新轮次只设 dirty 标记，完成后自动检查是否重跑。

没有自动过期机制——记忆一旦保存永远存在。

```mermaid
stateDiagram-v2
    state "空闲" as IDLE
    state "提取中" as RUNNING
    [*] --> IDLE
    IDLE --> RUNNING: request_extraction
    RUNNING --> RUNNING: 新轮次 dirty=True
    RUNNING --> IDLE: 完成 + dirty=False
    RUNNING --> RUNNING: 完成 + dirty=True 重跑
```

**为什么这么选**：LLM 提取能理解语义（隐式偏好、纠正、项目上下文），规则无法覆盖。项目隔离确保 /project-a 的记忆不出现在 /project-b 中。Coalescing 比 debounce 更适合执行时间不确定的场景（LLM 响应 1-30 秒不等）。代价是每轮提取一次 API 调用，且没有过期机制导致索引可能膨胀。

## 横向对比

四个项目在记忆系统上的核心岔路口是**"记忆的整合深度"**：

| 岔路口 | deer-flow | hermes-agent | openclaw-TS | claudecode |
|--------|-----------|--------------|-------------|------------|
| 整合深度 | 去重 + 合并 | 去重 + 写入 | 三阶段做梦 | 无整合 |
| 检索精度 | tiktoken 预算 | FTS5 BM25 | FTS5 + 向量混合 | 索引列表 |
| 注入策略 | 中间件注入 | 冻结快照 | 检索后注入 | system prompt |
| 过期策略 | 容量上限 100 | 无 | 做梦淘汰 | 无 |
| 提取并发 | 30s 防抖 | 异步 | cron 调度 | Coalescing |

```mermaid
graph TB
    A[记忆复杂度] --> B{部署场景}
    B -->|短期 CLI 会话| C[文件存储+索引: claudecode]
    B -->|长期个人助手| D[FTS5+冻结快照: hermes-agent]
    B -->|企业多用户| E[防抖+分层: deer-flow]
    B -->|平台级长期运行| F[做梦+混合检索: openclaw-TS]
```

**冻结 vs 实时**是注入策略的核心权衡。hermes-agent 选择冻结快照（牺牲会话内一致性换 prompt cache 命中率），deer-flow 通过中间件在每轮 before_agent 时重新加载（牺牲 cache 换实时性）。openclaw-TS 在 prompt 中注入检索结果（每次对话开始时检索一次），claudecode 只注入索引（模型需要时通过工具读取完整内容）。选择取决于"prefix cache 节省的 token 成本 vs 记忆实时性对用户体验的影响"。

**记忆整合**是 openclaw-TS 独有的深度设计。其他项目的记忆是"写了就在那里"的平面存在，openclaw-TS 的记忆有从短期到持久的晋升路径和跨记忆的模式发现。这反映了"平台级长期运行"的定位——Agent 服务用户数月甚至数年，不做整合记忆库会变成垃圾堆。

## 面试要点

**1. hermes-agent 的冻结快照（性能优先）和 deer-flow 的每轮重新加载（一致性优先），在什么场景下各自占优？**

参考答案方向：冻结快照在高频短对话场景占优——每次对话只有 5-10 轮，prefix cache 命中节省的 90% 输入 token 计费是显著的成本差异，且短对话中记忆变化的概率低。每轮重新加载在长对话 + 记忆频繁写入场景占优——如果 Agent 在第 5 轮写入了一条关键记忆，第 50 轮需要引用它，冻结快照中看不到（因为是本次会话写入的），每轮重新加载能看到。判断标准是"会话平均轮次 × 记忆写入频率"——乘积小用冻结，乘积大用实时。

**2. openclaw-TS 的三阶段做梦频率（6 小时/每日/每周）如果设错了会怎样？怎么确定正确的频率？**

参考答案方向：Light 频率太低→重复记忆堆积，检索冗余；太高→浪费 LLM token（大多数时候没有新重复）。Deep 频率太高→召回数据不足（minRecallCount=3 一天内难达到），可能把噪声提升为持久记忆；太低→有价值的短期记忆等待太久才被固化。REM 频率太高→模式样本不足，发现不可靠；太低→跨记忆关联迟迟不被发现。确定频率的方法是监控记忆库健康度指标（重复率、召回命中率、模式覆盖率），根据指标调整。openclaw-TS 的 memory health < 0.35 自动触发恢复就是这种自适应的雏形。

**3. claudecode 的记忆没有过期机制，长期使用后索引膨胀怎么办？hermes-agent 和 openclaw-TS 的方案哪个更适合借鉴？**

参考答案方向：hermes-agent 没有自动过期但有 Curator 管理技能（类似机制可以应用于记忆）。openclaw-TS 的做梦淘汰更优雅——Light 去重合并冗余，Deep 只提升高价值记忆，未被提升的短期记忆自然淘汰。借鉴方向：给 claudecode 加一个简单的容量上限（如 deer-flow 的 max_facts=100），超出时按最后访问时间排序删除最旧的。或者借鉴 openclaw-TS 的 recallCount 思路——每次记忆被模型引用时计数，长期未被引用的记忆降级或删除。

