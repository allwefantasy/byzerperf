from typing import Dict, Any,List,Generator
from byzerllm.utils.client import ByzerLLM,Templates
import json
import time
import os
import ray
import concurrent
from threading import Lock
from byzerperf import utils

class TaskResult():
    #{"response": "", "metadata": {"request_id": "d9577d6295804e1fbfc28d2e4065005b", 
    # "input_tokens_count": 21, "generated_tokens_count": 143, 
    # "time_cost": 9604, "first_token_time": 133, "speed": 14.889629321116201, "prob": -0.6931471824645996, "client.duration": 9619.448789977469}}
    def __init__(self,
                response:str,
                request_id:str,
                input_tokens_count:int,
                generated_tokens_count:int,
                time_cost:int,
                first_token_time:int,
                speed:float,
                prob:float,
                client_duration:float
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
     
    @classmethod
    def build_from(cls,data:Dict[str,Any]):         
        data["metadata"]["client_duration"] = data["metadata"]["client.duration"]
        del data["metadata"]["client.duration"]
        return cls(response=data["response"],**data["metadata"])         
    

class Task():

    def __init__(self,
                 prompts:List[str],
                 model:str,                                                
                 additional_sampling_params:Dict[str,Any],                 
                 metadata:Dict[str,Any],                                  
                 template:str="auto" ) -> None:
        self.prompts = prompts
        self.model = model                       
        self.additional_sampling_params = additional_sampling_params        
        self.metadata = metadata                            
        self.template = template
        self.client = self.construct_client()

    def construct_client(self):
        llm = ByzerLLM()  

        if self.template == "qwen":
            llm.setup_template(model=self.model,template=Templates.qwen())
        elif self.template == "yi":
            llm.setup_template(model=self.model,template=Templates.yi())
        else:
            llm.setup_template(model=self.model,template="auto")

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
        metadata["client.duration"] = (end - start)*1000
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
    def __init__(self,llm:ByzerLLM,results_dir:str) -> None:
        self.results_dir = results_dir  
        self.llm = llm 
        self.data = self.get_data()    


    def get_data(self)->Generator[TaskResult, None, None]:
        for root, dirs, files in os.walk(self.results_dir):
            for file in files:
                if file.endswith(".jsonl"):
                    with open(os.path.join(root, file), "r") as f:
                        for line in f:
                            if line.strip() == "":
                                continue
                            yield TaskResult.build_from(json.loads(line))

    def _run(self,prompt:str)->utils.Str:   
        pass 
    
    def run(self,prompt:str):
        metrics = {
            "avg_input_tokens_count": 0,
            "avg_generated_tokens_count": 0,
            "server_generated_tokens_per_second": 0,
            "avg_server_duration": 0,
            "avg_client_duration": 0,
            "client_generated_tokens_per_second": 0,
        }
        row_count = 0
        for row in self.data:
            row_count += 1
            metrics["avg_generated_tokens_count"] += row.generated_tokens_count
            metrics["avg_input_tokens_count"] += row.input_tokens_count
            metrics["avg_server_duration"] += row.time_cost
            metrics["avg_client_duration"] += row.client_duration

        metrics["avg_generated_tokens_count"] = metrics["avg_generated_tokens_count"] / row_count
        metrics["avg_input_tokens_count"] = metrics["avg_input_tokens_count"] / row_count
        metrics["avg_server_duration"] = metrics["avg_server_duration"] / row_count 
        metrics["avg_client_duration"] = metrics["avg_client_duration"] / row_count 

        context = json.dumps(metrics,ensure_ascii=False)   

        v = self.llm.response()(self._run)(f'''
有上下文如下：
                                              
```json                                              
{context}
```
请根据上面的上下文回答：{prompt}
''')
        return v,context


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
                 template:str="auto"                 
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
    
    def prompts(self):
        prompts = []
        for filename in os.listdir(self.prompts_dir):
            filepath = os.path.join(self.prompts_dir, filename)
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
                        template=template) 
                    tasks.append(task)
                                                
                for i,task in enumerate(tasks):                    
                    file = ouptut_files[i]
                    print(f"Starting task-{i} {task}. output_file:{file.name}",flush=True)
                    executor.submit(run_task,f"task-{i}",task.run.remote(),file,complted_requests)                                                                   
            
            return 
        
        raise NotImplementedError("tasks_use_ray only support Ray for now")                   
