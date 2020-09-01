import os
import glob
import json
from google_play_scraper import app
import time
import random

if __name__ == '__main__':
    file_path_logs = os.path.join(os.getcwd(), "logs")
    list_file_in_logs = glob.glob(os.path.join(file_path_logs, "*"))

    md5_dir_list = list(filter(lambda x: os.path.isdir(x), list_file_in_logs))
    error_app = 0
    index = 0
    tentative = 0
    app_analyzed = 0
    while (index < len(md5_dir_list)):
        print(f"{index+1}/{len(md5_dir_list)}")
        try:
            md5_dir = md5_dir_list[index]
            md5 = md5_dir.rsplit(os.sep, 1)[-1].split(".json")[0]
            file_name = os.path.join(f"{md5_dir}",f"{md5}.json")
            if os.path.exists(file_name):
                dict_app = json.load(open(file_name, "r"))
                app_analyzed += int(tentative == 0)
                print(f"App Analyzed {app_analyzed}")
                result = app(
                    dict_app["package_name"],
                )
                privacyPolicyGooglePlay = result["privacyPolicy"]
                print(privacyPolicyGooglePlay)
                if privacyPolicyGooglePlay is not None and len(privacyPolicyGooglePlay)>0:
                    dict_app["privacy_policy_page_detected_google_play"] = True
                else:
                    dict_app["privacy_policy_page_detected_google_play"] = False

            index += 1

        except Exception as e:
            print(f"Error as {e}")
            if tentative < 2:
                tentative += 1
                print("Try again on this app")
                # time.sleep(random.randint(1, 4))

            elif tentative == 2:
                index += 1
                tentative = 0
                error_app += 1
                dict_app["privacy_policy_page_detected_google_play"] = "Error"
                print("Pass next app")
                # time.sleep(random.randint(1, 4))

        json.dump(dict_app, open(file_name, "w"), indent=4)

    print(f"Error apps {error_app}")