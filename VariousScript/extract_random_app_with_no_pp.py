import os
import glob
import json
import random
import shutil
from tqdm import tqdm
import xlsxwriter

if __name__ == "__main__":

    path_log = os.path.join(os.getcwd(), "logs", "*")
    path_xml_dump_app = os.path.join(os.getcwd(), "xml_dump", "*")
    md5_in_xml_dump = list(map(lambda x: x.rsplit(os.sep, 1)[-1], glob.glob(path_xml_dump_app)))
    all_md5_app_analyzed = list(map(lambda x: x.rsplit(os.sep, 1)[-1], glob.glob(path_log)))
    list_app_without_pp = list()
    list_app_with_pp = list()

    for md5 in tqdm(all_md5_app_analyzed, desc="Finding App Without Privacy Policy"):
        json_file_app = os.path.join(os.getcwd(), "logs", md5, f"{md5}.json")
        if os.path.exists(json_file_app):
            dict_analysis = json.load(open(json_file_app,"r"))
            detected = dict_analysis["privacy_policy_page_detected"] if "privacy_policy_page_detected" in dict_analysis else False
            analyzed = dict_analysis["app_analyzed"] if "app_analyzed" in dict_analysis else False
            xml_is_present = md5 in md5_in_xml_dump
            if not detected and analyzed and xml_is_present:
                list_app_without_pp.append(md5)
            elif detected:
                list_app_with_pp.append(md5)

    number_random = len(list_app_with_pp)
    app_without_pp_to_manual_analysis = random.sample(list_app_without_pp, number_random)

    workbook = xlsxwriter.Workbook(
        os.path.join(os.getcwd(), "manual_validation", 'App_Without_Privacy_Policy.xlsx'))
    worksheet = workbook.add_worksheet("App Without Privacy Policy")

    row = 0
    col = 0
    # HEADER
    worksheet.write(row, col, "MD5_APP")
    row = 1
    for md5 in tqdm(app_without_pp_to_manual_analysis, desc="Copy dir xml_dump app without privacy policy"):
        shutil.copytree(os.path.join(os.getcwd(),"xml_dump",md5), os.path.join(os.getcwd(), "manual_validation", "xml_dump_no_privacy_policy", md5))
        worksheet.write(row, col, md5)
        row = row + 1
    workbook.close()
