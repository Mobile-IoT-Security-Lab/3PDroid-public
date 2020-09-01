import os
import glob
import json


if __name__ == '__main__':
    file_path_logs = os.path.join(os.getcwd(), "logs")
    list_file_in_logs = glob.glob(os.path.join(file_path_logs, "*"))

    md5_dir_list = list(filter(lambda x: os.path.isdir(x), list_file_in_logs))
    index = 0

    app_clean_with_pp_on_google_play = 0
    app_clean_without_pp_on_google_play = 0
    app_compliant_with_pp_on_google_play = 0
    app_compliant_without_pp_on_google_play = 0
    app_not_compliant_with_pp_on_google_play = 0
    app_not_compliant_without_pp_on_google_play = 0
    apps_no_more_on_google_play = 0
    app_not_analyzed = 0

    while (index < len(md5_dir_list)):
        print(f"{index+1}/{len(md5_dir_list)}")
        md5_dir = md5_dir_list[index]
        md5 = md5_dir.rsplit(os.sep, 1)[-1].split(".json")[0]
        file_name = os.path.join(f"{md5_dir}",f"{md5}.json")
        if os.path.exists(file_name):
            dict_app = json.load(open(file_name, "r"))
            if "privacy_policy_page_detected_google_play" in dict_app and dict_app["privacy_policy_page_detected_google_play"] == True:
                if "dynamic_analysis_needed" in dict_app and not dict_app["dynamic_analysis_needed"]:
                    app_clean_with_pp_on_google_play += 1
                elif "final_compliant" in dict_app and dict_app["final_compliant"]:
                    app_compliant_with_pp_on_google_play += 1
                elif "app_analyzed" in dict_app and dict_app["app_analyzed"] and (not dict_app["app_is_compliant_with_google_play_store"] or ("final_compliant" in dict_app and not dict_app["final_compliant"])):
                    app_not_compliant_with_pp_on_google_play += 1

            elif "privacy_policy_page_detected_google_play" in dict_app and dict_app["privacy_policy_page_detected_google_play"] == False:
                if "dynamic_analysis_needed" in dict_app and not dict_app["dynamic_analysis_needed"]:
                    app_clean_without_pp_on_google_play += 1
                elif "final_compliant" in dict_app and dict_app["final_compliant"]:
                    app_compliant_without_pp_on_google_play += 1
                elif "app_analyzed" in dict_app and dict_app["app_analyzed"] and (not dict_app["app_is_compliant_with_google_play_store"] or ("final_compliant" in dict_app and not dict_app["final_compliant"])):
                    app_not_compliant_without_pp_on_google_play += 1

            elif "privacy_policy_page_detected_google_play" in dict_app and dict_app["privacy_policy_page_detected_google_play"] == "Error":
                apps_no_more_on_google_play += 1
        index += 1

    print(f"- app clean with PP su google play: {app_clean_with_pp_on_google_play}")
    print(f"- app clean without PP su google play: {app_clean_without_pp_on_google_play}")
    print(f"- app compliant with PP su GP: {app_compliant_with_pp_on_google_play}")
    print(f"- app compliant without PP su GP: {app_compliant_without_pp_on_google_play}")
    print(f"- app NOT compliant with PP on GP: {app_not_compliant_with_pp_on_google_play}")
    print(f"- app NOT compliant without PP on GP: {app_not_compliant_without_pp_on_google_play}")
    print(f"- app NOT more on GP: {apps_no_more_on_google_play}")