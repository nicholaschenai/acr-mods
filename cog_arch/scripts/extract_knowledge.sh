MODEL_NAME="gpt-3.5-turbo-1106"
#MODEL_NAME="gpt-4o-2024-05-13"

PYTHONPATH=. python app/cog_arch/scripts/extract_knowledge.py \
--model $MODEL_NAME \
--output-dir output \
--use_agent \
--verbose \
--debug_mode