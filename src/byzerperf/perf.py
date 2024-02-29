from typing import Dict, Any,List
from byzerllm.utils.client import ByzerLLM,Templates
import json
import time
import os
import more_itertools
import ray
import concurrent
from threading import Lock

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
                for prompts in more_itertools.chunked(self.prompts(),self.num_concurrent_requests):
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
