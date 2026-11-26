# vllm-ascend-skills

面向昇腾 NPU 的 vLLM Ascend 工作流 skill 集合。

| Skill | 用途 |
| --- | --- |
| [vllm-ascend-model-deployer](skills/vllm-ascend-model-deployer/SKILL.md) | 根据模型对应的官方指南在远程服务器创建容器、对齐源码版本、按需适配并启动推理服务。执行前列出计划供核对，部署后用真实请求验收。 |
| [vllm-ascend-profiler](skills/vllm-ascend-profiler/SKILL.md) | 按确认的测试负载、触发时机和时长采集 NPU profiling，使用 TorchNPU 离线解析，逐个 rank 验证并给出时间线路径。 |

## 调用示例

将需要的 skill 目录安装到 Codex 的 `~/.codex/skills/`（自定义 `CODEX_HOME` 时使用其下的 `skills/`）。以下请求使用示例地址和路径，调用时替换为实际值。

```text
$vllm-ascend-model-deployer 帮我在 192.0.2.10 服务器上拉起 DeepSeek-V4.1-Flash 模型服务，权重位于 /mnt/weights/DeepSeek-V4.1-Flash-1017-w4a8。
```

只给一台服务器时，如果对应教程支持单节点共置，skill 会先提议该方式，给出容器名、工作目录和执行计划，并注明哪些信息要上机核实，例如硬件型号和空闲显存。回复“确认”即可执行，也可以直接修正，例如“改为 1P1D，P 节点用 192.0.2.10，D 节点用 192.0.2.11”。需要 TP8PP2 等额外适配时，也可以直接写在请求中。

```text
$vllm-ascend-profiler 通过 /srv/model/start_service.sh 拉起模型服务，采集 1s 的 profiling。
```

采集计划默认建议使用 AISBench 的 AIME 2026 负载，在 8 道正式题完成后采样。确认计划或修正负载、触发条件和时长后，skill 执行采集并返回解析路径。
