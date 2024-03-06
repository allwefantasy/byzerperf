
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


## Brand new Installation

You can use the script provided by Byzer-LLM to setup the nvidia-driver/cuda environment:

1. [CentOS 8 / Ubuntu 20.04 / Ubuntu 22.04](https://docs.byzer.org/#/byzer-lang/zh-cn/byzer-llm/deploy)

After the nvidia-driver/cuda environment is set up, you can install byzerperf like this:

```shell
pip install -U byzerperf
```

## Existing Installation


```shell
# or https://gitcode.com/allwefantasy11/byzerperf.git
git clone https://github.com/allwefantasy/byzerperf
pip install -r requirements.txt
pip install -U vllm
pip install -U byzerllm
pip install -U byzerperf
```

## Usage 

### Command Line

You need to use  [Byzer-LLM](https://github.com/allwefantasy/byzer-llm) to deploy model.
Once the model deployed, you can use the following command to test the performance of the model:

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


Then you can use the following command to view the performance test result:

```shell
python explain.py --results-dir ./result --model chat --template qwen
```

### Python API

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

## Troubleshooting

### One model intance with multiple Workers

If you deploy one model instance with multiple workers, here is a example code:


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

This code will deploy the model with 4 workers and each worker has 2 GPUs, and each worker is a vLLM backend.
When the request is sent to the model, the LRU policy will be used to route the request to the worker.

But the ByzerLLM have many type of request:

1. embedding
2. apply_chat_template
3. tokenize
4. complete/chat

This will cause some workers to be idle since some workers have much requests like `complete/chat` and some workers have much requests like `embedding`. but only complete/chat requests will be used to test the performance of the model.

The solution is that you can use the following code to bind non-complete/chat requests to the same worker and not use the LRU policy:

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