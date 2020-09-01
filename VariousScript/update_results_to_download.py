import os
import glob
import json


if __name__ == '__main__':
    all_dir = glob.glob(os.path.join(os.getcwd(), "logs", "*"))
    all_dir_logs = list(filter(lambda x: os.path.isdir(x), all_dir))
    dir_data_final = os.path.join(os.getcwd(), "logs_to_upload")
    for dir in all_dir_logs:
        md5_app = dir.rsplit(os.sep, 1)[-1]
        json_file = os.path.join(dir, f"{md5_app}.json")
        if os.path.exists(json_file):
            dict_file = json.load(open(json_file, "r"))
            del dict_file["package_name"]
            json.dump(dict_file, open(os.path.join(os.getcwd(),"logs_to_upload",f"{md5_app}.json"), "w"))

