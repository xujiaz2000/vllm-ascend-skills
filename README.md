# vllm-ascend-skills

面向昇腾 NPU 的 vLLM Ascend 工作流 skill 集合。

| Skill | 用途 |
| --- | --- |
| [vllm-ascend-model-deployer](skills/vllm-ascend-model-deployer/SKILL.md) | 根据模型对应的官方指南在远程服务器创建容器、对齐源码版本、按需适配并启动推理服务。执行前列出计划供核对，部署后用真实请求验收。 |

## 调用示例

将需要的 skill 目录安装到 Codex 的 `~/.codex/skills/`（自定义 `CODEX_HOME` 时使用其下的 `skills/`）。以下请求使用示例地址和路径，调用时替换为实际值。

```text
$vllm-ascend-model-deployer
服务器类型：A3 752T
IP：192.0.2.10
容器名称：deepseek-v41
工作目录：/mnt/share/team/deepseek-v41
模型权重路径：/mnt/weights/DeepSeek-V4.1-Flash-1017-w4a8
服务部署方式：A3 单节点共置
额外适配点：无
```

核对返回的机器、环境和计划后，回复“执行”。需要 TP8PP2 等改动时，在“额外适配点”中明确填写。
