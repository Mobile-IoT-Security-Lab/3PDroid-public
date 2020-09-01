import dynamic_testing_environment
import app_analyzer
import argparse
import glob
import os
import logging
import requests
from stats import Statistic
import time
import shutil
import subprocess
from adb import ADB
import frida_monitoring
from p3detector.prediction_model import PredictionModel
from androguard.core.bytecodes.apk import APK
import json
import hashlib
import signal
import sys


LOCAL_URL_EMULATOR = "http://127.0.0.1:21212"
MAX_TENTATIVE = 2
MAX_TIME_ANALYSIS = 600

if 'LOG_LEVEL' in os.environ:
    log_level = os.environ['LOG_LEVEL']
else:
    log_level = logging.INFO

# Logging configuration.
logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s> [%(levelname)s][%(name)s][%(funcName)s()] %(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S', level=log_level, stream=sys.stdout)


class MyTimeoutExcpetion(Exception):
    pass


def handler_timeout(signum, frame):
    logger.info(
        "Timeout analysis is reached {sig}, on line {line}, in {file_name}".format(sig=signum, line=str(frame.f_lineno),
                                                                                   file_name=str(
                                                                                       frame.f_code.co_filename)))
    raise MyTimeoutExcpetion("Timeout reached")


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def write_json_file_log(md5_app: str, dict_analysis_app: dict):
    dir_result = os.path.join(os.getcwd(), "logs", md5_app)
    if not os.path.exists(dir_result):
        os.makedirs(dir_result)
    with open(os.path.join(dir_result, "{}.json".format(md5_app)), "w") as json_file:
        json.dump(dict_analysis_app, json_file, indent=4)


def push_api_monitor_xposed(adb: ADB, package_name: str, dir_hook_file: str):
    """
    push file on emulator needed to api monitor

    Parameters
    ----------
    adb
    package_name
    dir_hook_file

    Returns
    -------

    """
    logger.info("Push files needed to API Monitor")
    adb.push_file(os.path.join(dir_hook_file, "hooks.json"), "/data/local/tmp")
    adb.shell(['echo', '"{0}"'.format(package_name), '>', '/data/local/tmp/package.name'])


def write_package_name_and_md5(package_name: str, md5: str, path_file_log: str):
    with open(path_file_log, "a") as file_log:
        file_log.write("{},{}\n".format(package_name, md5))


def pull_api_monitor_xposed(adb: ADB, package_name: str, result_directory: str, md5_app: str = None):
    """

    Parameters
    ----------
    adb
    package_name
    result_directory
    md5_app

    Returns
    -------

    """
    extracted_log_path = os.path.join(result_directory, 'monitoring_api_{}.log'.format(md5_app))

    try:
        adb.execute(['root'])
    except Exception:
        adb.kill_server()

    adb.pull_file('/data/data/{0}/TalosApiMonitor/apimonitor.log'.format(package_name),
                  extracted_log_path)


def check_app_already_analyzed_md5(md5_app: str):
    file_log = os.path.join(os.getcwd(), "logs",
                            md5_app,
                            "{}.json".format(md5_app))
    return os.path.exists(file_log)


def check_app_already_analyzed(package_name: str):
    file_log = os.path.join(os.getcwd(), "logs",
                            package_name.replace(".", "_"),
                            "{}.json".format(package_name.replace(".", "_")))
    return os.path.exists(file_log)


def check_api_invoked_during_dynamic_analysis(md5_app: str):
    file_api = os.path.join(os.getcwd(), "logs",
                            md5_app,
                            "monitoring_api_{}.json".format(md5_app))
    list_api_invoked = []
    if os.path.exists(file_api):
        with open(file_api) as json_file:
            list_api_invoked = json.load(json_file)

    return list_api_invoked


def start_appium_node(type):
    try:
        # check if appium is installed and start it
        if type == "random" and shutil.which("appium") is None:
            type = "Droidbot"
            logger.info("Appium not found, start dynamic analysis with type==Droidbot")
        elif type == "random":
            # start appium process
            logger.info("Start appium process")
            command_appium = ["appium", "--log-level", "warn:error"]
            subprocess.Popen(command_appium, shell=True)
    except Exception as e:
        logger.error("Error on {}".format(e))
        logger.info("Kill and re-launch appium process")
        name_os = os.name
        if name_os == "nt":
            command_kill_appium = ["TASKKILL /F /M node.exe"]
            subprocess.Popen(command_kill_appium)
            time.sleep(1)
            command_appium = ["appium", "--log-level", "warn:error"]
            subprocess.Popen(command_appium, shell=True)
        else:
            command_kill_appium = ["killall node"]
            subprocess.Popen(command_kill_appium)
            time.sleep(1)
            command_appium = ["appium", "--log-level", "warn:error"]
            subprocess.Popen(command_appium, shell=True)
    return type


def start_analysis(list_apps: list, timeout_privacy: int, max_actions: int, type: str, emulator_name: str):
    logger.info("Start Analysis of {} apps".format(len(list_apps)))
    start = time.time()
    stats = Statistic(type)

    if type == "random":
        type = start_appium_node(type)

    logger.info("Upload model p3 detector")
    # upload model
    pdetector = PredictionModel()
    logger.info("P3detector model uploaded")

    # start analysis
    count = 0
    tentative = 0
    num_log = len(glob.glob(os.path.join(os.getcwd(), "logs", "log_analysis_*")))

    log_analysis_file = os.path.join(os.getcwd(), "logs", "log_analysis_{}.json".format(num_log + 1))
    log_permission_file = os.path.join(os.getcwd(), "logs", "permissions_stats_{}.json".format(num_log + 1))
    log_trackers_file = os.path.join(os.getcwd(), "logs", "tracker_stats_{}.json".format(num_log + 1))

    while count < len(list_apps):

        app = list_apps[count]
        dict_analysis_app = {}
        md5_app = md5(app)

        dir_result = os.path.join(os.getcwd(), "logs", md5_app)
        if not os.path.exists(dir_result):
            os.makedirs(dir_result)

        try:

            dict_analysis_app["md5"] = md5_app
            apk_object = APK(app)
            dict_analysis_app["package_name"] = apk_object.get_package()

            if not check_app_already_analyzed_md5(md5_app) or tentative > 0:

                logger.info("3PDroid start Analysis {}".format(app))
                write_package_name_and_md5(apk_object.get_package(), md5_app,
                                           os.path.join(os.getcwd(), "logs", "package_md5.txt"))
                # start emulator
                r_start_emulator = requests.get("{}/start/{}".format(LOCAL_URL_EMULATOR, emulator_name))
                # if the emulator star ok
                if r_start_emulator.status_code == 200:
                    # get trackers libraries and list permissions
                    logger.info("Start emulator ok")
                    logger.info("Get application information")
                    app_trackers, app_permissions_list, api_to_monitoring_trackers, application, dict_analysis_app = app_analyzer. \
                        analyze_apk_androguard(app, md5_app, dict_analysis_app)
                    # get permissions privacy relevant
                    logger.info("Package name {}".format(application.get_package()))
                    dict_analysis_app["package_name"] = application.get_package()
                    logger.info("MD5 {}".format(md5_app))

                    logger.info("Get permission-api mapping")
                    permissions_api_mapping = app_analyzer.get_api_related_to_permission_privacy_relevant()
                    logger.info("Creation list api to be monitored during dynamic analysis")
                    list_api_to_monitoring = app_analyzer.create_list_api_to_monitoring_from_file(
                        permissions_api_mapping,
                        app_permissions_list,
                        app_trackers)

                    # if API == 0 --> app is cleaned
                    if len(list_api_to_monitoring) == 0:
                        logger.info("Application does not need privacy policy page, "
                                    "close the emulator and "
                                    "pass to the next application")
                        # write on file
                        file_name = md5_app
                        dir_result = os.path.join(os.getcwd(), "logs", file_name)
                        dict_analysis_app["dynamic_analysis_needed"] = False
                        with open(os.path.join(dir_result, "{}.json".format(file_name)), "w") as json_file:
                            json.dump(dict_analysis_app, json_file, indent=4)

                        count += 1
                        r_stop_emulator = requests.get("{}/stop/{}".format(LOCAL_URL_EMULATOR, emulator_name))
                        # UPDATE STATS
                        logger.info("Update stats")
                        stats.update_stats_permission(app_permissions_list)
                        stats.update_stats_trackers(app_trackers)
                        stats.add_app_cleaned()
                        # STORE INFORMATION
                        logger.info(stats.stats_trackers)
                        logger.info(stats.stats_permission)
                        # write on file
                        stats.write_on_file(log_analysis_file, count)
                        stats.write_stats_permissions(log_permission_file)
                        stats.write_stats_trackers(log_trackers_file)
                        shutil.move(app, os.path.join(os.getcwd(), "apps_analyzed"))
                        continue

                    # APP should be analyzed in a dynamic way
                    logger.info("Number of APIs to monitoring: {}".format(len(list_api_to_monitoring)))
                    file_name = md5_app
                    dir_result = os.path.join(os.getcwd(), "logs", file_name)
                    dict_analysis_app["api_to_monitoring_all"] = len(list_api_to_monitoring)
                    with open(os.path.join(dir_result, "{}.json".format(file_name)), "w") as json_file:
                        json.dump(dict_analysis_app, json_file, indent=4)
                    # disable verify installer and set correct time
                    time.sleep(5)
                    logger.info("Set correct time on emulator")
                    adb = ADB()
                    adb.kill_server()
                    adb.connect()
                    time.sleep(2)
                    try:
                        command_settings_verify = ["settings put global verifier_verify_adb_installs 0"]
                        adb.shell(command_settings_verify)
                        date_command = ['su 0 date {0}; am broadcast -a android.intent.action.TIME_SET'.
                                            format(time.strftime('%m%d%H%M%Y.%S'))]
                        adb.shell(date_command)
                    except Exception as e:
                        logger.error("Exception as e {}, restart and re-connect to emulator".format(e))
                        adb.kill_server()
                        adb.connect()
                        command_settings_verify = ["settings put global verifier_verify_adb_installs 0"]
                        adb.shell(command_settings_verify)
                        date_command = ['su 0 date {0}; am broadcast -a android.intent.action.TIME_SET'.
                                            format(time.strftime('%m%d%H%M%Y.%S'))]
                        adb.shell(date_command)

                    dir_hook_file = os.path.join(os.getcwd(), "hook", md5_app)
                    logger.info("Creation hook dir frida")

                    if not os.path.exists(dir_hook_file):
                        os.makedirs(dir_hook_file)
                    hook_is_created = app_analyzer.create_api_list_frida(list_api_to_monitoring,
                                                                         os.path.join(dir_hook_file, "frida_api.txt"))
                    frida_monitoring.push_and_start_frida_server(adb)
                    frida_monitoring.set_file_log_frida(os.path.join(os.getcwd(), "logs",
                                                                     md5_app, "monitoring_api_{}.json".format(md5_app)))

                    frida_monitoring.clean_list_json_api_invoked()
                    signal.signal(signal.SIGALRM, handler_timeout)
                    signal.alarm(MAX_TIME_ANALYSIS)
                    result_app, dict_analysis_app = dynamic_testing_environment.start_analysis(type_analysis=type,
                                                                                               app=app,
                                                                                               max_actions=max_actions,
                                                                                               timeout_privacy=timeout_privacy,
                                                                                               pdetector=pdetector,
                                                                                               md5_app=md5_app,
                                                                                               frida_monitoring=frida_monitoring,
                                                                                               dict_analysis_app=dict_analysis_app)

                    # END DYNAMIC ANALYSIS NOW STORE DATA
                    result_directory = os.path.join(os.getcwd(), "logs", md5_app)
                    if not os.path.exists(result_directory):
                        os.makedirs(result_directory)

                    logger.info("Analysis api invoked during dynamic analysis")
                    # Get API Invoked
                    list_json_api_invoked = frida_monitoring.get_list_api_invoked()
                    # set_list_json_api_invoked = list(set(list_json_api_invoked))
                    logger.info("Api invoked during dynamic analysis {}".format(len(list_json_api_invoked)))

                    # store on json file the api invoked
                    if len(list_json_api_invoked) > 0:
                        file_log_frida = frida_monitoring.get_file_log_frida()
                        with open(file_log_frida, "w") as outfile_api:
                            json.dump(list_json_api_invoked, outfile_api, indent=4)

                    # Action not needed
                    # DETECT IF THE APP IS COMPLIANT OR NOT WITH GOOGLE PLAY STORE
                    app_is_compliant = result_app.detected and not (result_app.back_button_change_page or
                                                                    result_app.home_button_change_page or
                                                                    len(list_json_api_invoked) > 0
                                                                    )

                    dict_analysis_app["api_invoked_during_dynamic_analysis"] = len(list_json_api_invoked)
                    if app_is_compliant:
                        stats.add_app_compliant()
                    else:
                        stats.add_app_not_compliant()
                    dict_analysis_app["app_is_compliant_with_google_play_store"] = app_is_compliant
                    dict_analysis_app["app_analyzed"] = True
                    dict_analysis_app["num_tentative"] = tentative + 1

                    write_json_file_log(md5_app, dict_analysis_app)

                    stats.add_api_privacy_relevant_invoked(len(list_json_api_invoked))

                    # r_reset_emulator = requests.get("{}/reset/{}".format(LOCAL_URL_EMULATOR, emulator_name))
                    r_stop_emulator = requests.get("{}/stop/{}".format(LOCAL_URL_EMULATOR, emulator_name))

                    # UPDATE stats analysis
                    logger.info("Update stats")
                    stats.list_max_actions.append(result_app.max_actions)
                    stats.update_value_dynamic_analysis(result_app)
                    stats.update_stats_permission(app_permissions_list)
                    stats.update_stats_trackers(app_trackers)

                    # debug
                    logger.info(stats.stats_trackers)
                    logger.info(stats.stats_permission)

                    # write on file
                    count += 1
                    tentative = 0

                    stats.write_on_file(log_analysis_file, count)
                    stats.write_stats_permissions(log_permission_file)
                    stats.write_stats_trackers(log_trackers_file)
                    logger.info("End update stats")
                    logger.info("3PDroid end analysis")
                    str_end_file = "*" * 20
                    logger.info("{}\n\n".format(str_end_file))
                    shutil.move(app, os.path.join(os.getcwd(), "apps_analyzed"))
                    
                else:

                    tentative += 1
                    if tentative < MAX_TENTATIVE:
                        logger.error("Unable to start emulator, try again this app")
                        str_end_file = "*" * 20
                        logger.info("{}\n\n".format(str_end_file))
                        r_stop_emulator = requests.get("{}/stop/{}".format(LOCAL_URL_EMULATOR, emulator_name))
                    else:
                        tentative = 0
                        count += 1
                        r_stop_emulator = requests.get("{}/stop/{}".format(LOCAL_URL_EMULATOR, emulator_name))
                        stats.add_app_not_analyzed()
                        dict_analysis_app["app_analyzed"] = False
                        write_json_file_log(md5_app, dict_analysis_app)
                        logger.error("Unable to start emulator, pass to next app")
                        str_end_file = "*" * 20
                        logger.info("{}\n\n".format(str_end_file))
                        shutil.move(app, os.path.join(os.getcwd(), "apps_analyzed"))
                        

            else:
                logger.info("App already analyzed, pass to next app")
                shutil.move(app, os.path.join(os.getcwd(), "apps_analyzed"))
                count += 1

        except MyTimeoutExcpetion as e:
            tentative += 1
            if tentative < MAX_TENTATIVE:
                logger.error("Exception stop emulator, Exception: {}".format(e))
                str_end_file = "*" * 20
                logger.info("{}\n\n".format(str_end_file))
                r_stop_emulator = requests.get("{}/stop/{}".format(LOCAL_URL_EMULATOR, emulator_name))
            else:
                tentative = 0
                count += 1
                r_stop_emulator = requests.get("{}/stop/{}".format(LOCAL_URL_EMULATOR, emulator_name))
                stats.add_app_not_analyzed()
                logger.error("Exception stop emulator pass to next apps, Exception: {}".format(e))
                dict_analysis_app["app_analyzed"] = False
                write_json_file_log(md5_app, dict_analysis_app)
                str_end_file = "*" * 20
                logger.info("{}\n\n".format(str_end_file))
                shutil.move(app, os.path.join(os.getcwd(), "apps_analyzed"))
                

        except Exception as e:
            tentative += 1
            if tentative < MAX_TENTATIVE:
                logger.error("Exception stop emulator, Exception: {}".format(e))
                str_end_file = "*" * 20
                logger.info("{}\n\n".format(str_end_file))
                r_stop_emulator = requests.get("{}/stop/{}".format(LOCAL_URL_EMULATOR, emulator_name))
            else:
                tentative = 0
                count += 1
                r_stop_emulator = requests.get("{}/stop/{}".format(LOCAL_URL_EMULATOR, emulator_name))
                stats.add_app_not_analyzed()
                logger.error("Exception stop emulator pass to next apps, Exception: {}".format(e))
                dict_analysis_app["app_analyzed"] = False
                write_json_file_log(md5_app, dict_analysis_app)
                str_end_file = "*" * 20
                logger.info("{}\n\n".format(str_end_file))
                shutil.move(app, os.path.join(os.getcwd(), "apps_analyzed"))
             
    end = time.time()
    logger.info("\n\n")
    logger.info("Execution time: {}, mean: {}".format(end - start, (end - start) / count))
   


def get_cmd_args(args: list = None):
    """
    Parse and return the command line parameters needed for the script execution.
    :param args: List of arguments to be parsed (by default sys.argv is used).
    :return: The command line needed parameters.
    """

    parser = argparse.ArgumentParser(
        prog='python dynamic_testing_environment.py',
        description='Start dynamic testing environment to analyze the app'
    )

    parser.add_argument('-t', '--timeout-privacy', type=int, metavar='TIMEOUT', default=60,
                        help='Timeout to waiting (in seconds) to discover if the privacy page has an expiration')
    parser.add_argument('-m', '--max-actions', type=int, metavar='MAXACTIONS', default=30,
                        help='Maximum actions (in number of events) for the app stimulation')
    parser.add_argument('-d', '--dir-app', type=str, metavar='DIR', default=os.path.join(os.getcwd(), 'apps'),
                        help='The directory where is the apps')
    parser.add_argument('--type', type=str, metavar='TYPE', default='Droidbot', choices=["random", "Droidbot"],
                        help="The type of app stimulation ")
    parser.add_argument("--emulator-name", type=str, default="AndroidEmulator",
                        help="Name of Android Emulator within Virtual Box")

    return parser.parse_args(args)


if __name__ == "__main__":
    arguments = get_cmd_args()
    list_apps = glob.glob(os.path.join(arguments.dir_app, "*.apk"))
    start_analysis(list_apps, arguments.timeout_privacy, arguments.max_actions,
                   arguments.type, arguments.emulator_name)
