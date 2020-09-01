import os
import glob
import json
from tqdm import tqdm

if __name__ == "__main__":
    path_log = os.path.join(os.getcwd(), "logs")
    dir_inside_log = [x[0] for x in os.walk(path_log)]
    dir_inside_log.pop(0)

    all_logs_analysis = list()
    # update data and api monitored
    number_app_with_privacy_relevant_api_but_not_pp = 0
    number_app_with_privacy_relevant_api_and_pp = 0

    for index in tqdm(range(0, len(dir_inside_log))):
        dir = dir_inside_log[index]
        md5_app = dir.split(os.sep)[-1]
        log_file = os.path.join(dir, "{}.json".format(md5_app))
        dict_log_analysis = json.load(open(log_file))
        if "app_analyzed" in dict_log_analysis and dict_log_analysis[
            "app_analyzed"] and "app_is_compliant_with_google_play_store" in dict_log_analysis and not \
                dict_log_analysis["app_is_compliant_with_google_play_store"]:
            if "privacy_policy_page_detected" in dict_log_analysis and dict_log_analysis["privacy_policy_page_detected"]:
                num_api_different = 1 if "different_api_invoked" in dict_log_analysis and dict_log_analysis[
                    "different_api_invoked"] > 0 else 0
                number_app_with_privacy_relevant_api_and_pp += 1
            elif "privacy_policy_page_detected" in dict_log_analysis and not dict_log_analysis["privacy_policy_page_detected"]:
                num_api_different = 1 if "different_api_invoked" in dict_log_analysis and dict_log_analysis[
                    "different_api_invoked"] > 0 else 0
                number_app_with_privacy_relevant_api_but_not_pp += 1

    path_final_file = os.path.join(os.getcwd(), "final_results", "log_analysis_final.json")
    final_results_dict = json.load(open(path_final_file))

    final_results_dict["number_app_with_privacy_relevant_api_and_pp"] = number_app_with_privacy_relevant_api_and_pp
    final_results_dict["number_app_with_privacy_relevant_api_but_not_pp"] = number_app_with_privacy_relevant_api_but_not_pp

    json.dump(final_results_dict, open(path_final_file, "w"), indent=4)

    path_logs = os.path.join(os.getcwd(), "logs","log_analysis_1.json")
    json.dump(final_results_dict, open(path_logs, "w"), indent=4)