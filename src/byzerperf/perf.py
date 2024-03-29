from typing import Dict, Any,List,Generator,Optional
from byzerllm.utils.client import ByzerLLM,Templates
import json
import time
import os
import ray
import concurrent
from threading import Lock
from byzerperf import utils

class TaskResult():    
    def __init__(self,
                response:str,
                request_id:str,
                input_tokens_count:int,
                generated_tokens_count:int,
                time_cost:int,
                first_token_time:int,
                speed:float,
                prob:float,
                client_duration:float,
                client_start:float,
                client_end:float
                 ) -> None:
        self.response = response
        self.request_id = request_id
        self.input_tokens_count = input_tokens_count
        self.generated_tokens_count = generated_tokens_count
        self.time_cost = time_cost
        self.first_token_time = first_token_time
        self.speed = speed
        self.prob = prob
        self.client_duration = client_duration
        self.client_start = client_start
        self.client_end = client_end
     
    @classmethod
    def build_from(cls,data:Dict[str,Any]):                   
        return cls(response=data["response"],**data["metadata"])         
    

class Task():

    def __init__(self,
                 prompts:List[str],
                 model:str,                                                
                 additional_sampling_params:Dict[str,Any],                 
                 metadata:Dict[str,Any],                                  
                 template:str="auto" ,
                 pin_model_worker_mapping:Optional[Dict[str,int]]=None,
                 ) -> None:
        self.prompts = prompts
        self.model = model                       
        self.additional_sampling_params = additional_sampling_params        
        self.metadata = metadata                            
        self.template = template
        self.pin_model_worker_mapping = pin_model_worker_mapping
        self.client = self.construct_client()

    def construct_client(self):
        llm = ByzerLLM()  

        if self.template == "qwen":
            llm.setup_template(model=self.model,template=Templates.qwen())
        elif self.template == "yi":
            llm.setup_template(model=self.model,template=Templates.yi())  
        elif self.template == "default":
            llm.setup_template(model=self.model,template=Templates.default())            
        else:
            llm.setup_template(model=self.model,template="auto")
        
        if self.pin_model_worker_mapping is not None:
            llm.setup_pin_model_worker_mapping(self.pin_model_worker_mapping)

        llm.setup_default_emb_model_name("emb")
        llm.setup_default_model_name(self.model)
        llm.setup_extra_generation_params(self.model,extra_generation_params={
            "temperature":0.01,
            "top_p":0.99,
            **self.additional_sampling_params
        })
        return llm

    def request(self,query:str):
        if self.client is None:            
            self.client = self.construct_client()
    
        start = time.monotonic()
        t = self.client.chat_oai(conversations=[{
            "role":"user",
            "content":query
        }])
        end = time.monotonic()
        metadata = t[0].metadata
        metadata["client_duration"] = (end - start)*1000
        metadata["client_start"] = start
        metadata["client_end"] = end
        return {
            "response":t[0].output,
            "metadata":metadata
        }
    
    def run(self):        
        for prompt in self.prompts:
            yield(self.request(prompt)) 

class RowCounter():
    def __init__(self,total:int):
        self.count = 0
        self.total = total
        self.lock = Lock()

    def increment(self,suffix=""):
        with self.lock:
            self.count += 1

        print(f"Completed Requests:{self.count}/{self.total} {suffix}",flush=True)    
        return self.count

def run_task(task_id,task_response,output_file,counter:RowCounter):
    for item in task_response:
        row = ray.get(item)
        output_file.write(json.dumps(row,ensure_ascii=False) + "\n")
        counter.increment(f"from task {task_id}")
    output_file.close()                                
                            

