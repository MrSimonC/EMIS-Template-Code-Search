"""Traverse EMIS xml

Usage: traverse FOLDER [-d (DATABASE_SERVER) -u (DATABASE_USERNAME)]

Options:
    -d              change database connection server
    -u              change database username (you will be prompted for password)

Arguments:
    FOLDER              path to EMIS Template xml files
    DATABASE_SERVER     name of the database server e.g. sqlanalytics.emis.thirdparty.nhs.uk,1601
    DATABASE_USERNAME   database username (default is "SimonCrouch")
"""
from docopt import docopt
import csv
import datetime
import getpass
import mssql
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as Et
__version__ = '2.1.4'


def find_all_codes(path):
    """
    Return certain xml fields from an EMIS template xml file
    :param path: file path to emis template xml file
    :return: list(Dict[xml fields]) e.g. [{'displayName': 'Goal achieved'}, {'mandatory': 'false', 'codeSystem': '2...
    """
    with open(path, encoding='utf8') as f:
        xml = f.read()
    tree = Et.fromstring(re.sub(r"(<\?xml[^>]+\?>)", r"\1<root>", xml) + "</root>")  # fix bad xml by containing all file within a "<root>" node

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
                                        filename = os.path.split(path)[1]
                                        re_remove_version = r'\s*(\.xml+|[vV]+[0-9]+\.*[0-9]*\.xml+)$'
                                        # remove version and extension
                                        result['template name'] = filename.replace(
                                            re.search(re_remove_version, filename).group(), '') \
                                            if re.search(re_remove_version, filename) \
                                            else filename.replace('.xml', '')
                                        result['library'] = library
                                        result['page'] = page
                                        result['location'] = location
                                        result['prompt'] = label
                                        result['mandatory'] = mandatory
                                        result['prompt for date'] = prompt_for_date
                                        result['diary'] = diary
                                        results.append(result)

    return results


def file_ext(path):
    _, extension = os.path.splitext(path)
    return extension


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


def main(folder, db_server, db_user, db_pass):
    print('Traversing the xml folder now')
    all_files = [os.path.join(path, file) for path, _, files in os.walk(folder) for file in files
                 if os.path.basename(path) != 'Archive' and file_ext(file) == '.xml']
    codes = [x for file in all_files for x in find_all_codes(file)]
    print('XML files successfully traversed')

    print('Get EMIS IDs vs SNOMED codes from database')
    db = mssql.QueryDB(db_server, 'BCH_Community', db_user, db_pass)
    emis_codes = db.exec_sql('select * from dbo.CodeLookup')
    print('SNOMED codes successfully obtained')

    print('Translating EMIS IDs to SNOMED read codes')
    for code in codes:
        snomed = emis_to_snomed(emis_codes, code['code'])
        code['code'] = snomed['ReadCV2'] if snomed else 'zzzCan\'t resolve code'

    print('Ouputting CSV')
    headers = ['path', 'template name', 'library', 'page', 'location', 'prompt', 'displayName', 'code', 'codeSystem',
               'mandatory', 'prompt for date', 'diary']
    timestamp = datetime.datetime.now().strftime('%d%b%y_%H%M')
    temp_results_file = os.path.join(tempfile.gettempdir(), 'emis_template_analysis_{0}.csv'.format(timestamp))
    with open(temp_results_file, 'w', newline='') as file_out:
        csv_obj = csv.DictWriter(file_out, headers)
        csv_obj.writeheader()
        for c in codes:
            csv_obj.writerow(c)
    print('Outputting to: {0}'.format(temp_results_file))
    subprocess.Popen(temp_results_file, shell=True)

if __name__ == '__main__':
    print('Traverse EMIS xml v{0}'.format(__version__))
    database_server = 'sqlanalytics.emis.thirdparty.nhs.uk,1601'
    database_user = 'Paul.Stinson'
    try:
        database_password = os.environ['EMIS_SQL']
    except KeyError:
        database_password = ''
        pass
    args = docopt(__doc__)
    if not (os.path.isdir(args['FOLDER'])):
        print('Path "{path}" not valid. Please check the folder exists for your FOLDER input'.format(path=sys.argv[1]))
        sys.exit(1)
    if args['-d'] and args['-u']:
        database_server = args['DATABASE_SERVER']
        database_user = args['DATABASE_USERNAME']
        try:
            database_password = os.environ['EMIS_SQL']
            print('Found a password in EMIS_SQL environment variable. Using that.')
        except KeyError:
            print('No password found in EMIS_SQL environment variable - please enter one.')
            database_password = getpass.getpass('Password: ')
            pass
    main(args['FOLDER'], database_server, database_user, database_password)
