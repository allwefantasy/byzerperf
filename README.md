
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
3. auto

Since Byzer-LLM supports SaaS model and roprietary model deployment, so you can test the performance of any SaaS model or proprietary model.

If you prefer to use the Python API, you can use the following code to test the performance of the model:

```python
 
from byzerperf.perf import ByzerLLMPerf

byzer_llm_perf = ByzerLLMPerf(
        model="chat",
        timeout=1000,
        max_num_completed_requests= -1 ,
        num_concurrent_requests=10,
        additional_sampling_params={},
        results_dir="/home/byzerllm/projects/byzerperf/result-15",
        metadata={},
        tasks_use_ray=True,
        prompts_dir="/home/byzerllm/projects/byzerperf/prompts",
        template="qwen",        
    )        

byzer_llm_perf.run()    
```

## Performance Test Result

```python
import ray
from byzerllm.utils.client import ByzerLLM,Templates
from byzerperf.perf import ByzerLLMPerfExplains

ray.init(address="auto",namespace="default",ignore_reinit_error=True)  

llm = ByzerLLM()
chat_model_name = "qianwen_chat"               
llm.setup_template(chat_model_name,"auto") 
llm.setup_default_model_name(chat_model_name)

explains = ByzerLLMPerfExplains(llm,"/home/byzerllm/projects/byzerperf/result-15")
t,context = explains.run("服务端和客户端tokens/s分别是多少")   
t.value
```

The output:

```
服务端tokens/s为109.92657498681595，客户端tokens/s为93.13436850985012
```

You can get more metrics by print the `context`:

```python
print(context)
```

The output:

```json
{'avg_input_tokens_count': 18.678571428571427,
 'avg_generated_tokens_count': 161.29761904761904,
 'server_generated_tokens_per_second': 109.92657498681595,
 'avg_server_duration': 14673.214285714286,
 'avg_client_duration': 14693.433444989274,
 'client_generated_tokens_per_second': 93.13436850985012,
 'generated_tokens_count': 13549,
 'input_tokens_count': 1569,
 'server_duration': 1232550,
 'client_duration': 1234248.409379099,
 'first_request_submit_time': 279711.875170331,
 'last_request_complete_time': 279857.353152485,
 'server_generated_tokens_per_second_per_request': 10.992657498681595,
 'client_generated_tokens_per_second_per_request': 10.97753085767877,
 'num_concurrent_requests': 10}
```

## Roadmap

- [] Support streaming inference performance test which can have TTFT metric(the first token arrived time)
- [] Add metric of  error rate