# 使用 AISBench 触发采样

## 准备测试容器

1. 在宿主机根据架构选取官方最新正式版 Ubuntu 基础镜像；核对发行标签、架构和镜像 ID。已有匹配镜像时直接复用。若下载了离线包，`docker load -i "$ARCHIVE"` 成功并核对镜像后，删除本次下载的包。[官方部署指南](https://github.com/AISBench/benchmark) · [发行版本及镜像](https://github.com/AISBench/benchmark/releases)
2. 让测试容器可访问服务和模型分词器，并把本轮评测结果目录挂载到宿主机，供触发器读取。Linux 上使用 host 网络时，同机服务可用 `127.0.0.1`；其他网络模式填写从测试容器可达的地址。
3. 在评测容器检查 `ais_bench/datasets/aime2026/aime2026.jsonl`。已有完整文件时复用；需要下载时，按镜像内该数据集的 README 整理为 JSONL。AIME 2026 应有 30 道不同的题目，每条都包含 `problem` 和 `answer`。下面的相对路径从 AISBench 工具根目录计算。[数据集说明](https://github.com/AISBench/benchmark/blob/master/ais_bench/benchmark/configs/datasets/aime2026/README.md) · [ModelScope 数据集](https://www.modelscope.cn/datasets/evalscope/aime26)
4. 修改 `ais_bench/benchmark/configs/models/vllm_api/vllm_api_stream_chat.py`，将 `model` 对应到 `/v1/models` 返回的别名，`host_ip` 和 `host_port` 对应服务地址，`path` 对应评测容器内可读的分词器路径。核对 `stream=True`、并发和 `max_out_len`。用 `ais_bench --help` 确认当前版本的参数。

## 在第 8 道正式题后采集

下面的观察器适用于单个流式对话服务、仅本轮评测流量、并发 1 的情况。先核对镜像的正式推理结果会逐条刷新到 `**/tmp/tmp_*.jsonl`，其中有 `data_abbr`、`id`、`success`；warmup 走单独的结果队列。确认服务 access log 在流开始时写入成功的 `POST /v1/chat/completions`，并且两种日志均对观察器可见。轮次目录必须是新的。若有其他流量、不同的日志格式或并发要求，保留调用者的配置，用对应版本的客户端成功回调和在途请求事件关联本轮请求。

在宿主机（或能同时读取这两个路径的环境）先运行 [capture_after.py](../scripts/capture_after.py)。`HOST_RUN` 与下文的 `BENCH_RUN` 指向同一新目录在宿主机和评测容器中的路径。`API_ROOT` 形如 `http://127.0.0.1:8900`，`ACCESS_LOG` 是当前服务实际写入的日志文件。等待观察器输出 `ready` 再发起压测。

```bash
python3 capture_after.py --results "$HOST_RUN" --access-log "$ACCESS_LOG" \
  --api-root "$API_ROOT" --warmups 1 --after 8 --seconds 1
```

在评测容器运行：

```bash
ais_bench --models vllm_api_stream_chat \
  --datasets aime2026_gen_0_shot_chat_prompt --mode perf --debug \
  --num-warmups 1 -w "$BENCH_RUN"
```

观察器按正式成功结果的唯一 ID 计数。示例中第 10 个流对应 1 个 warmup、8 个已完成的正式请求和正在处理的第 9 个正式请求。采集停止后让压测跑完，保留观察器的时间记录和 AISBench 输出的性能报告，核对失败数。若某次请求重试或未能确定窗口，在新轮次修正观测条件；保留已有数据以便追溯。
