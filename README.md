
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

1. qwen (If you use Qwen 1.5,please use `auto` instead)
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

## Roadmap

- [] Support streaming inference performance test which can have TTFT metric(the first token arrived time)
- [] Add metric of  error rate