# DeepSeek 开发集生成预算与收录适配（2026-10-04）

用户指定 DeepSeek，并授权助手判断费用上限。本轮选择人民币 1 元、最多 30 次请求；仅适用于已有 30 题开发集 pilot，不授权自动扩展或重试。当前真实调用数为 0。

## 配置与预算

- 请求模型：`deepseek-flash`；记录接口实际返回的 `model`，不将别名等同于固定版本。旧实验模型身份不回填。
- 非思考模式：`thinking.type=disabled`，temperature=0.2；最多 4,096 输入 token（含消息封装）、512 输出 token。
- 使用官方高峰、输入缓存全未命中的价格保守估算：输入 2 元/百万 token，输出 8 元/百万 token。
- 30 × (4,096 × 2 + 512 × 8) / 1,000,000 = 0.36864 元；1 元是本轮授权额度。估算不是供应商账单或账户级消费限额。
- 价格依据：[官方价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)；模式依据：[思考模式](https://api-docs.deepseek.com/guides/thinking_mode/)。执行时价格若变化，须重新检查是否仍满足本额度。

旧协议的零费用约束记录的是前阶段。本补充仅为上述 pilot 设置条件预算，不修改旧协议快照和历史 manifest。

## 尚未满足的执行条件

1. 确认当前模型 tokenizer 及消息封装计数，逐条生成绑定完整请求 SHA-256 的 token 检查记录。字符数不能替代 token 数；参考[官方 token 说明](https://api-docs.deepseek.com/zh-cn/quick_start/token_usage/)。
2. 按既定语义规范完成生成前上下文审阅，保留与生成后答案审阅的时序隔离。
3. 将确认后的 tokenizer 身份、审批引用、端点、价格与解码参数绑定到新的运行日志；密钥只传给客户端，不写入配置或日志。

这些条件未满足，因此没有制作声称可以直接执行的完整运行配置，没有调用真实接口。旧 14 题冻结复标材料与结果不变。

### 同日后续：离线 token 预检完成

30 条请求已按官方 V4.1 纯文本消息模板计数，包含起始标记、角色标记与非思考回答前缀：最小 862、最大 1,270、总计 32,701 token。逐条请求哈希和计数见 `results/selective/token-preflight-20261004/token-checks.jsonl`；软件版本、来源及哈希见同目录 manifest。

官方来源固定为 `deepseek-ai/deepseek-recipe` 提交 `8cadfede7063c896b944e7bae05daa3549ae97ea`。下载的 tokenizer SHA-256 与其 V4.1 README 声明一致。当前环境从配置索引与 PyPI 官方索引均未找到可安装的 `deepseek-recipe` wheel；本实现据固定源码核对，仅支持一条 system、一条 user 的纯文本、非思考输入，不支持工具或结构化输出。未完成与官方编译版 renderer 的独立交叉比对。

按本地输入计数加每条 512 输出 token，估算最多 0.188282 元；原 1 元、30 次与 4,096/512 token 额度不变。这不是供应商实测用量，收录时仍须检测用量越界并停止。生成前语义审阅尚未完成，本次接口调用为 0。

复现时将固定提交中的 `static/tokenizers/v41/tokenizer.json` 下载到忽略目录，然后执行：

```powershell
python scripts/check_deepseek_tokens.py --requests results/selective/request-draft-20260930/requests.jsonl --tokenizer .venv/tokenizer-preflight/tokenizer.json --output <新的输出目录>/token-checks.jsonl
```

脚本验证 tokenizer 字节哈希，拒绝不支持的消息结构、重复题号、超额批次和已有输出文件。tokenizer 大文件不纳入本仓库。

## 已实现与边界

`ResponseCollector` 在调用前用 SQLite 事务持久化额度预留；配置、请求和 token 检查绑定哈希。完成的同一请求直接返回已存结果；中断后结果未知的请求禁止自动重试。失败请求同样占用调用与预留额度。SDK 适配器明确 `max_retries=0`。

日志分别记录请求模型与返回模型、用量、耗时、结束原因、保守费用估算和执行错误类型。错误消息原文不入日志。返回用量缺失、越界或模型身份缺失时停止后续收录。供应商单次超报 token 只能事后检测，因此费用保证依赖已验证的输入计数与供应商遵守输出上限。

回放允许系统错误行没有返回模型，但必须保留请求模型；不把系统错误当作模型拒答。成功行仍必须有返回模型，同批成功行的返回模型须一致。开发/测试配置比较分别核对请求配置与已观察到的返回模型。

本地模拟测试覆盖重启去重、中断状态、失败计额、预算与 token 绑定、元数据异常停机、模型身份比较，以及 SDK 单次调用适配。模拟答案不是科研结果。此模块仍需调用方组织前置审阅与 token 预检，不是绕过这些条件的批量执行入口。
