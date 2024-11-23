# declare tasks n models here so can easily swap around
# MODEL_NAME="gpt-3.5-turbo-1106"
MODEL_NAME="gpt-4o-2024-05-13"
# MODEL_NAME="gpt-4o-mini-2024-07-18"
# TASK_NAME="django__django-14608"
#TASK_NAME="sphinx-doc__sphinx-10451"
# below has test error from single threading
# TASK_NAME="django__django-13321"
# TASK_NAME="django__django-16910"
# TASK_NAME="django__django-13220"
# TASK_NAME="django__django-16229"
TASK_NAME="django__django-12113"
# resolved
# ['django__django-16379', 'django__django-11133', 'django__django-13964', 'django__django-12497', 'django__django-13447']
# unresolved
# ['django__django-13321', 'django__django-16910', 'django__django-13220', 'django__django-16229', 'django__django-12113']

PYTHONPATH=. python app/main.py swe-bench --model $MODEL_NAME --setup-map ../SWE-bench/setup_result/setup_map.json \
--tasks-map ../SWE-bench/setup_result/tasks_map.json --output-dir output/kg \
--task $TASK_NAME \
--enable-validation \
--agent_mode kg \
--verbose \
--patch_retries 3 \
--edge_include_nodes \
--use_agent

# --debug_mode \
#--enable-perfect-angelic \
# --run_result wrong_patch \