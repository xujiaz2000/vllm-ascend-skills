---
name: vllm-ascend-perf-tester
description: 使用 AISBench 为 vLLM Ascend 在线推理服务做性能测试。适用于通过指定脚本拉起服务或复用现有端点，先列出可修正的负载参数，确认后执行稳态压测并交付宿主机日志和吞吐、延迟结果。
---

# vLLM Ascend 性能测试

## 先给调用者一份可执行的计划

结合调用者给出的脚本、服务地址和当前会话，只读核实可获得的信息。用一张参数表区分调用者指定的值、建议默认值和待核实项。计划应能回答以下问题。

- **测哪个服务**。列出主机、启动脚本或现有端点、模型别名、tokenizer 路径、上下文上限和实际服务 NPU 数。通过运行参数、worker 与设备映射核对卡数，多节点按参与本实例的设备合计。说明将复用服务还是执行哪个启动脚本。
- **施加什么负载**。给出数据源、模式、目标输入和输出长度、长度分布、并发、样本数、seed、请求速率、warmup 和重复轮数。给出展开后的命令和宿主机日志根目录。调用者覆盖并发时，未指定的样本数随之重算；覆盖定长输入时，未指定的均值随之更新。
- **服务能否承载**。按聊天模板封装后的输入加输出预算检查上下文，区分客户端并发和服务端调度上限。若上下文不足或现有流量会干扰测量，说明影响并提出最小调整供调用者选择。

仅要求“跑一下性能测试”时，建议以下基线。这里的 128K 是 131072 token。

| 参数 | 建议值 |
| --- | --- |
| 工具与统计 | `aisbench_auto_tools_prefix`，流式对话，`stable_stage` |
| 数据集 | 工具自带 GSM8K，`normal` 模式，省略 `--dataset` |
| 长度 | 输入 131072，输出 1，`length_mean=131072`，`length_std=0` |
| 并发与样本 | 并发 32，样本数为并发的 4 倍，默认 128 条 |
| 其他 | `seed=1024`，`npu_num` 取服务实际值；其余沿用所用版本默认值 |

先展示计划，再等调用者确认或给出可执行的修正。例如“改成 8K、并发 8，其他照旧”即按 8192 输入、均值 8192、并发 8、32 条执行。只要求更新计划时继续等待。启动服务、下载镜像、修改配置和发起压测都在此后进行。

## 按确认的参数执行

1. **就绪服务**。按计划复用匹配的服务，或运行指定启动脚本。从评测容器可达的地址验证 `/health` 和 `/v1/models`，核实模型别名、上下文和 NPU 数。若实际情况要求更换测试对象、挤占其他服务或改变已确认的负载，先说明差异。
2. **准备 AISBench**。在评测宿主机按架构选择最新官方基础镜像，默认 Ubuntu。核对本机已有镜像的版本和架构，匹配即可复用。需要下载时按官方指南导入并核对镜像，核实成功后删除本次下载的归档；下载工具源码压缩包时同样在核实解压成功后删除。记录使用的镜像标识和工具版本。[AISBench 官方指南](https://github.com/AISBench/benchmark) · [基础镜像 Releases](https://github.com/AISBench/benchmark/releases/latest)
3. **配置工具**。在可写的独立工具工作目录中按 README 修改 `config.py`。`WORK_PATH` 指向容器内 AISBench 源码根目录，`DATASET_PATH` 指向本轮生成数据的可写目录，`MODEL_PATH` 指向评测容器可读的模型 tokenizer，`MODEL_NAME` 使用服务别名。按端点设置 `HOST_IP`、`HOST_PORT` 或 `URL`。默认设 `DEFAULT_PERFORMANCE_TEST = "stable_stage"`，让 `OUTPUT_DIR` 映射到宿主机的 `<工作路径>/aisbench_output`。工具会替换 AISBench 的 `gsm8k/test.jsonl` 和临时模型配置软链。复用容器前核对这两处，若为共享数据或只读挂载，可用同一镜像新建独立评测容器。长输入数据会进入 `/dev/shm`，按数据体量留足空间；默认负载的 128 条长输入可用 `--shm-size=1g`。[工具 README](https://github.com/rayn-zzz/aisbench_auto_tools_prefix)
4. **发起并监测**。从包含 `GSM8K.jsonl` 的工具根目录执行。下面是默认负载，运行前将 `NPU_NUM` 设为核实的卡数，按计划替换其余参数。观察 `POST/RECV/FAIL/FIN` 直到请求结束并生成报告。若工具失败，先核对已发送请求、错误和服务健康；修正评测环境后用同一批样本、新实验目录重试。需要改变负载或重复错误原因仍不明时，保留失败日志并告知调用者。

   ```bash
   python3 aisbench_test.py \
     --input_len 131072 --output_len 1 --concurrency 32 --data_num 128 \
     --seed 1024 --npu_num "${NPU_NUM:?请先设置实际服务卡数}" \
     --length_mean 131072 --length_std 0
   ```

## 核对结果并交付

从本轮日志的 `Current exp folder` 定位原生报告。包装脚本经过 `tee`，即使 AISBench 失败也可能返回 0 并写出汇总 CSV。默认单轮 GSM8K 稳态测试可在能读取实验目录的位置运行随附的[校验脚本](scripts/check_run.py)，传入本轮原生报告和预期请求数。

```bash
python3 /path/to/check_run.py "$EXP_DIR/performances/vllm-api-stream-chat/gsm8k.json" --requests 128
```

校验全程唯一请求数、成功和失败数、各请求实际输入输出长度，并单列稳态样本数和峰值并发。模板会改变输入 token 数；将实测长度与约定目标一起报告。按原生 JSON 取稳态吞吐，按同目录 CSV 取平均和 P90 首 token 延迟，保留单位。输出只有 1 token 时，TPOT 无有效解码间隔。对于其他格式或多轮测试，按实际的运行标识逐轮核对相同证据。

最终先给出**主机和宿主机上可读的本轮 `aisbench.log` 绝对路径**，通常为 `<工作路径>/aisbench_output/<实验标识>/aisbench.log`。若工具版本仅在当前目录生成日志，将它复制到本轮实验目录并验证可读。随后列出全程成功数、稳态样本数、实际并发、关键性能指标与服务最终健康状态。有失败、缺报告或未形成稳态时，明确缺失项并给出可定位原因的日志。