class ByzerLLMPerfExplains():     
    def __init__(self,llm:ByzerLLM,results_dir:str,num_concurrent_requests:int=0) -> None:
        self.results_dir = results_dir  
        self.llm = llm 
        self.data = self.get_data() 
        self.memory = []   
        self.num_concurrent_requests = num_concurrent_requests
        if self.num_concurrent_requests == 0:
            self.num_concurrent_requests = self.get_num_concurrent_requests()

    def get_num_concurrent_requests(self):
        count = 0
        for root, dirs, files in os.walk(self.results_dir):
            for file in files:
                if file.endswith(".jsonl"):
                   count += 1
        return count           

    def get_data(self)->Generator[TaskResult, None, None]:
        for root, dirs, files in os.walk(self.results_dir):
            for file in files:
                if file.endswith(".jsonl"):
                    with open(os.path.join(root, file), "r") as f:
                        for line in f:
                            if line.strip() == "":
                                continue
                            yield TaskResult.build_from(json.loads(line))

    def get_metrics(self):
        metrics = {
            "avg_input_tokens_count": 0,
            "avg_generated_tokens_count": 0,
            "server_generated_tokens_per_second": 0,
            "avg_server_duration": 0,
            "avg_client_duration": 0,
            "client_generated_tokens_per_second": 0,
            "generated_tokens_count": 0,
            "input_tokens_count": 0,
            "server_duration": 0,
            "client_duration": 0,
            "server_sum_speed":0,
            "server_sum_first_token_time":0,
        }
        row_count = 0
        min_start = 0
        max_end = 0
        for row in self.data:
            row_count += 1

            if min_start == 0:
                min_start = row.client_start
            if max_end == 0:
                max_end = row.client_end

            if row.client_start < min_start:
                min_start = row.client_start
            if row.client_end > max_end:
                max_end = row.client_end
            metrics["generated_tokens_count"] += row.generated_tokens_count
            metrics["input_tokens_count"] += row.input_tokens_count
            metrics["server_duration"] += row.time_cost
            metrics["client_duration"] += row.client_duration
            metrics["server_sum_speed"] += row.speed
            metrics["server_sum_first_token_time"] += row.first_token_time
        
        metrics["first_request_submit_time"]  = min_start
        metrics["last_request_complete_time"] = max_end

        metrics["avg_server_speed"] = metrics["server_sum_speed"] / row_count
        metrics["avg_server_first_token_time"] = metrics["server_sum_first_token_time"] / row_count

        metrics["server_generated_tokens_per_second_per_request"] = metrics["generated_tokens_count"] / metrics["server_duration"] * 1000
        metrics["client_generated_tokens_per_second_per_request"] = metrics["generated_tokens_count"] / metrics["client_duration"] * 1000

        metrics["server_generated_tokens_per_second"] = metrics["server_generated_tokens_per_second_per_request"] * self.num_concurrent_requests
        metrics["client_generated_tokens_per_second"] = metrics["generated_tokens_count"] / (max_end - min_start) 

        metrics["avg_generated_tokens_count"] = metrics["generated_tokens_count"] / row_count
        metrics["avg_input_tokens_count"] = metrics["input_tokens_count"] / row_count
        metrics["avg_server_duration"] = metrics["server_duration"] / row_count 
        metrics["avg_client_duration"] = metrics["client_duration"] / row_count 

        metrics["num_concurrent_requests"] = self.num_concurrent_requests
        return metrics 

    def get_system_message(self):
        metrics = self.get_metrics()  
        context = json.dumps(metrics,ensure_ascii=False)  
        return f'''有上下文如下：
```json
{context}
```

下面是一些关键指标的解释：
1. avg_server_speed: 服务器每个请求平均吞吐(tokens/s)
2. avg_input_tokens_count: 输入的平均tokens数
3. avg_server_first_token_time: 从请求输入到服务器返回第一个token的平均时间(ms)
4. client_generated_tokens_per_second: 客户端每秒生成的tokens数
5. server_generated_tokens_per_second: 服务器每秒生成的tokens数
''',context

    
    def run(self,prompt:str=None):        
        sys_content,context = self.get_system_message() 
        if len(self.memory) == 0:
            self.memory.append({
                "role":"system",
                "content":sys_content
            })            
        
        if prompt is None:
            conversation = {
    "role":"user",
    "content":f'''用下面的模板进行解释：

在平均输入token长度为{{avg_input_tokens_count}}的情况下，
从请求输入到服务器返回第一个token的平均时间为{{avg_server_first_token_time}}ms

服务器每个请求平均吞吐{{avg_server_speed}} tokens/s

客户端每秒生成{{client_generated_tokens_per_second}} tokens
服务器每秒生成{{server_generated_tokens_per_second}} tokens
'''
}          
            self.memory.append(conversation)
            t = self.llm.chat_oai(conversations=self.memory)
            self.memory.append({
                "role":"assistant",
                "content":t[0].output
            })
            return t[0].output,context
        
        conversation = {
                "role":"user",
                "content":prompt
        }        
        self.memory.append(conversation)
        t = self.llm.chat_oai(conversations=self.memory)        
        self.memory.append({
                "role":"assistant",
                "content":t[0].output
            })
        return t[0].output,context


