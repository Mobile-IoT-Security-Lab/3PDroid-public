import sys
import time
from androguard.misc import AnalyzeAPK
import os
import logging
import json
import hashlib
import glob

if 'LOG_LEVEL' in os.environ:
    log_level = os.environ['LOG_LEVEL']
else:
    log_level = logging.INFO

# Logging configuration.
logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s> [%(levelname)s][%(name)s][%(funcName)s()] %(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S', level=log_level, stream=sys.stdout)


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def write_result_md5_app(md5_app, list_tracker_inside_app, list_permission, execution_time, dict_analysis_app):
    logger.info("Write result of AppAnalyzer on file")
    file_name = md5_app
    dir_result = os.path.join(os.getcwd(), "logs", file_name)

    if not os.path.exists(dir_result):
        os.makedirs(dir_result)

    permission = ",".join(list_permission) if len(list_permission) > 0 else "N.A"
    tracker = ",".join(list_tracker_inside_app) if len(list_tracker_inside_app) > 0 else "N.A"

    with open(os.path.join(dir_result, "{}.json".format(file_name)), "w") as log_analysis:
        json.dump(dict_analysis_app, log_analysis, indent=4)


def get_all_permission_privacy_relevant():
    """

    Returns only the permissions privacy relevant for Android platform
    -------

    """
    list_permission_privacy_relevant = []
    with open(os.path.join(os.getcwd(), "resources", "permissions_privacy_relevant.txt"), "r") as file:
        content = file.readlines()
        list_permission_privacy_relevant = [x.strip() for x in content]

    return list_permission_privacy_relevant


def get_api_related_to_permission_privacy_relevant():
    """
    Analyze file permission_api_mapping_cleaned.txt in order to find all methods related to these permissions
    Returns api_mapping_related_to_permissions

    -------

    """
    api_mapping = dict()
    with open(os.path.join(os.getcwd(), "resources", "permission_api_mapping_cleaned.txt"), "r") as file:
        content = file.readlines()
        content = [x.strip() for x in content]
    # create for each permission a list of tuple (class_name, method_name)
    for row in content:
        permission = (row.split("::")[0].strip().replace(" ", ""))
        api = row.split("::")[1]
        class_name = api.split(",")[0]
        method_name = api.split(",")[1]
        if permission not in api_mapping:
            api_mapping[permission] = [(str(class_name), str(method_name))]
        else:
            api_mapping[permission].append((str(class_name), str(method_name)))
    return api_mapping


def create_list_api_to_monitoring_from_file(permissions_api_mapping: dict, permissions_app: list,
                                            list_trackers_inside_app: list):
    # Third party libraries
    dir_api_libraries = os.path.join(os.getcwd(), "resources", "api_libraries")
    path_mapping_libraries_name_file = os.path.join(os.getcwd(), "resources", "mapping_libraries_api_file.txt")
    list_api_to_monitoring = []

    dict_trackers_filename = {}
    with open(path_mapping_libraries_name_file, "r") as file_mapping_libraries:
        contents = file_mapping_libraries.readlines()
        contents = [x.strip() for x in contents]
        for line in contents:
            dict_trackers_filename[line.split(",")[0]] = os.path.join(dir_api_libraries, line.split(",")[1])

    all_api_trackers = []
    for tracker in list_trackers_inside_app:
        if tracker in dict_trackers_filename:
            path_file_to_read = dict_trackers_filename[tracker]
            with open(path_file_to_read, "r") as file_api_trackers:
                content = file_api_trackers.readlines()
                content = [x.strip() for x in content]
                all_api_trackers = all_api_trackers + content

    for api_trackers in all_api_trackers:
        list_api_to_monitoring.append((api_trackers.split(",")[0], api_trackers.split(",")[1]))

    for permission_key, value in permissions_api_mapping.items():
        for permission in permissions_app:
            if permission in permission_key:
                # for each method related to this permission append to list to monitoring
                for tuple_class_name_api in value:
                    list_api_to_monitoring.append(tuple_class_name_api)

    return list(set(list_api_to_monitoring))


def create_list_api_to_monitoring(permissions_api_mapping: dict, permissions_app: list,
                                  trackers_api_to_monitoring: dict):
    """

    Parameters
    ----------
    permissions_api_mapping, mapping between permissions and api related to them
    permissions_app, app's permissions
    trackers_api_to_monitoring,

    Returns a file that contains the list of API to monitoring during dynamic analysis
    -------
    """
    list_api_to_monitoring = []
    for permission_key, value in permissions_api_mapping.items():
        for permission in permissions_app:
            if permission in permission_key:
                # for each method related to this permission append to list to monitoring
                for tuple_class_name_api in value:
                    list_api_to_monitoring.append(tuple_class_name_api)

    for package_name, value in trackers_api_to_monitoring.items():
        for tuple_class_name_api in value:
            list_api_to_monitoring.append(tuple_class_name_api)

    # a list that contains class name and method to monitoring
    return list(set(list_api_to_monitoring))


def create_api_list_frida(list_api_to_monitoring: list, output_name_file: str):
    if len(list_api_to_monitoring) > 0:
        logger.info("Creation {} file".format(output_name_file))
        file_open = open(output_name_file, "w")
        for tuple_class_api in list_api_to_monitoring:
            try:
                class_name = tuple_class_api[0]
                method_name = tuple_class_api[1] if tuple_class_api[1] != "<init>" or tuple_class_api[1] != "<clinit>" else "$init"
                file_open.write("{},{}\n".format(class_name, method_name))
            except Exception as e:
                logger.error("Error as {}".format(e))
                continue

        file_open.close()
        return True
    else:
        return False


def analyze_apk_androguard(apk_file: str, md5_app: str = None, dict_analysis_apk: dict = None):
    """

    Parameters
    ----------
    apk_file

    Returns
    -------

    """
    tracker_name_package = {}  # package name analytics to monitoring
    logger.info("Start App Analyzer")
    start = time.time()
    application, dalvik, analysis = AnalyzeAPK(apk_file)

    # read all trackers package name inside app
    with open(os.path.join(os.getcwd(), "resources", "package_name_trackers_most_used.txt"), "r") as file:
        tracker_list = file.readlines()
        tracker_list = [x.strip() for x in tracker_list]

    # creation of regular expression for searching methods inside apps
    for tracker in tracker_list:
        name = tracker.split(",")[0]
        packages = tracker.split(",")[1].split("|")
        packages_new = []
        for package in packages:
            package_new = "L" + package.replace(".", "/")
            if package_new.endswith("/"):
                package_new = package_new + ".*"
            else:
                package_new = package_new + "/.*"
            packages_new.append(package_new)
        tracker_name_package[name] = packages_new

    # creation list of API for monitoring
    n_method = 0
    list_tracker_inside_app = []
    trackers_api_to_monitoring = {}  # dict api to monitoring during dynamic analysis
    for key, list_package_name in tracker_name_package.items():
        for package_name in list_package_name:
            methods = list(analysis.find_methods(package_name))  # find all methods that satisfy regular expression

            if len(methods) > 0:
                trackers_api_to_monitoring[package_name] = []
                list_tracker_inside_app.append(key)

            # add each method to list for monitoring during dynamic analysis
            for method in methods:
                n_method = n_method + 1
                trackers_api_to_monitoring[package_name].append((
                    method.get_method().get_class_name().
                        replace("L", "", 1).replace("/", ".").replace(";", ""),
                    method.get_method().get_name()
                ))

            if len(methods) > 0:
                # remove duplicate
                trackers_api_to_monitoring[package_name] = list(set(trackers_api_to_monitoring[package_name]))

    list_tracker_inside_app = list(set(list_tracker_inside_app))
    list_permissions_app = application.get_permissions()
    end = time.time()
    logger.info("Permission requested by the app {}".format(list_permissions_app))
    logger.info("Tracker inside the app {}".format(list_tracker_inside_app))
    logger.info("Execution time App Analyzer {}".format(end - start))
    # logger.info("API to Monitoring (Trackers) {}".format(n_method))

    dict_analysis_apk["permission_requested"] = list_permissions_app
    dict_analysis_apk["trackers_inside"] = list_tracker_inside_app
    dict_analysis_apk["execution_time_app_analyzer"] = end - start
    # dict_analysis_apk["api_to_monitoring_trackers"] = n_method

    write_result_md5_app(md5_app, list_tracker_inside_app, list_permissions_app, end - start, dict_analysis_apk)
    logger.info("End App Analyzer")

    return list_tracker_inside_app, list_permissions_app, trackers_api_to_monitoring, application, dict_analysis_apk
