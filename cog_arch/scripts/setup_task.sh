# declare tasks n models here so can easily swap around
#TASK_NAME="sphinx-doc__sphinx-10451"
# TASK_NAME="django__django-14608"
# ['django__django-16379', 'django__django-11133', 'django__django-13964', 'django__django-12497', 'django__django-13447']
# unresolved
# ['django__django-13321', 'django__django-16910', 'django__django-13220', 'django__django-16229', 'django__django-12113']
# TASKS=("django__django-14608" "sphinx-doc__sphinx-10451")
TASKS=(
  "django__django-14608"
  "django__django-16379"
  "django__django-11133"
  "django__django-13964"
  "django__django-12497"
  "django__django-13447"
  "django__django-13321"
  "django__django-16910"
  "django__django-13220"
  "django__django-16229"
  "django__django-12113"
)

#  initialization commands that set up conda are not executed in non-interactive shells by default.
source ~/miniconda3/etc/profile.d/conda.sh
cd /opt/SWE-bench

# echo $TASK_NAME > tasks.txt
# Write tasks to tasks.txt
> tasks.txt
for TASK in "${TASKS[@]}"; do
  echo $TASK >> tasks.txt
done

# Check if there are multiple tasks
if [[ ${#TASKS[@]} -gt 1 ]]; then
  echo "Setting up multiple tasks"
else
  echo "Setting up a single task"
fi

#cd /opt/SWE-bench
conda activate swe-bench
python harness/run_setup.py --log_dir logs --testbed testbed --result_dir setup_result --subset_file tasks.txt