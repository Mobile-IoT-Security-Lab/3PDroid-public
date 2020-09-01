echo "START CHECKING EXPLICIT ACCEPTANCE"
python3 explicit_acceptance_policy_page.py
echo "UPDATE RESULTS EXPERIMENTS AND COMPUTE FINAL RESULTS"
python3 update_stats_experiments.py
echo "COMPUTING CREvaluator"
python3 CREvaluator.py
echo "Analyzing CR"
python3 check_CREvaluator_results.py