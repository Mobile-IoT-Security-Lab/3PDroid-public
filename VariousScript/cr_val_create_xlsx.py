import os
import glob
import json
import xlsxwriter


if __name__ == '__main__':

    list_permission_privacy_relevant = []
    with open(os.path.join(os.getcwd(), "resources", "permissions_privacy_relevant.txt"), "r") as file:
        content = file.readlines()
        list_permission_privacy_relevant = [x.strip() for x in content]

    workbook = xlsxwriter.Workbook(os.path.join(os.getcwd(), "manual_validation", 'CR_Evaluato_Manual_Validation.xlsx'))
    worksheet = workbook.add_worksheet("CREvaluator")
    row = 0
    md5_col = 0
    permissions_col = md5_col + 1
    trackers_col = permissions_col + 1
    sentences_col = trackers_col + 1
    practices_col = sentences_col + 1
    performed_col = practices_col + 1
    third_party_col = performed_col + 1
    app_compliant_CR_1_col = third_party_col + 1
    app_compliant_CR_2_col = app_compliant_CR_1_col + 1
    manual_evaluation_sentences = app_compliant_CR_2_col + 1
    manual_evaluation_app = manual_evaluation_sentences + 1

    ## HEADER ##
    worksheet.write(row, md5_col, "MD5")
    worksheet.write(row, permissions_col, "Permissions")
    worksheet.write(row, trackers_col, "Trackers")
    worksheet.write(row, sentences_col, "Sentence")
    worksheet.write(row, practices_col, "PSI")
    worksheet.write(row, performed_col, "Performed")
    worksheet.write(row, third_party_col, "Third_party")
    worksheet.write(row, app_compliant_CR_1_col, "CR1_Compliant")
    worksheet.write(row, app_compliant_CR_2_col, "CR2_Compliant")
    worksheet.write(row, manual_evaluation_sentences, "Manual Evaluation Sentences")
    worksheet.write(row, manual_evaluation_app, "Manual Evaluation App")

    # worksheet.write()

    path_cr_to_evaluate = os.path.join(os.getcwd(), "manual_validation", "cr_to_manual_analyze")
    list_all_json_results = glob.glob(os.path.join(path_cr_to_evaluate, "*.json"))
    list_all_json_results.remove(os.path.join(path_cr_to_evaluate, "results.json"))
    try:
        row = 1
        for json_result_file in list_all_json_results:
            json_result = json.load(open(json_result_file,"r"))
            md5_app = json_result["md5_app"]
            permissions = json_result["permission_requested"]
            permission_filtered = list(filter(lambda x: x in list_permission_privacy_relevant, permissions))
            # for p in permissions
            permission = ", ".join(permission_filtered)

            trackers = ", ".join(json_result["trackers_inside"])
            print(md5_app)
            cr1_compliant = json_result["policy_page_compliant"] if "policy_page_compliant" in json_result else False
            cr2_compliant = json_result["policy_page_compliant_third_party"] if "policy_page_compliant_third_party" in json_result else False
            analysis_sentences_list = json_result["analysis_sentence"]
            worksheet.write(row, md5_col, md5_app)
            worksheet.write(row, permissions_col, permission)
            worksheet.write(row, trackers_col, trackers)
            worksheet.write(row, app_compliant_CR_1_col, cr1_compliant)
            worksheet.write(row, app_compliant_CR_2_col, cr2_compliant)

            for sentence_dict in analysis_sentences_list:
                sentence = sentence_dict["sentence"]
                privacy_information = ", ".join(sentence_dict["privacy_information"][0])
                performed = sentence_dict["privacy_information_performed_or_not"]
                third_party = sentence_dict["privacy_information_first_party_third_party"]
                worksheet.write(row, sentences_col, sentence)
                worksheet.write(row, practices_col, privacy_information)
                worksheet.write(row, performed_col, performed)
                worksheet.write(row, third_party_col, third_party)
                row = row + 1

    except Exception as e:
        workbook.close()

    workbook.close()
