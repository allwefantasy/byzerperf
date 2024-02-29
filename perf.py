import argparse
import json
import ray
from byzerperf.perf import ByzerLLMPerf

args = argparse.ArgumentParser(description="Run a correctness test for a given model.")

args.add_argument(
    "--model", type=str, required=True, help="The model to use for this perf test."
)
args.add_argument(
    "--num-concurrent-requests",
    type=int,
    default=5,
    help=("The number of concurrent requests to send. (default: %(default)s)"),
)
args.add_argument(
    "--timeout",
    type=int,
    default=90,
    help="The amount of time to run the load test for. (default: %(default)s)",
)
args.add_argument(
    "--max-num-completed-requests",
    type=int,
    default=50,
    help=(
        "The number of requests to complete before finishing the test. Note "
        "that its possible for the test to timeout first. (default: %(default)s)"
    ),
)
args.add_argument(
    "--additional-sampling-params",
    type=str,
    default="{}",
    help=(
        "Additional sampling params to send with the each request to the LLM API. "
        "(default: %(default)s) No additional sampling params are sent."
    ),
)

args.add_argument(
    "--prompts-dir",
    type=str,
    required=True,
    help=(
        "The directory to get the prompts from."        
    ),
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
    "--metadata",
    type=str,
    default="",
    help=(
        "A comma separated list of metadata to include in the results, e.g. "
        "name=foo,bar=1. These will be added to the metadata field of the results. "
    ),
)

args.add_argument(
    "--tasks_use_ray",
    type=bool,
    default=False,
    help=(
        "The perf task will be launched using ray, otherwise it will be executed by conccurent.ProcessPoolExecutor. "        
    ),
)

if __name__ == "__main__":
    args = args.parse_args()

    # env_vars = dict(os.environ)
    # ray.init(runtime_env={"env_vars": env_vars})
    ray.init(address="auto",namespace="default",ignore_reinit_error=True)
    # Parse user metadata.
    user_metadata = {}
    if args.metadata:
        for item in args.metadata.split(","):
            key, value = item.split("=")
            user_metadata[key] = value

    byzer_llm_perf = ByzerLLMPerf(
        model=args.model,
        timeout=args.timeout,
        max_num_completed_requests=args.max_num_completed_requests,
        num_concurrent_requests=args.num_concurrent_requests,
        additional_sampling_params=json.loads(args.additional_sampling_params),
        results_dir=args.results_dir,
        user_metadata=json.loads(user_metadata),
        tasks_use_ray=args.tasks_use_ray,
        prompts_dir=args.prompts_dir
    )        

    results = byzer_llm_perf.run()