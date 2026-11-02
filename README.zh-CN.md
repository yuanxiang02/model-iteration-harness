# Model Iteration Harness

为 coding agent 提供可追溯、可恢复、评测受控的模型迭代运行时。

[English](README.md) · [架构设计](docs/architecture.md) · [MVP 范围](docs/mvp.md)

> **当前状态：设计阶段。** 仓库目前包含项目定位、架构决策和实验合同草案；尚未提供可执行 harness、安装包或已实现的隔离保证。

## 解决的问题

Agent 可以修改训练代码，但可靠地迭代模型，还需要解决：

1. **评测受控：** 评测程序、数据划分、指标定义和晋级规则由可信组件管理。
2. **实验隔离：** 每个 patch 独立运行，记录 baseline、parent、配置、日志和产物。
3. **异步执行：** 训练期间由普通程序等待；任务结束或失败后，再触发评测和 agent review。
4. **证据验收：** 候选按预先确定的规则晋级，失败和不确定的实验也保留记录。

## 为什么采用 harness

Harness 负责状态、边界、执行与验收；skill 负责告诉 agent 如何调用这些能力。

项目会提供核心运行时和 CLI/API，再按需要提供 Codex、Claude Code 等 agent 的薄 skill。执行状态和验收规则不能只依赖对话上下文或提示词。

## 如何与模型训练解耦

使用者保留现有训练脚本。项目 adapter 声明如何启动训练、查询任务、收集产物和执行推理；可信 evaluator 根据固定评分协议计算结果。

核心框架理解实验生命周期，不要求统一模型结构、loss、checkpoint 格式或 Trainer 类。模型架构变化所需的加载与推理代码，应在受限的候选执行环境运行，不直接获得评分环境的数据和写权限。

## 第一版计划

- 每个候选一个独立 Git worktree，并立即保存实验合同和 patch。
- 本地 Linux 执行后端，训练与评分权限分离。
- job 状态落盘、结束事件、超时处理和重启恢复。
- 固定评分入口与证据归档。
- 一个明确的配对比较验收方案，输出通过、未通过或不确定。
- 输出可审查的晋级 patch；通过独立命令才应用到目标分支。

实验归档与代码晋级分开。只有点估计变好，不能自动证明有可靠收益；统计规则要匹配训练 seeds、评测样本和重复尝试的方式。

第一版先打通一个真实项目，再接入一个训练结构不同的任务验证解耦。DVC、SSH、Slurm、多 agent 和 UI 等能力按实际需求逐步加入。

## 设计资料

- [核心架构与信任边界](docs/architecture.md)
- [MVP 验收标准](docs/mvp.md)
- [Harness-first 架构决策](docs/decisions/0001-harness-first.md)
- [实验合同草案](examples/experiment.proposed.json)——仅用于讨论，目前不能运行。

项目采用 [MIT License](LICENSE)。
