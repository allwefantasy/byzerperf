
<p align="center">
  <picture>    
    <img alt="byzer-perf" src="https://github.com/allwefantasy/byzer-llm/blob/master/docs/source/assets/logos/logo.jpg" width=55%>
  </picture>
</p>

<h3 align="center">
Perf Tool For Byzer-LLM
</h3>

<p align="center">
| <a href="./README.md"><b>English</b></a> | <a href="./README-CN.md"><b>中文</b></a> |

</p>

---

*Latest News* 🔥

- [2024/03] Release Byzer-Perf 0.1.2
- [2024/02] Release Byzer-Perf 0.1.0

---


## Installation

```shell
# or https://gitcode.com/allwefantasy11/byzerperf.git
git clone https://github.com/allwefantasy/byzerperf
pip install -r requirements.txt
pip install -U byzerperf
```

We recommend that you use the environment configured for [Byzer-LLM](https://github.com/allwefantasy/byzer-llm) and then just install byzerperf like this:

```shell
pip install -U byzerperf
```


## Usage

Deploy the model by [Byzer-LLM](https://github.com/allwefantasy/byzer-llm). With the model deployed, you can use the following command to test the performance of the model:

```shell
cd byzerperf
python perf.py --results-dir ./result  --prompts-dir ./prompts --num-concurrent-requests 5 --model chat --template qwen
```

The above command will send 5 concurrent requests to the model and the result will be saved in the `./result` directory.
The parameter template now supports:

1. qwen
2. yi 
3. default (Style: User:xxxx \nAssistant:xxxx )
3. auto

Since Byzer-LLM supports SaaS model and roprietary model deployment, so you can test the performance of any SaaS model or proprietary model.

If you prefer to use the Python API, you can use the following code to test the performance of the model.

Suppose we want to test the performance of the chat model with [5,10,15,20] concurrent requests separately, and the model is deployed with 4 GPUs, quantization is int4, and the LLM size is qwen-72B.

```python

import os
import ray

ray.init(address="auto",namespace="default",ignore_reinit_error=True)   

from byzerperf.perf import ByzerLLMPerf

num_gpus = 4
quantization = "int4"
llm_size = "qwen1_5-72B"

for i in range(5,25,5):
    num_concurrent_requests = i
    result_dir = f"/home/byzerllm/projects/byzerperf/result-{num_concurrent_requests}-{llm_size}-{quantization}-{num_gpus}gpu"

    byzer_llm_perf = ByzerLLMPerf.create(
            model="chat",                        
            num_concurrent_requests=num_concurrent_requests,            
            results_dir=result_dir,                        
            prompts_dir="/home/byzerllm/projects/byzerperf/prompts",
            template="qwen",        
        )        

    byzer_llm_perf.run()
    
```

After running the above code, you will get the performance test result in the `result_dir` directory.

```python
 
import ray
from byzerllm.utils.client import ByzerLLM,Templates
from byzerperf.perf import ByzerLLMPerfExplains

ray.init(address="auto",namespace="default",ignore_reinit_error=True) 

result = []

num_gpus = 4
quantization = "int4"
llm_size = "qwen1_5-72B"

llm = ByzerLLM()
chat_model_name = "chat"               
llm.setup_template(chat_model_name,"auto") 
llm.setup_default_model_name(chat_model_name)

for i in range(5,25,5):
    num_concurrent_requests = i
    result_dir = f"/home/byzerllm/projects/byzerperf/result-{num_concurrent_requests}-{llm_size}-{quantization}-{num_gpus}gpu"    
    explains = ByzerLLMPerfExplains(llm,result_dir)
    t,context = explains.run()  
    print()
    print()
    title = f"==========num_concurrent_requests:{num_concurrent_requests} total_requests: 84=============" 
    print(context)
    print(title)
    print(t)
    result.append(title)
    result.append(t)
```

Here is the output:

```

==========num_concurrent_requests:5 total_requests: 84=============
在平均输入token长度为18.68的情况下，从请求输入到服务器返回第一个token的平均时间为174.79ms。

服务器每个请求平均吞吐23.21 tokens/s

客户端每秒生成97.78 tokens
服务器每秒生成115.33 tokens


==========num_concurrent_requests:10 total_requests: 84=============
在平均输入token长度为18.68的情况下，从请求输入到服务器返回第一个token的平均时间为227.48ms。

服务器每个请求平均吞吐14.93 tokens/s

客户端每秒生成121.59 tokens
服务器每秒生成145.34 tokens


==========num_concurrent_requests:15 total_requests: 84=============
在平均输入token长度为18.68的情况下，从请求输入到服务器返回第一个token的平均时间为313.24ms。

服务器每个请求平均吞吐13.73 tokens/s

客户端每秒生成166.85 tokens
服务器每秒生成198.85 tokens


==========num_concurrent_requests:20 total_requests: 84=============
在平均输入token长度为18.68的情况下，从请求输入到服务器返回第一个token的平均时间为465.92ms。

服务器每个请求平均吞吐10.90 tokens/s

客户端每秒生成162.73 tokens
服务器每秒生成202.48 tokens
```

We hope that we can get the best num_concurrent_requests value from the above output:

```python
s = "\n\n".join(result)
t = llm.chat_oai(conversations=[{
    "role":"user",
    "content":f'''
有上下文如下：

```
{s}
```
请参考上面的内容，随着num_concurrent_requests的增加，其他指标的变化情况做个总结。
另外分析最佳并发数应该是多少？随着并发数上升吞吐也会上升，而单次请求吞吐则会下降，请找到两者的交汇点，给出交汇点。
'''
}])

print(t[0].output)
```

The output:

```
随着`num_concurrent_requests`的增加，以下指标发生了变化：

1. **平均响应时间**：随着并发请求的增加，从请求输入到服务器返回第一个token的平均时间也在增加。这表明服务器处理请求的压力增大，响应时间变慢。具体来说，从5个并发请求的174.79ms增加到20个并发请求的465.92ms。

2. **服务器每个请求的平均吞吐量（tokens/s）**：并发请求的增加导致服务器每个请求的吞吐量下降。从5个并发请求时的23.21 tokens/s，下降到20个并发请求时的10.90 tokens/s，这表明服务器在处理更多并发请求时，处理每个请求的效率降低。

3. **客户端和服务器生成tokens的速度**：尽管服务器的单个请求处理速度下降，但随着并发请求的增加，服务器和客户端整体生成tokens的速度都在上升。这表明系统在处理更多并发请求时，整体处理能力有所提高。

最佳并发数的确定需要找到服务器处理请求效率和并发数之间的平衡点。从上述数据来看，随着并发数的增加，服务器单个请求的吞吐量下降，但整体吞吐量（即总处理能力）在增加，直到某个点后，增加的并发数可能对服务器造成过度压力，导致响应时间过长，效率下降。在给出的数据中，这个平衡点可能在`num_concurrent_requests:10`时达到，因为此时服务器的每个请求吞吐量（14.93 tokens/s）和整体吞吐量（145.34 tokens/s）都相对较高，同时响应时间（227.48ms）还在可接受范围内。然而，这需要根据实际应用的需求和服务器的承载能力来进一步确认。
```

## Troubleshooting

### One model intance with multiple Workers

If you deploy one model instance with multiple workers, then the ByzerLLM will route the request to the worker with the LRU policy. But the ByzerLLM have other type of request:

1. embedding
2. apply_chat_template
3. tokenize
4. complete/chat

This will cause some workers to be idle since some workers have much requests like `complete/chat` and some workers have much requests like `embedding`. but only complete/chat requests will be used to test the performance of the model.

Here is the deployment code:

```python
llm.setup_gpus_per_worker(2).setup_num_workers(4).setup_infer_backend(InferBackend.VLLM)
llm.setup_worker_concurrency(999)
llm.sys_conf["load_balance"] = "round_robin"
llm.deploy(
    model_path=model_location,
    pretrained_model_type="custom/auto",
    udf_name=chat_model_name,
    infer_params={"backend.gpu_memory_utilization":0.8,
                  "backend.enforce_eager":False,
                  "backend.trust_remote_code":True,
                  "backend.max_model_len":1024*4,
                  "backend.quantization":"gptq",
                  }
)
```

This code will deploy the model with 4 workers and each worker has 2 GPUs, and each worker is a vLLM worker.
When the request is sent to the model, the LRU policy will be used to route the request to the worker.

Then you can use the following code to bind non-complete/chat requests to the same worker and not use the LRU policy.

```python

import os
import ray

ray.init(address="auto",namespace="default",ignore_reinit_error=True)   

from byzerperf.perf import ByzerLLMPerf

num_gpus = 8
quantization = "int4"
llm_size = "qwen-72B"


for i in range(50,230,30):
    num_concurrent_requests = i
    result_dir = f"/home/byzerllm/projects/byzerperf/result-6-{num_concurrent_requests}-{llm_size}-{quantization}-{num_gpus}gpu"

    byzer_llm_perf = ByzerLLMPerf.create(
            model="chat",                        
            num_concurrent_requests=num_concurrent_requests,            
            results_dir=result_dir,                        
            prompts_dir="/home/byzerllm/projects/byzerperf/prompts",
            template="qwen",  
            pin_model_worker_mapping={
                "embedding":0,
                "tokenizer":0,
                "apply_chat_template":0,
                "meta":0,
            }      
        )        

    byzer_llm_perf.run()
    
```

After setting the `pin_model_worker_mapping` parameter, the complete/chat request will be sent to the workers with the LRU policy, and the other requests will be sent to the workers with the specified worker id.

## Roadmap

- [] Support streaming inference performance test
- [] Add metric of  error rate