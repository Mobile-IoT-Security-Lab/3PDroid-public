import pandas as pd
import os
import glob
import xlsxwriter


if __name__== "__main__":
    path_file = os.path.join(os.getcwd(), "manual_validation","App_With_Privacy_Policy.xlsx")
    dfs = pd.read_excel(path_file, sheet_name="App With Privacy Policy")
    md5_app_already_checked = list(dfs["MD5_APP"].dropna().values)

    path_app_with_privacy_policy = glob.glob(os.path.join(os.getcwd(), "privacypoliciesxml", "*.xml"))

    tuple_list_app_pp = set(
        map(lambda x: (x.rsplit(os.sep, 1)[-1].split("_")[0], x.rsplit(os.sep, 1)[-1].split("_")[1].split(".xml")[0]),
            path_app_with_privacy_policy))

    workbook = xlsxwriter.Workbook(os.path.join(os.getcwd(), "manual_validation", 'App_With_Privacy_Policy_not_analyzed.xlsx'))
    worksheet = workbook.add_worksheet("App With Privacy Policy")
    row = 0
    col = 0

    worksheet.write(row, col, "MD5_APP")
    worksheet.write(row, col + 1, "MD5_PP")

    row = 1
    for md5_app, md5_pp in tuple_list_app_pp:
        if md5_app not in md5_app_already_checked:
            worksheet.write(row, col, md5_app)
            worksheet.write(row, col + 1, md5_pp)
            row = row + 1

    workbook.close()
    #
    # with pd.ExcelWriter('output.xlsx') as writer:
    #     df1.to_excel(writer, sheet_name='Sheet_name_1')
    #     df2.to_excel(writer, sheet_name='Sheet_name_2')