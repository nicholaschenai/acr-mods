# declare tasks n models here so can easily swap around
MODEL_NAME="gpt-3.5-turbo-1106"
#MODEL_NAME="gpt-4o-2024-05-13"
#MODEL_NAME="gpt-4o-mini-2024-07-18"
TASK_NAME="django__django-14608"
#TASK_NAME="sphinx-doc__sphinx-10451"

PYTHONPATH=. python app/main.py swe-bench --model $MODEL_NAME --setup-map ../SWE-bench/setup_result/setup_map.json \
--tasks-map ../SWE-bench/setup_result/tasks_map.json --output-dir output \
--task $TASK_NAME \
--enable-validation \
--run_result wrong_patch \
--agent_mode multi_attempt \
--verbose \
--use_agent

#--enable-perfect-angelic \