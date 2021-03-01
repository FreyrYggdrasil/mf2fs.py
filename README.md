# mf2fs.py
Script to move files from source into target folder structure using different file properties.

    optional arguments:
    -h, --help            show this help message and exit
    --action, -a          Perform actions, if not used just display results. If used result 
                          csv files are saved.
    --foldercreate, -c    Create target folder (structure) when missing
    --sourcerename, -r    Rename source when target does not exist (only same drive support, no copy)
    --sourcedelete, -d    Delete source when target exists and is the same
    --subfolders          Traverse directory (search sub folders), default is True
    --folderpattern [], -p []
                          Pattern to use when defining the destination folder for verification 
                          of files from source folder (not implemented yet). Implemented is 
                          YEAR\MONTH\DAY into rootfolder (specified with --target). Supports 
                          different file extensions to gather information about (media) file creation.
    --target [], -t []    Destination root folder to use for file verifications (if exist, is different)
    --input [], -i []     Source folder to be used
    --search  [ ...], -s  [ ...]
                          Only evaluate files that conform to the supplied pattern in their filename
                          (not implemented yet)
    --loglevel [], -l []  Loglevel to use
    --modified [], -w []  Accepts a date or keywords 'lastday', 'lastweek', 'lastmonth', 'lastyear'.
                          Limits files to be evaluated to that periode until today (not implemented yet).
    --saveresults         Save results in csv files (tab seperated). No further actions.
    --useresults []       Use results from csv files (tab seperated) and perform actions. Takes file 
                          prefix as a parameter in the form YYYYMMDD_HHMMSS.
    --number [], -n []    Maximum files to evaluate (steps of 50).

Not all arguments are implemented (yet).
