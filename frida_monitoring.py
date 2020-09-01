import frida
import os
import logging
import sys

from adb import ADB

if 'LOG_LEVEL' in os.environ:
    log_level = os.environ['LOG_LEVEL']
else:
    log_level = logging.INFO

LOCAL_URL_EMULATOR = "http://127.0.0.1:21212"
logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s> [%(levelname)s][%(name)s][%(funcName)s()] %(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S', level=log_level, stream=sys.stdout)


file_log_frida = os.path.join(os.getcwd(), "logs")
list_json_api_invoked = []


def get_file_log_frida():
    global file_log_frida
    return file_log_frida


def set_file_log_frida(path_file):
    if os.path.exists(path_file):
        os.remove(path_file)
    global file_log_frida
    file_log_frida = path_file


def clean_list_json_api_invoked():
    global list_json_api_invoked
    list_json_api_invoked = []


def get_list_api_invoked():
    global list_json_api_invoked
    return list_json_api_invoked


def on_message(message, data):
    global list_json_api_invoked
    if message['type'] == 'send':
        if "Error" not in str(message["payload"]):
            list_json_api_invoked.append(message["payload"])


def push_and_start_frida_server(adb: ADB):
    """

    Parameters
    ----------
    adb

    Returns
    -------

    """
    frida_server = os.path.join(os.getcwd(), "resources", "frida-server", "frida-server")
    try:
        adb.execute(['root'])
        adb.connect()
    except Exception as e:
        adb.kill_server()
        logger.error("Error on adb {}".format(e))

    logger.info("Push frida server")
    try:
        adb.push_file(frida_server, "/data/local/tmp")
    except Exception as e:
        logger.error("Push frida error as {}".format(e))
        pass
    logger.info("Add execution permission to frida-server")
    chmod_frida = ["chmod 755 /data/local/tmp/frida-server"]
    adb.shell(chmod_frida)
    logger.info("Start frida server")
    start_frida = ["cd /data/local/tmp/ && ./frida-server &"]
    adb.shell(start_frida, is_async=True)


def read_api_to_monitoring(file_api_to_monitoring):
    if os.path.exists(file_api_to_monitoring):
        list_api_to_monitoring = []
        content = []
        with open(file_api_to_monitoring) as file_api:
            content = file_api.readlines()
        content = [x.strip() for x in content]
        for class_method in content:
            list_api_to_monitoring.append((class_method.split(",")[0], class_method.split(",")[1]))
        return list_api_to_monitoring
    else:
        return None


def create_script_frida(list_api_to_monitoring: list, path_frida_script_template: str):
    with open(path_frida_script_template) as frida_script_file:
        script_frida_template = frida_script_file.read()

    script_frida = ""
    for tuple_class_method in list_api_to_monitoring:
        script_frida += script_frida_template.replace("class_name", "\"" + tuple_class_method[0] + "\""). \
                            replace("method_name", "\"" + tuple_class_method[1] + "\"") + "\n\n"
    return script_frida


def start(package_name, execution_time, file_api_to_monitoring):
    list_api_to_monitoring = read_api_to_monitoring(file_api_to_monitoring)

    pid = None
    device = None
    session = None
    try:
        device = frida.get_usb_device()
        pid = device.spawn([package_name])
        session = device.attach(pid)
    except Exception as e:

        logger.error("Error {}".format(e))

    logger.info("Succesfully attached frida to app")

    script_frida = create_script_frida(list_api_to_monitoring,
                                       os.path.join(os.getcwd(), "frida_scripts", "frida_script_template.js"))

    script = session.create_script(script_frida.strip().replace("\n", ""))
    script.on("message", on_message)
    script.load()

    device.resume(pid)


if __name__ == "__main__":
    if len(sys.argv) == 4:
        package_name = sys.argv[1]
        execution_time = int(sys.argv[2])
        file_api_to_monitoring = sys.argv[3]
        start(package_name, execution_time, file_api_to_monitoring)
    else:
        print("[*] Usage: python frida_monitoring.py com.example.app 5000 api.txt")
