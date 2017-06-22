# EMIS Template Code Search

EMIS templates use SNOMED / Read codes saved inside. This program will traverse a folder and it's subfolders, looking for extracted EMIS templates in .xml file format.
It will miss out folders named "Archive". It will output results to a csv file saved to the temp folder in the operating system which will open automatically after processing.

As extracted EMIS template xml files only contain in internal EMIS ID code representing the SNOMED code, this program also contacts an EMIS extract database to resolve the internal ID, translating it to the actual SNOMED code.

## Run
To run the tool in windows command line:
```bash
traverse FOLDER [-d (DATABASE_SERVER) -u (DATABASE_USERNAME)]

Options:
    -d              change database connection server
    -u              change database username (you will be prompted for password)

Arguments:
    FOLDER              path to EMIS Template xml files
    DATABASE_SERVER     name of the database server e.g. sqlanalytics.emis.thirdparty.nhs.uk,1601
    DATABASE_USERNAME   database username (default is "SimonCrouch")
```

### Versions
* v2.0 - Introduced docopt-style input of user options and allowed database, username and password input, and froze into exe
* v2.1.1 - Remove the Version number and .xml extension in results for easier vlookup use in excel later