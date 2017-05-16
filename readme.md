# EMIS Template Code Search

EMIS templates use SNOMED / Read codes saved inside. This program will traverse a folder and it's subfolders, looking for extracted EMIS templates in .xml file format.
It will miss out folders named "Archive". It will output results in Excel, with a file saved to the temp folder in the operating system.


As extracted EMIS template xml files only contain in internal EMIS ID code representing the SNOMED code, this program also contacts an EMIS extract database to resolve the internal ID, translating it to the actual SNOMED code.

Run with:
```bash
"c:\python.exe" "traverse.py" "Path\to\xml\files"
```