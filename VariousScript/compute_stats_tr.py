import os
import glob
import json
from tqdm import tqdm
if __name__ == '__main__':
    file_path_logs = os.path.join(os.getcwd(), "logs")
    list_file_in_logs = glob.glob(os.path.join(file_path_logs, "*"))
    md5_dir_list = list(filter(lambda x: os.path.isdir(x), list_file_in_logs))
    tr3_explicit_acceptance = 0
    tr4_api = 0
    tr5_home_back_button = 0
    tr6_timeout = 0

    for md5_dir in tqdm(md5_dir_list):
        md5 = md5_dir.rsplit(os.sep, 1)[-1].split(".json")[0]
        file_name = os.path.join(f"{md5_dir}", f"{md5}.json")
        if os.path.exists(file_name):
            dict_app = json.load(open(file_name, "r"))
            if "app_analyzed" in dict_app and dict_app["app_analyzed"] and dict_app["privacy_policy_page_detected"] and "app_is_compliant_with_google_play_store" in dict_app and not dict_app[
                "app_is_compliant_with_google_play_store"]:

                if "privacy_policy_contain_explicit_acceptance" in dict_app and not dict_app["privacy_policy_contain_explicit_acceptance"]:
                    tr3_explicit_acceptance +=1
                elif "timeout_privacy_policy_page" in dict_app and dict_app["timeout_privacy_policy_page"]:
                    tr6_timeout += 1
                elif ("home_button_change_privacy_policy_page" in dict_app and dict_app["home_button_change_privacy_policy_page"]) or ("back_button_change_privacy_policy_page" in dict_app and dict_app["back_button_change_privacy_policy_page"]):
                    tr5_home_back_button += 1
                elif "different_api_invoked" in dict_app and dict_app["different_api_invoked"] > 0:
                    tr4_api += 1


    print(f"TR3 Failed {tr3_explicit_acceptance}")
    print(f"TR4 Failed {tr4_api}")
    print(f"TR5 Failed {tr5_home_back_button}")
    print(f"TR6 Failed {tr6_timeout}")