class ByzerLLMPerf():

    def __init__(self,model:str,
                 timeout:int,
                 max_num_completed_requests:int,
                 num_concurrent_requests:int,
                 additional_sampling_params:Dict[str,Any],
                 results_dir:str,
                 metadata:Dict[str,Any],
                 prompts_dir:str,
                 tasks_use_ray:bool=True,
                 template:str="auto",
                 pin_model_worker_mapping:Optional[Dict[str,int]]=None                 
                 ):
         
        self.model = model
        self.timeout = timeout
        self.max_num_completed_requests = max_num_completed_requests
        self.num_concurrent_requests = num_concurrent_requests
        self.additional_sampling_params = additional_sampling_params
        self.results_dir = results_dir
        self.metadata = metadata            
        self.tasks_use_ray = tasks_use_ray
        self.prompts_dir = prompts_dir
        self.template = template
        self.client = None
        self.pin_model_worker_mapping = pin_model_worker_mapping
    
    @classmethod
    def create(cls,model:str,prompts_dir:str,results_dir:str,num_concurrent_requests:int,template:str="auto",pin_model_worker_mapping:Optional[Dict[str,int]]=None):
        return cls(
            model=model,
            timeout=90,
            max_num_completed_requests= 0,
            num_concurrent_requests=num_concurrent_requests,
            additional_sampling_params={},
            results_dir=results_dir,
            metadata={},            
            prompts_dir=prompts_dir,
            tasks_use_ray=True,
            template=template,
            pin_model_worker_mapping=pin_model_worker_mapping    
        )
    
    def prompts(self):
        prompts = []
        for filename in os.listdir(self.prompts_dir):
            filepath = os.path.join(self.prompts_dir, filename)
            _,extension = os.path.splitext(filepath)
            if extension == ".jsonl":
                with open(filepath, 'r') as file:
                    for line in file:
                        prompts.append(json.loads(line)["prompt"])
            else:            
                with open(filepath, 'r') as file:
                    for line in file:
                        prompts.append(line.strip())
        return prompts

    
    def run(self):
        model = self.model
        additional_sampling_params=self.additional_sampling_params 
        metadata=self.metadata   
        template=self.template 
        
        print("============================================",flush=True)
        print(f"Running perf with {self.num_concurrent_requests} concurrent requests",flush=True)
        print(f"Results will be saved to {self.results_dir}",flush=True)
        print(f"Using model {model}",flush=True)
        print(f"Using prompts from {self.prompts_dir}",flush=True)
        print(f"Using template {template}",flush=True)
        print(f"Using additional sampling params {additional_sampling_params}",flush=True)
        print(f"Using metadata {metadata}",flush=True)
        print(f"Using Ray for tasks {self.tasks_use_ray}",flush=True)
        
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
        
        if self.tasks_use_ray:            
            ouptut_files = [open(os.path.join(self.results_dir,f"perf_{i}.jsonl"),"w") for i in range(self.num_concurrent_requests)]            
            total_requests = len(self.prompts())
            complted_requests = RowCounter(total_requests)

            tasks = []            

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_concurrent_requests) as executor:
                for prompts in utils.split_list(self.prompts(),self.num_concurrent_requests):
                    task = ray.remote(Task).remote(
                        prompts=prompts,
                        model=model, 
                        additional_sampling_params=additional_sampling_params,                        
                        metadata=metadata,                                                
                        template=template,
                        pin_model_worker_mapping=self.pin_model_worker_mapping,
                        ) 
                    tasks.append(task)
                                                
                for i,task in enumerate(tasks):                    
                    file = ouptut_files[i]
                    print(f"Starting task-{i} {task}. output_file:{file.name}",flush=True)
                    executor.submit(run_task,f"task-{i}",task.run.remote(),file,complted_requests)                                                                   
            
            return 
        
        raise NotImplementedError("tasks_use_ray only support Ray for now")                   
