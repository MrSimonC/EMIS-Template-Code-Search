import csv
import datetime
import mssql
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as Et
__version__ = '1.1'

def find_all_codes(path):
    """
    Return certain xml fields from an EMIS template xml file
    :param path: file path to emis template xml file
    :return: list(Dict[xml fields]) e.g. [{'displayName': 'Goal achieved'}, {'mandatory': 'false', 'codeSystem': '2...
    """
    tree = Et.parse(path)

    # remove namespace
    for el in tree.iter():
        if '}' in el.tag:
            el.tag = el.tag.split('}', 1)[1]

    # traverse entries (noting parent entry to find code's location)
    results = []
    for great_grandparent_three in tree.iter():  # needed for library item
        for great_grandparent_two in great_grandparent_three:
            for great_grandparent in great_grandparent_two:  # level needed for page name
                for grandparent in great_grandparent:
                    for parent in grandparent:
                        for child in parent:
                            if child.tag == 'component':
                                label = child.find('label').text
                                prompt_for_date = child.find('promptForDate').text  # true for both 'diary'&'prompt for a date'
                                mandatory = child.find('mandatory').text
                                diary = 'diary' if child.find('diary') else ''  # diary field allows future dates
                                location = parent.find('title').text
                                try:
                                    library = great_grandparent_three.find('libraryItemDefintionName').text
                                except (AttributeError, TypeError):
                                    library = ''
                                try:
                                    page = great_grandparent.find('title').text
                                except AttributeError:
                                    page = ''
                                for code in child.iter('code'):
                                    if code.attrib:
                                        result = code.attrib
                                        result['path'] = path
                                        result['file'] = os.path.split(path)[1]
                                        result['library'] = library
                                        result['page'] = page
                                        result['location'] = location
                                        result['prompt'] = label
                                        result['mandatory'] = mandatory
                                        result['prompt for date'] = prompt_for_date
                                        result['diary'] = diary
                                        results.append(result)

    return results


def emis_to_snomed(emis_codes, emis_id):
    """
    Translates EMIS ID codes into SNOMED codes
    :param emis_codes: list of ordered dicts from EMIS sql (select top 1 * from dbo.CodeLookup')
    :param emis_id: id to look up
    :return: row from sql e.g. OrderedDict([('EmisCodeId', 237011), ('SnomedConceptId', 126949007), ('SnomedDescription
    """
    for code in emis_codes:
        if code['EmisCodeId'] == int(emis_id):
            return code


def main(folder):
    # Env vars check
    try:
        if not os.environ['EMIS_SQL']:
            print('Needed environment variables not found')
            sys.exit(1)  # exit as error
    except KeyError:
        print('Needed environment variables not found')
        sys.exit(1)  # exit as error

    # Excel path check
    excel_path = r'C:\Program Files (x86)\Microsoft Office\Office14\EXCEL.EXE'
    if not os.path.exists(excel_path):
        print('I can\'t find "{path}" - can you correct the code?'.format(path=excel_path))
        sys.exit(1)

    # Main code
    all_files = [os.path.join(path, file) for path, _, files in os.walk(folder) for file in files
                 if os.path.basename(path) != 'Archive']
    codes = [x for file in all_files for x in find_all_codes(file)]

    print('Get EMIS IDs vs SNOMED codes from database')
    db = mssql.QueryDB('sqlanalytics.emis.thirdparty.nhs.uk,1601', 'BCH_Community', 'SimonCrouch', os.environ['EMIS_SQL'])
    emis_codes = db.exec_sql('select * from dbo.CodeLookup')

    print('Translate EMIS id to SNOMED read code')
    for code in codes:
        snomed = emis_to_snomed(emis_codes, code['code'])
        code['code'] = snomed['ReadCV2'] if snomed else 'zzzCan\'t resolve code'

    print('CSV output')
    headers = ['path', 'file', 'library', 'page', 'location', 'prompt', 'displayName', 'code', 'codeSystem',
               'mandatory', 'prompt for date', 'diary']
    timestamp = datetime.datetime.now().strftime('%d%b%y_%H%M')
    temp_results_file = os.path.join(tempfile.gettempdir(), 'emis_template_analysis_{0}.csv'.format(timestamp))
    with open(temp_results_file, 'w', newline='') as file_out:
        csv_obj = csv.DictWriter(file_out, headers)
        csv_obj.writeheader()
        for c in codes:
            csv_obj.writerow(c)
    print('Outputting to: {0]'.format(temp_results_file))
    subprocess.Popen([excel_path, temp_results_file])

if __name__ == '__main__':
    print('version: {0}'.format(__version__))
    if len(sys.argv) != 2:
        print('Usage: traverse "<FOLDER_PATH>"')
        sys.exit(1)
    elif not(os.path.isdir(sys.argv[1])):
        print('Path "{path}" not valid'.format(path=sys.argv[1]))
        sys.exit(1)
    else:
        folder = sys.argv[1]
        main(sys.argv[1])
