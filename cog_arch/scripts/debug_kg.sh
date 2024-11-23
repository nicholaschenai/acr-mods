# declare tasks n models here so can easily swap around
#MODEL_NAME="gpt-3.5-turbo-1106"
# MODEL_NAME="gpt-4o-2024-05-13"
MODEL_NAME="gpt-4o-mini-2024-07-18"
# TASK_NAME="django__django-14608"
#TASK_NAME="sphinx-doc__sphinx-10451"

PYTHONPATH=. python cog_arch/scripts/kg_construct.py \
--model $MODEL_NAME \
--output-dir output/kg \
--use_agent \
--agent_mode kg \
--edge_include_nodes \
--verbose \
--debug_mode
#--task $TASK_NAME \