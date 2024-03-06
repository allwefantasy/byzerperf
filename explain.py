import argparse
import json
import ray
from byzerperf.perf import ByzerLLMPerfExplains
from byzerllm.utils.client import ByzerLLM

args = argparse.ArgumentParser(description="Run a correctness test for a given model.")

args.add_argument(
    "--model", type=str, required=True, help="The model to use for this perf test."
)

args.add_argument(
    "--template", type=str, default="auto", help="The template name of model"
)

args.add_argument(
    "--timeout",
    type=int,
    default=90,
    help="The amount of time to run the load test for. (default: %(default)s)",
)

args.add_argument(
    "--results-dir",
    type=str,
    default="",
    help=(
        "The directory to save the results to. "
        "(`default: %(default)s`) No results are saved)"
    ),
)

args.add_argument(
    "--ray-address",
    type=str,
    default="auto",
    help=(
        "The ray address to connect to. by default, the value is auto."         
    ),
)


if __name__ == "__main__":
    args = args.parse_args()

    # env_vars = dict(os.environ)
    # ray.init(runtime_env={"env_vars": env_vars})            
    ray.init(address=args.ray_address,namespace="default",ignore_reinit_error=True)
    # Parse user metadata.
    
    llm = ByzerLLM()                   
    llm.setup_template(args.model,args.template) 
    llm.setup_default_model_name(args.model)

    
    explains = ByzerLLMPerfExplains(llm,args.results_dir)
    num_concurrent_requests = explains.num_concurrent_requests
    t,context = explains.run()  
    print()
    print()
    title = f"==========num_concurrent_requests:{num_concurrent_requests}=============" 
    print(context)
    print(title)
    print(t)    
        
    