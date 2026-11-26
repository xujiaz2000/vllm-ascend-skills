# 部署时遇到特定现象再使用

## 官网短命令没有注入设备

先比较教程要求的 Ascend Docker Runtime 与宿主机实际 runtime、hook 报错和配置。若 runtime 无法使用，按官方手动映射章节为**本机实际逻辑设备**传入设备节点、控制节点及驱动挂载，再在容器内检查设备可见性。设备数量、型号和驱动路径以当前机器为准。使用 autofs 时，可在绑定父目录前访问实际权重目录触发挂载。[官方手动设备映射](https://docs.vllm.ai/projects/ascend/en/latest/getting_started/installation.html#manual-device-mapping-without-ascend-docker-runtime)

## HBM 已释放，新容器仍报 DCMI `-8020`

在宿主机检查 `npu-smi info` 的设备、进程和显存，结合进程 cgroup、`docker inspect` 和 `docker top` 确认容器归属。支持 `/proc/uda/namespace_node` 的驱动还可从 `ns_id < 128` 的映射中查逻辑设备和 `root_tgid`，与容器 PID 1 对照。worker 退出后，旧容器的命名空间仍可能独占设备。报告具体持有者，以及停止它会影响的其他进程、转发端口或跨节点服务。等待用户指令后，只对获准的对象操作并复查新容器能否看到设备。[昇腾设备独占故障说明](https://www.hiascend.com/document/caselibrary/detail/topic_0000002238354198)

## DeepSeek-V4.1-Flash 在 A3 上显式要求 TP8PP2

官方 A3 单节点共置示例使用 DP4/TP4。若用户要求在 16 个逻辑设备上使用 TP8PP2，则设为 `--data-parallel-size 1 --tensor-parallel-size 8 --pipeline-parallel-size 2`。核对所选版本是否支持 PP 和投机解码的组合；保留 Engram CPU offload，DP1 时按配对版本的要求关闭 `dp_shared_memory`。验收时从日志核对两个 PP 阶段、16 个 rank 和实际返回的模型输出。其他模型及部署模式从各自的官方示例重新推导。[DeepSeek-V4.1-Flash 单节点共置](https://docs.vllm.ai/projects/ascend/en/latest/tutorials/models/DeepSeek-V4.1-Flash.html#51-single-node-colocated-deployment)

## 加载完成后，KV 块表申请主机锁页内存失败

先读到第一个 worker 的完整异常，核对分配 API、失败大小和发生阶段。一次 A3 部署在分配 KV 块表时，`aclrtMallocHostWithCfg` 申请 128 字节主机锁页内存返回 `207001`。核对 TorchNPU、CANN 和驱动版本支持后，仅在该服务原有的 `PYTORCH_NPU_ALLOC_CONF` 中追加 `pin_memory_expandable_segments:True`。该次部署保留了原并行、上下文和显存比例，通过块表初始化、图捕获及真实推理。相同错误码也可能来自其他分配；先匹配现场堆栈并验证，避免全机清缓存或把这项参数带入常规脚本。[TorchNPU 分配器说明](https://github.com/Ascend/pytorch/blob/master/docs/zh/api/environment_variable/memory_management/PYTORCH_NPU_ALLOC_CONF.md)
