import json
import os
import glob
from tqdm import tqdm
import sys
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO")


def start_check_analysis_CREvaluator():
    dir_results_cr_evaluator = os.path.join(os.getcwd(), "manual_validation","cr_to_manual_analyze")
    # dir_results_cr_evaluator = os.path.join(os.getcwd(), "cr_evaluator_results")
    file_mapping_practices_results = os.path.join(os.getcwd(), "resources", "cr_evaluator_model",
                                                  "mapping_practices_permissions.json")
    list_file_cr_evaluator = glob.glob(os.path.join(dir_results_cr_evaluator, "*.json"))
    list_file_cr_evaluator.remove(os.path.join(dir_results_cr_evaluator, "results.json"))

    json_file_mapping = json.load(open(file_mapping_practices_results, "r"))
    file_permissions_privacy_relevant = os.path.join(os.getcwd(), "resources", "cr_evaluator_model",
                                                     "permissions_privacy_relevant_crevaluator.txt")

    file_stats_finals = os.path.join(os.getcwd(), "final_results", "cr_evaluator_stats.json")

    with open(file_permissions_privacy_relevant, "r") as file_open:
        content = file_open.readlines()
        content = [x.strip() for x in content]
    permissions_privacy_relevant = content

    app_with_pp = len(list_file_cr_evaluator)
    app_not_compliant_description = 0
    app_compliant_with_description = 0
    app_not_compliant_description_third_party = 0
    app_compliant_with_description_third_party = 0
    app_that_declared_the_use_of_third_party_lib = 0
    app_that_does_not_use_third_party_lib = 0
    dict_language = {}
    practices_used = {}
    app_not_compliant = 0
    app_only_description_not_compliant = 0
    app_only_third_party_description_not_compliant = 0
    for file_json_cr_evaluator in tqdm(list_file_cr_evaluator, file=sys.stdout):

        json_content_file = json.load(open(file_json_cr_evaluator, "r"))
        logger.debug(json_content_file)
        print(file_json_cr_evaluator)

        analysis_sentences_list = json_content_file["analysis_sentence"]
        app_permissions = json_content_file["permission_requested"]
        app_tracker = json_content_file["trackers_inside"]
        permission_app_privacy_relevant = list(set(app_permissions).intersection(permissions_privacy_relevant))
        logger.debug(f"{permissions_privacy_relevant}, {app_permissions}, {permission_app_privacy_relevant}")
        if json_content_file["language"] in dict_language:
            dict_language[json_content_file["language"]] += 1
        else:
            dict_language[json_content_file["language"]] = 1
        permission_related_to_privacy_information = list()
        use_third_party_libraries = False
        practices_described_in_the_app = set()
        for analysis_sentence in analysis_sentences_list:
            # analysis_sentence contains 4 elements
            # sentence,
            # privacy_information,
            # privacy_information_performed_or_not,
            # privacy_information_first_party_third_party
            # we check only the sentences where the model says that the information is performed now
            if analysis_sentence["privacy_information_performed_or_not"] == "performed":
                use_third_party_libraries = analysis_sentence[
                                                "privacy_information_first_party_third_party"] == "third_party" \
                                            or \
                                            use_third_party_libraries

                privacy_information_performed = analysis_sentence["privacy_information"][0]

                for privacy_id in privacy_information_performed:
                    permission_related_to_privacy_information = permission_related_to_privacy_information + \
                                                                json_file_mapping[privacy_id]
                    # store all most used privacy_practices within app
                    practices_described_in_the_app.add(privacy_id)

        permission_related_to_privacy_information = list(set(permission_related_to_privacy_information))
        # update frequency used in the app set
        for privacy_id in practices_described_in_the_app:
            if privacy_id not in practices_used:
                practices_used[privacy_id] = 1
            else:
                practices_used[privacy_id] += 1

        app_that_declared_the_use_of_third_party_lib += int(use_third_party_libraries)
        # check if the app is compliant or not
        if not set(permission_app_privacy_relevant).issubset(set(permission_related_to_privacy_information)):
            logger.debug(f"WARNING!! {permission_app_privacy_relevant}, {permission_related_to_privacy_information}")
            json_content_file["policy_page_compliant"] = False
            app_not_compliant_description += 1
        else:
            json_content_file["policy_page_compliant"] = True
            app_compliant_with_description += 1

        if not use_third_party_libraries and len(app_tracker) > 0:
            json_content_file["policy_page_compliant_third_party"] = False
            app_not_compliant_description_third_party += 1
        elif use_third_party_libraries and len(app_tracker) > 0:
            json_content_file["policy_page_compliant_third_party"] = True
            app_compliant_with_description_third_party += 1
        else:
            json_content_file["policy_page_compliant_third_party"] = True
            app_that_does_not_use_third_party_lib += 1
        # update json dict
        app_only_description_not_compliant += int( json_content_file["policy_page_compliant_third_party"] and not json_content_file["policy_page_compliant"])
        app_only_third_party_description_not_compliant += int( not
            json_content_file["policy_page_compliant_third_party"] and json_content_file["policy_page_compliant"])

        app_not_compliant += int( not json_content_file["policy_page_compliant_third_party"] or not json_content_file["policy_page_compliant"])
        json.dump(json_content_file, open(file_json_cr_evaluator, "w"), indent=4)

    key_reorderd = sorted(practices_used, key=practices_used.get, reverse=True)
    practices_used_reordered = {}
    for key in key_reorderd:
        practices_used_reordered[key] = practices_used[key]
    dict_stats_final = {
        "Apps_Analyzed_With_PP": app_with_pp,
        # Apps that request more permission than described in the pp
        "App_Not_Compliants_with_Desc_and_Perm": app_not_compliant_description,
        "App_Compliants_with_Desc_and_Perm": app_compliant_with_description,
        # Apps that does not declared any third party libraries but used within app
        "App_Not_Compliants_with_Desc_and_3rd_Party_Lib": app_not_compliant_description_third_party,
        # app that declared the use of third party
        "App_Compliants_with_Desc_and_3rd_Party_Lib": app_compliant_with_description_third_party,
        "App_Does_Not_Use_3rd_Party_Lib": app_that_does_not_use_third_party_lib,
        "App_Declared_Use_3rd_Party_Lib": app_that_declared_the_use_of_third_party_lib,
        "Language in PP": dict_language,
        # Practices and their frequency
        "Practices": practices_used_reordered
    }
    # json.dump(dict_stats_final, open(file_stats_finals, "w"), indent=4)
    logger.info(
        f"APP NOT COMPLIANT WITH DESCRIPTION {app_not_compliant_description}, APP NOT COMPLIANT THIRD PARTY {app_not_compliant_description_third_party}, TOTAL APP NOT COMPLIANT {app_not_compliant}, ONLY PSI {app_only_description_not_compliant}, ONLY 3rdParty {app_only_third_party_description_not_compliant}")


if __name__ == "__main__":
    start_check_analysis_CREvaluator()
