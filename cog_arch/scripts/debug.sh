# declare tasks n models here so can easily swap around
#MODEL_NAME="gpt-3.5-turbo-1106"
MODEL_NAME="gpt-4o-2024-05-13"
TASK_NAME="sphinx-doc__sphinx-10451"

PYTHONPATH=. python app/main.py swe-bench --model $MODEL_NAME --setup-map ../SWE-bench/setup_result/setup_map.json --tasks-map ../SWE-bench/setup_result/tasks_map.json --output-dir output \
--task $TASK_NAME \
--enable-validation \
--enable-perfect-angelic \
--use_agent