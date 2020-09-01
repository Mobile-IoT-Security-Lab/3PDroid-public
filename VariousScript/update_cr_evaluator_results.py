import os
import glob
import json
from  tqdm import  tqdm

if __name__ == '__main__':
    path_cr_to_evaluate = os.path.join(os.getcwd(), "manual_validation", "cr_to_manual_analyze")
    list_all_json_results = glob.glob(os.path.join(path_cr_to_evaluate, "*.json"))
    list_all_json_results.remove(os.path.join(path_cr_to_evaluate, "results.json"))
    final_app_compliant = 0
    for json_result_file in tqdm(list_all_json_results):
        json_result_cr = json.load(open(json_result_file, "r"))
        md5_app = json_result_cr["md5_app"]

        cr1_psi_compliant = json_result_cr["policy_page_compliant"] if "policy_page_compliant" in json_result_cr else False
        cr1_third_party_compliant = json_result_cr[
            "policy_page_compliant_third_party"] if "policy_page_compliant_third_party" in json_result_cr else False

        file_to_update = os.path.join(os.getcwd(), "logs", md5_app, f"{md5_app}.json")
        dict_log = json.load(open(file_to_update, "r"))
        dict_log["policy_page_compliant_third_party"] = cr1_third_party_compliant
        dict_log["policy_page_compliant"] = cr1_psi_compliant
        dict_log["final_compliant"] = dict_log["app_is_compliant_with_google_play_store"] and dict_log["policy_page_compliant_third_party"] and dict_log["policy_page_compliant"]
        final_app_compliant += int(dict_log["final_compliant"] )
        json.dump(dict_log, open(file_to_update, "w"), indent=4)

    print(f"Final App Compliant {final_app_compliant}")