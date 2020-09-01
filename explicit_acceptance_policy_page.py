import os
import glob
import json
import hashlib
import collections
from tqdm import tqdm
import logging
import app_analyzer
import sys
from loguru import logger

string_explicit_acceptance = ["agree", "i agree", "continue", "yes, i agree", "accept", "accept all", "ok"]

def check_if_all_privacy_policy_page_contains_explicit_acceptance():
    logger.info("Start Analysis to find all privacy policy page without explicit acceptance")
    # All dir inside log directory
    path_log = os.path.join(os.getcwd(), "logs")
    dir_inside_log = [x[0] for x in os.walk(path_log)]
    dir_inside_log.pop(0)
    number_of_app_analyzed = len(dir_inside_log)

    dict_md5_app_privacy_policy_page = {}
    contain_explicit_acceptance = 0
    app_with_privacy_policy = 0
    for dir_app in tqdm(dir_inside_log, file=sys.stdout):
        md5_app = dir_app.split(os.sep)[-1]
        json_file = os.path.join(dir_app, f"{md5_app}.json")
        if os.path.exists(json_file):
            analysis_json = json.load(open(json_file))
            if "privacy_policy_page_detected" in analysis_json and analysis_json["privacy_policy_page_detected"]:
                app_with_privacy_policy += 1
                md5_privacy_policy_page = analysis_json["privacy_policy_page_md5"]
                dict_md5_app_privacy_policy_page[md5_app] = {
                    "md5_privacy_policy_page": md5_privacy_policy_page,
                    "content_xml_privacy_policy_page": "",
                    "content_cleaned_privacy_policy_page": ""
                }

                dir_privacy_policy_page = os.path.join(os.getcwd(), "privacypoliciesxml")
                file_name_xml = os.path.join(dir_privacy_policy_page, f"{md5_app}_{md5_privacy_policy_page}.xml")
                file_name_cleaned = os.path.join(dir_privacy_policy_page,
                                                 f"{md5_app}_{md5_privacy_policy_page}_cleaned.txt")
                content_file_xml = ""
                content_cleaned_privacy_policy_page = ""

                if os.path.exists(file_name_xml):
                    file_object = open(file_name_xml, "r", encoding="utf-8", errors='ignore')
                    content_file_xml = file_object.read()
                    file_object.close()
                if os.path.exists(file_name_cleaned):
                    file_object = open(file_name_cleaned, "r", encoding="utf-8", errors='ignore')
                    content_cleaned_privacy_policy_page = file_object.read()
                    file_object.close()
                dict_md5_app_privacy_policy_page[md5_app]["content_xml_privacy_policy_page"] = content_file_xml
                dict_md5_app_privacy_policy_page[md5_app][
                    "content_cleaned_privacy_policy_page"] = content_cleaned_privacy_policy_page

                found = False
                for value in string_explicit_acceptance:
                    if value in dict_md5_app_privacy_policy_page[md5_app]["content_cleaned_privacy_policy_page"].lower():
                        dict_md5_app_privacy_policy_page[md5_app]["contain_explicit_acceptance"] = True
                        analysis_json["privacy_policy_contain_explicit_acceptance"] = True
                        found = True
                        contain_explicit_acceptance += 1
                        break
                if not found:
                    dict_md5_app_privacy_policy_page[md5_app]["contain_explicit_acceptance"] = False
                    analysis_json["privacy_policy_contain_explicit_acceptance"] = False

                if analysis_json["app_is_compliant_with_google_play_store"] and not  analysis_json["privacy_policy_contain_explicit_acceptance"]:
                    analysis_json["app_is_compliant_with_google_play_store"] = False
                json.dump(analysis_json, open(json_file, "w"), indent=4)

    logger.info(f"App with privacy policy {app_with_privacy_policy}, apps with explicit acceptance {contain_explicit_acceptance}")


if __name__ == "__main__":
    check_if_all_privacy_policy_page_contains_explicit_acceptance()
