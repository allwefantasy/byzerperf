from typing import Dict, Any
from byzerllm.utils.client import ByzerLLM,Templates
import json
from concurrent.futures import ProcessPoolExecutor
import time
import os
import more_itertools
import ray

class Task():

    def __init__(self,model:str,                                                
                 additional_sampling_params:Dict[str,Any],                 
                 metadata:Dict[str,Any],                                  
                 template:str="auto" ) -> None:
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

def request(query:str,**kargs):
    task = Task(**kargs)
    return task.request(query)    


class ByzerLLMPerf():

    def __init__(self,model:str,
                 timeout:int,
                 max_num_completed_requests:int,
                 num_concurrent_requests:int,
                 additional_sampling_params:Dict[str,Any],
                 results_dir:str,
                 metadata:Dict[str,Any],
                 prompts_dir:str,
                 tasks_use_ray:bool=False,
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

        
        
        if self.tasks_use_ray:            
            output_file = open(os.path.join(self.results_dir,"perf.jsonl"),"w")                            
            total_requests = len(self.prompts())
            complted_requests = 0
            for prompts in more_itertools.chunked(self.prompts(),self.num_concurrent_requests):
                temp_data = []
                if len(prompts) == self.num_concurrent_requests:
                    for prompt in prompts:      
                        print(f"Submit {prompt} ",flush=True)                  
                        task = ray.remote(Task).remote(model=model, 
                                                        additional_sampling_params=additional_sampling_params,                        
                                                        metadata=metadata,                                                
                                                        template=template)                                            
                        temp_data.append(ray.get(task.request.remote(prompt)))  
                        complted_requests += len(temp_data)
                        print(f"Completed {complted_requests}/{total_requests} requests ",flush=True)                                             
                for data in temp_data:
                    for d in data:
                        output_file.write(json.dumps(d,ensure_ascii=False) + "\n")
                temp_data.clear()
            output_file.close()
            return 
        
        output_file = open(os.path.join(self.results_dir,"perf.jsonl"),"w")
                
        with ProcessPoolExecutor(self.num_concurrent_requests) as executor:            
            total_requests = len(self.prompts())
            complted_requests = 0
            for prompts in more_itertools.chunked(self.prompts(),self.num_concurrent_requests):
                temp_data = []
                if len(prompts) == self.num_concurrent_requests:
                    for prompt in prompts:      
                        print(f"Submit {prompt} ",flush=True)                  
                        future = executor.submit(request,prompt,model=model, 
                        additional_sampling_params=additional_sampling_params,                        
                        metadata=metadata,                                                
                        template=template)
                        
                        temp_data.append(future.result())  
                        complted_requests += len(temp_data)
                        print(f"Completed {complted_requests}/{total_requests} requests ",flush=True)                                             
                for data in temp_data:
                    for d in data:
                        output_file.write(json.dumps(d,ensure_ascii=False) + "\n")
                temp_data.clear()
        output_file.close()                    
