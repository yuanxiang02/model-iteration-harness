# Model Iteration Harness

为 coding agent 提供可追溯、可恢复、评测受控的模型迭代运行时。

[English](README.md) · [架构设计](docs/architecture.md) · [MVP 范围](docs/mvp.md)

> **当前状态：本地原型 v0.1.0。** 已有可执行 CLI，可运行基线和候选、归档证据、固定评分、做探索性配对比较，并显式应用晋级 patch。macOS 子进程限制已实现；Linux 目前只有明确选择的可信本地模式。尚不具备生产级沙箱或确认性统计保证。

## 运行原型

核心零第三方运行时依赖，支持 Python 3.9+。全部示例建议使用 Python 3.10+；PyTorch 示例可复用另一个已有解释器及其包目录，不会下载或重新安装 PyTorch。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/mih --help
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python examples/run_lightweight.py --task micrograd
.venv/bin/python examples/run_lightweight.py --task torch-lm
```

[完整运行说明](docs/runtime.md)包含实际配置、后台任务、恢复、评分与晋级命令。准备脚本下载固定 commit 和哈希的公开源码；训练期间不调用 LLM。Linux 运行可信示例时需显式指定 `--isolation trusted-local`。

## 解决的问题

Agent 可以修改训练代码，但可靠地迭代模型，还需要解决：

1. **评测受控：** 评测程序、数据划分、指标定义和晋级规则由可信组件管理。
2. **实验隔离：** 每个 patch 独立运行，记录 baseline、parent、配置、日志和产物。
3. **异步执行：** 训练期间由普通程序等待；任务结束或失败后，再触发评测和 agent review。
4. **证据验收：** 候选按预先确定的规则晋级，失败和不确定的实验也保留记录。

## 为什么采用 harness

Harness 负责状态、边界、执行与验收；skill 负责告诉 agent 如何调用这些能力。

项目已有核心运行时和 JSON CLI，Codex 等 agent 可以通过 shell 工具调用。专用 skill 和自动唤醒 controller 尚未实现。执行状态和验收规则不依赖对话上下文或提示词。

## 如何与模型训练解耦

使用者保留现有训练脚本。项目 adapter 声明如何启动训练、查询任务、收集产物和执行推理；可信 evaluator 根据固定评分协议计算结果。

核心框架理解实验生命周期，不要求统一模型结构、loss、checkpoint 格式或 Trainer 类。模型架构变化所需的加载与推理代码，应在受限的候选执行环境运行，不直接获得评分环境的数据和写权限。

## 已实现与边界

- 基线与候选各有独立 worktree；提交前校验修改范围并冻结 patch。
- detached worker 在 agent 调用结束后继续执行，状态落盘，可重连。
- 取消、超时、重复提交保护；worker 丢失但子进程仍活着时标记 orphaned，不重复启动。
- macOS 对训练/推理子进程施加写入、指定路径读取、网络与发信号限制；调用方 agent 本身没有被自动隔离。
- 独立评分进程验证预测 ID 全量覆盖；不信任训练 stdout 自报指标。
- 开发阶段的配对种子 bootstrap 输出 accepted、rejected 或 inconclusive；它不解决自适应选优或重复检验。
- 显式晋级前检查源工作区、patch 与目标 baseline；应用后保留为未提交改动。

实验归档与代码晋级分开。只有点估计变好，不能自动证明有可靠收益；统计规则要匹配训练 seeds、评测样本和重复尝试的方式。

验证示例包括 micrograd、SimpleBayes 文本分类和 PyTorch 微型字符语言模型。PyTorch 示例使用 CPU 单线程，训练、checkpoint 推理、可信评分分离。DVC、SSH、Slurm、专用 agent skill 和 UI 等能力尚未实现。

## 设计资料

- [核心架构与信任边界](docs/architecture.md)
- [MVP 验收标准](docs/mvp.md)
- [Harness-first 架构决策](docs/decisions/0001-harness-first.md)
- [实验合同草案](examples/experiment.proposed.json)——仅用于讨论，目前不能运行。

项目采用 [MIT License](LICENSE)。
