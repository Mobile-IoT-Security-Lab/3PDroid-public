import os
import glob
import json
import hashlib
import collections
from tqdm import tqdm
import logging
import app_analyzer
import sys

if 'LOG_LEVEL' in os.environ:
    log_level = os.environ['LOG_LEVEL']
else:
    log_level = logging.INFO

# Logging configuration.
logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s> [%(levelname)s][%(name)s][%(funcName)s()] %(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S', level=log_level, stream=sys.stdout)


class ApiSet(dict):

    # This class is used to create a hashable dict, in order to avoid adding more than once the same
    # code for a certain vulnerability (this can happen with multi-dex, when the manifest is analyzed
    # once for every dex, so the same manifest vulnerability would be added as many times as the
    # number of dex files contained in the application).

    def __hash__(self):
        return hash((frozenset(self), frozenset(self.values())))


def update_api_privacy_relevant_and_all_log_files():
    """
        Da usare nel caso si cambiassero le api privacy relevant delle app
    Returns
    -------

    """
    permission_api_mapping = app_analyzer.get_api_related_to_permission_privacy_relevant()
    path_mapping_libraries_name_file = os.path.join(os.getcwd(), "resources", "mapping_libraries_api_file.txt")
    dir_api_libraries = os.path.join(os.getcwd(), "resources", "api_libraries")
    path_log = os.path.join(os.getcwd(), "logs")
    dir_inside_log = [x[0] for x in os.walk(path_log)]
    dir_inside_log.pop(0)

    # from library name obtain file_name
    dict_trackers_filename = {}
    with open(path_mapping_libraries_name_file, "r") as file_mapping_libraries:
        contents = file_mapping_libraries.readlines()
        contents = [x.strip() for x in contents]
        for line in contents:
            dict_trackers_filename[line.split(",")[0]] = os.path.join(dir_api_libraries, line.split(",")[1])

    # for each app analyzed
    all_logs_analysis = list()
    # update data and api monitored
    logger.info("Start update_api_privacy_relevant_and_all_log_files")
    for index in tqdm(range(0, len(dir_inside_log))):
        dir = dir_inside_log[index]
        md5_app = dir.split(os.sep)[-1]
        log_file = os.path.join(dir, "{}.json".format(md5_app))
        api_file = os.path.join(dir, "monitoring_api_{}.json".format(md5_app))

        dict_log_analysis = json.load(open(log_file))
        list_api_privacy_relevant = list()
        list_trackers_inside_app = dict_log_analysis["trackers_inside"] if "trackers_inside" in dict_log_analysis else []
        permission_app = dict_log_analysis["permission_requested"] if "permission_requested" in dict_log_analysis else []
        # if the app has been analyzed in a dynamic way
        if os.path.exists(api_file):

            list_dict_api = json.load(open(api_file))
            # for each tracker inside app obtain all api privacy relevants
            all_api_trackers = []
            for tracker in list_trackers_inside_app:
                if tracker in dict_trackers_filename:
                    path_file_to_read = dict_trackers_filename[tracker]
                    with open(path_file_to_read, "r") as file_api_trackers:
                        content = file_api_trackers.readlines()
                        content = [x.strip() for x in content]
                        all_api_trackers = all_api_trackers + content
            # create a list of tuple for all api privacy relevant
            for api_trackers in all_api_trackers:
                list_api_privacy_relevant.append((api_trackers.split(",")[0], api_trackers.split(",")[1]))

            for permission_key, value in permission_api_mapping.items():
                for permission in permission_app:
                    if permission in permission_key:
                        # for each method related to this permission append to list to monitoring
                        for tuple_class_name_api in value:
                            list_api_privacy_relevant.append(tuple_class_name_api)

            # obtain all api monitored during dynamic analysis
            api_monitored = list()
            for dict_api in list_dict_api:
                api_monitored.append((dict_api["className"], dict_api["method"]))

            api_monitored_without_duplicated = set(api_monitored)
            list_api_privacy_relevant = set(list_api_privacy_relevant)
            api_privacy_relevant_invoked_by_app = list_api_privacy_relevant.intersection(
                api_monitored_without_duplicated)

            # change different api invoked
            dict_log_analysis["different_api_invoked"] = len(api_privacy_relevant_invoked_by_app)
            # update if the app is complaint or not
            dict_log_analysis["app_is_compliant_with_google_play_store"] = dict_log_analysis[
                                                                               "privacy_policy_page_detected"] and not \
                                                                               (
                                                                                       len(
                                                                                           api_privacy_relevant_invoked_by_app) > 0 or
                                                                                       dict_log_analysis[
                                                                                           "timeout_privacy_policy_page"] or
                                                                                       dict_log_analysis[
                                                                                           "home_button_change_privacy_policy_page"] or
                                                                                       dict_log_analysis[
                                                                                           "back_button_change_privacy_policy_page"]
                                                                               )

            # update list of api
            list_dict_api_new = []
            for index_dict in range(0, len(list_dict_api)):
                dict_api = list_dict_api[index_dict]
                if (dict_api["className"], dict_api["method"]) in list(list_api_privacy_relevant):
                    list_dict_api_new.append(dict_api)
            dict_log_analysis["api_invoked_during_dynamic_analysis"] = len(list_dict_api)
            update_json_file(log_file, dict_log_analysis)

            if len(list_dict_api) > 0:
                json.dump(list_dict_api_new, open(api_file, "w"), indent=4)

        all_logs_analysis.append(dict_log_analysis)

    ##################################################################################################################
    ############################################### NOW COMPUTE STATS ################################################
    ##################################################################################################################
    logger.info("Compute final stats")
    stats_final = \
        {
            "Apps Analyzed": len(all_logs_analysis),
            "Type of Interaction": "Droidbot",
            "Apps with privacy policy page": 0,
            "Apps with timeout mechanism": 0,
            "Apps with home button accepts": 0,
            "Apps with back button accepts": 0,
            "Apps cleaned": 0,
            "Apps not analyzed": 0,
            "Apps compliant": 0,
            "Apps not compliant": 0,
            "Apps with explicit acceptance": 0,
            "Mean action to reach privacy policy page": 0.0,
            "Mean api invoked (privacy relevant)": 0.0
        }

    action_to_reach_privacy_policy = 0
    api_invoked = 0
    apps_analyzed = 0
    api_different_invoked = 0
    for dict_log_analysis in all_logs_analysis:
        if "dynamic_analysis_needed" not in dict_log_analysis:
            if "app_analyzed" in dict_log_analysis and dict_log_analysis["app_analyzed"]:

                stats_final["Apps with privacy policy page"] += int(
                    dict_log_analysis["privacy_policy_page_detected"])

                stats_final["Apps with timeout mechanism"] += int(
                    dict_log_analysis["timeout_privacy_policy_page"])

                stats_final["Apps with home button accepts"] += int(
                    dict_log_analysis["home_button_change_privacy_policy_page"])

                stats_final["Apps with back button accepts"] += int(
                    dict_log_analysis["back_button_change_privacy_policy_page"])

                stats_final["Apps compliant"] += int(
                    dict_log_analysis["app_is_compliant_with_google_play_store"])

                stats_final["Apps not compliant"] += int(
                    not dict_log_analysis["app_is_compliant_with_google_play_store"])

                if "privacy_policy_contain_explicit_acceptance" in dict_log_analysis:
                    stats_final["Apps with explicit acceptance"] += int(
                        dict_log_analysis["privacy_policy_contain_explicit_acceptance"])

                apps_analyzed += 1

                if "api_invoked_during_dynamic_analysis" in dict_log_analysis:
                    api_invoked += dict_log_analysis["api_invoked_during_dynamic_analysis"]
                if "actions_needed_to_reach_privacy_policy" in dict_log_analysis:
                    action_to_reach_privacy_policy += dict_log_analysis["actions_needed_to_reach_privacy_policy"] + 1
                if "different_api_invoked" in dict_log_analysis:
                    api_different_invoked += dict_log_analysis["different_api_invoked"]

            else:
                stats_final["Apps not analyzed"] += 1
        else:
            stats_final["Apps cleaned"] += 1

    stats_final["Mean action to reach privacy policy page"] = action_to_reach_privacy_policy / apps_analyzed
    stats_final["Mean api invoked (privacy relevant)"] = api_invoked / apps_analyzed
    stats_final["Mean different api invoked (privacy relevant)"] = api_different_invoked / apps_analyzed

    path_file_log_final = os.path.join(os.getcwd(), "final_results", "log_analysis_final.json")
    json.dump(stats_final, open(path_file_log_final, "w"), indent=4)

    # update all json on final results
    path_dir = os.path.join(os.getcwd(), "logs")
    files_log = glob.glob(os.path.join(path_dir, "log_analysis_*"))
    files_permissions_stats = glob.glob(os.path.join(path_dir, "permissions_stats_*"))
    files_tracker_stats = glob.glob(os.path.join(path_dir, "tracker_stats_*"))

    dict_final_permissions_stats = {}
    dict_final_tracker_stats = {}
    logger.info("Compute all final stats files: permission")
    for index_file in tqdm(range(0, len(files_permissions_stats))):
        file_log = files_permissions_stats[index_file]
        dict_permissions_stats = json.load(open(file_log))
        if not dict_final_permissions_stats:
            dict_final_permissions_stats = dict_permissions_stats
        else:
            for key_2, value_2 in dict_permissions_stats.items():
                if key_2 not in dict_final_permissions_stats:
                    dict_final_permissions_stats[key_2] = value_2
                else:
                    dict_final_permissions_stats[key_2] = dict_permissions_stats[key_2] + \
                                                          dict_final_permissions_stats[
                                                              key_2]

    path_permission_final = os.path.join(os.getcwd(), "final_results", "permission_stats_final.json")
    json.dump(dict_final_permissions_stats, open(path_permission_final, "w"), indent=4)

    logger.info("Compute all final stats files: trackers")
    for index_file in tqdm(range(0, len(files_tracker_stats))):
        file_log = files_tracker_stats[index_file]
        dict_tracker_stats = json.load(open(file_log))
        if not dict_final_tracker_stats:
            dict_final_tracker_stats = dict_tracker_stats
        else:
            for key_2, value_2 in dict_tracker_stats.items():
                if key_2 not in dict_final_tracker_stats:
                    dict_final_tracker_stats[key_2] = value_2
                else:
                    dict_final_tracker_stats[key_2] = dict_tracker_stats[key_2] + dict_final_tracker_stats[key_2]
    path_tracker_finale = os.path.join(os.getcwd(), "final_results", "trackers_stats_final.json")
    json.dump(dict_final_tracker_stats, open(path_tracker_finale, "w"), indent=4)

    # remove file on logs dir
    for file_log in files_log:
        os.remove(file_log)
    for file_log in files_tracker_stats:
        os.remove(file_log)
    for file_log in files_permissions_stats:
        os.remove(file_log)

    # store on file
    file_log_analysis = os.path.join(os.getcwd(), "logs", "log_analysis_1.json")
    file_permission_analysis = os.path.join(os.getcwd(), "logs", "permissions_stats_1.json")
    file_tracker_analysis = os.path.join(os.getcwd(), "logs", "tracker_stats_1.json")

    json.dump(stats_final, open(file_log_analysis, "w"), indent=4)
    json.dump(dict_final_permissions_stats, open(file_permission_analysis, "w"), indent=4)
    json.dump(dict_final_tracker_stats, open(file_tracker_analysis, "w"), indent=4)


def stats_analysis():
    logger.info("Compute all final stats files")
    path_dir = os.path.join(os.getcwd(), "logs")
    files_log = glob.glob(os.path.join(path_dir, "log_analysis_*"))
    files_permissions_stats = glob.glob(os.path.join(path_dir, "permissions_stats_*"))
    files_tracker_stats = glob.glob(os.path.join(path_dir, "tracker_stats_*"))

    dict_final_log_analysis = {}
    dict_final_permissions_stats = {}
    dict_final_tracker_stats = {}

    logger.info("Compute all final stats files: log")
    for index_file in tqdm(range(0, len(files_log))):
        file_log = files_log[index_file]

        dict_log_analysis = json.load(open(file_log))
        if not dict_final_log_analysis:
            dict_final_log_analysis = dict_log_analysis
        else:
            for key, value in dict_final_log_analysis.items():
                if key != "Type of Interaction" and "Mean" not in key:
                    dict_final_log_analysis[key] = dict_final_log_analysis[key] + \
                                                   dict_log_analysis[key]
                    if "Mean" in key:
                        dict_final_log_analysis[key] = (dict_final_log_analysis[key] + dict_log_analysis[key]) / 2
    path_file_log_final = os.path.join(os.getcwd(), "final_results", "log_analysis_final.json")
    json.dump(dict_final_log_analysis, open(path_file_log_final, "w"), indent=4)

    logger.info("Compute all final stats files: permissions")
    for index_file in tqdm(range(0, len(files_permissions_stats))):
        file_log = files_permissions_stats[index_file]
        dict_permissions_stats = json.load(open(file_log))
        if not dict_final_permissions_stats:
            dict_final_permissions_stats = dict_permissions_stats
        else:
            for key_2, value_2 in dict_permissions_stats.items():
                if key_2 not in dict_final_permissions_stats:
                    dict_final_permissions_stats[key_2] = value_2
                else:
                    dict_final_permissions_stats[key_2] = dict_permissions_stats[key_2] + dict_final_permissions_stats[
                        key_2]

    path_permission_final = os.path.join(os.getcwd(), "final_results", "permission_stats_final.json")
    json.dump(dict_final_permissions_stats, open(path_permission_final, "w"), indent=4)

    logger.info("Compute all final stats files: tracker")
    for index_file in tqdm(range(0, len(files_tracker_stats))):
        file_log = files_tracker_stats[index_file]
        dict_tracker_stats = json.load(open(file_log))
        if not dict_final_tracker_stats:
            dict_final_tracker_stats = dict_tracker_stats
        else:
            for key_2, value_2 in dict_tracker_stats.items():
                if key_2 not in dict_final_tracker_stats:
                    dict_final_tracker_stats[key_2] = value_2
                else:
                    dict_final_tracker_stats[key_2] = dict_tracker_stats[key_2] + dict_final_tracker_stats[key_2]
    path_tracker_finale = os.path.join(os.getcwd(), "final_results", "trackers_stats_final.json")
    json.dump(dict_final_tracker_stats, open(path_tracker_finale, "w"), indent=4)


def update_json_file(path_json_file: str, dict_to_add_to_analysis: dict):
    dict_analysis = json.load(open(path_json_file, "r"))
    for key, value in dict_to_add_to_analysis.items():
        dict_analysis[key] = value
    json.dump(dict_analysis, open(path_json_file, "w"), indent=4)


def stats_api_remove_duplicate():
    path_log = os.path.join(os.getcwd(), "logs")
    dir_inside_log = [x[0] for x in os.walk(path_log)]
    dir_inside_log.pop(0)
    number_of_app_analyzed = len(dir_inside_log)
    number_of_api_different = 0

    logger.info("Remove API duplicated")
    for index in tqdm(range(0, len(dir_inside_log))):
        dir = dir_inside_log[index]
        api_set = set()
        md5_app = dir.split(os.sep)[-1]
        api_file = os.path.join(dir, "monitoring_api_{}.json".format(md5_app))
        if os.path.exists(api_file):
            list_api_dict = json.load(open(api_file, "r"))
            for dict_item in list_api_dict:
                del dict_item["parameters"]
                api_set.add(ApiSet(dict_item))
            api_set_list = list(api_set)
            api_file_cleaned = os.path.join(dir, "monitoring_api_cleaned_{}.json".format(md5_app))
            json.dump(api_set_list, open(api_file_cleaned, "w"), indent=4)
            update_json_file(os.path.join(dir, "{}.json".format(md5_app)),
                             {"different_api_invoked": len(api_set_list)})
            number_of_api_different += len(api_set_list)
            update_json_file(os.path.join(os.getcwd(), "final_results", "log_analysis_final.json"),
                             {"Mean APIs Different Invoked": number_of_api_different / number_of_app_analyzed})


def main():
    update_api_privacy_relevant_and_all_log_files()
    stats_api_remove_duplicate()
    stats_analysis()


if __name__ == "__main__":
    main()
