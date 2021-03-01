#  https://docs.python.org/3/library/os.html
import os
import glob
import pytz
import datetime
import time
from win32com.propsys import propsys, pscon
import argparse
import sys
import re
import hashlib 
import exifread
from pathlib import Path
import shutil
#  https://docs.python.org/3/library/csv.html
import csv
from dateutil.parser import parse

# **************************************************
# processing
def update_progress():
	print('.', end = '', flush = True)
    
# **************************************************
# default settings
def get_defaults():
    """
    Helper method for getting the default settings.

    Returns
    -------
    default_settings : dict
        A dictionary of the default settings.
    """

    return {
        "action": False,
        "foldertarget": "",
        "folderinput": "",
        "folderssub": False,
        "folderpattern": "",
        "filesearchpattern": [],
        "filemodifiedwithin": "",
        "loglevel": "info",
        "foldercreate": False,
        "sourcerename": False,
        "sourcedelete":False,
        "resultssave":False,
        "resultsuse":"",
        "number":0,
    }


# **************************************************
# print string to screen for user feedback
def p(plevel:int, text, *args) -> bool:

    global loglevels
    global settings

    level = settings["loglevel"]
    print_line = False
    no_linefeed = False

    try:
        if loglevels.index(settings["loglevel"]) >= plevel: 
            print_line = True
    except Exception as e:
        return False

    if print_line:
        if not text: 
            text = ''
        elif type(text) == type(list()):
            # no lists
            text = ''
        else:
            text = str(text)

        try:
            if args:
                for i in args:
                    if not i == 'end=""':
                        text = text + ' ' + str(i)
                    else:
                        no_linefeed = True
        except Exception as f:
            return False

        if no_linefeed:
            print(text, end="")
        else:
            print(re.sub(' +', ' ', str(text)))

    return True

#  ********
#  main function
def initialize():
 
    # doc: https://docs.python.org/3/library/argparse.html
    parser = argparse.ArgumentParser(
        prog="mp2fmdf.py",
        usage=argparse.SUPPRESS,
        description="Automate checking picture folder "
                    "removing duplicates and moving"
                    "pictures into their Y\M\D folder.",
        prefix_chars="-",
        fromfile_prefix_chars=None,
        add_help=True,
        exit_on_error=True,
        parents=[],
        allow_abbrev=False,
        argument_default=None,
        epilog='',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--action",
        "-a",
        dest="action",
        default=False,
        action="store_true",
        help="Perform actions, if not used just display results.",
    )
    parser.add_argument(
        "--foldercreate",
        "-c",
        default=False,
        dest="foldercreate",
        action="store_true",
        help="Create target folders when missing",
    )
    parser.add_argument(
        "--sourcerename",
        "-r",
        default=False,
        dest="sourcerename",
        action="store_true",
        help="Rename source when target does not exist",
    )
    parser.add_argument(
        "--sourcedelete",
        "-d",
        default=False,
        dest="sourcedelete",
        action="store_true",
        help="Delete source when target exists",
    )
    parser.add_argument(
        "--subfolders",
        default=False,
        dest="folderssub",
        action="store_true",
        help="Traverse directory (search sub folders), default is False",
    )
    parser.add_argument(
        "--folderpattern",
        "-p",
        metavar='',
        dest="folderpattern",
        default="ymd_structure",
        nargs="?",
        help="Pattern to use when defining the destination folder \
            for verification of files from source folder \
            (not implemented yet).",
    )
    parser.add_argument(
        "--target",
        "-t",
        metavar='',
        dest="foldertarget",
        default="",
        nargs="?",
        help="Destination folder to use for file verifications",
    )
    parser.add_argument(
        "--input",
        "-i",
        metavar='',
        dest="folderinput",
        default="./",
        nargs="?",
        help="Source folder to be used",
    )
    parser.add_argument(
        "--search",
        "-s",
        type=str,
        metavar='',
        dest="filesearchpattern",
        default="",
        nargs="+",
        help="Only evaluate files that conform to the supplied \
                pattern in their filename (not implemented yet)",
    )
    parser.add_argument(
        "--loglevel",
        "-l",
        metavar='',
        dest="loglevel",
        default="verbose",
        choices=loglevels,
        nargs="?",
        help="Loglevel to use",
    )
    parser.add_argument(
        "--modified",
        "-w",
        metavar='',
        type=str,
        dest="filemodifiedwithin",
        default="",
        nargs="?",
        help="Accepts a date or keywords 'lastday', \
            'lastweek', 'lastmonth', 'lastyear'. Limits files \
            to be evaluated to that periode until today.",
    )
    parser.add_argument(
        "--saveresults",
        dest="resultssave",
        default=False,
        action="store_true",
        help="Save results in csv files (tab seperated). \
            No further actions.",
    )
    parser.add_argument(
        "--useresults",
        metavar='',
        dest="resultsuse",
        default="",
        nargs="?",
        help="Use results from csv files (tab seperated) and \
            perform actions. Takes file prefix as a parameter in \
            the form YYYYMMDD_HHMMSS.",
    )
    parser.add_argument(
        "--number",
        "-n",
        metavar='',
        dest="number",
        default=0,
        nargs="?",
        help="Maximum files to evaluate (steps of 50).",
    )
    
    global settings
    global silent
    global critical
    global error
    global warning
    global info
    global verbose
    global allmsg

    options = vars(parser.parse_args())
    settings = get_defaults()
    settings.update(options)


#  ********
#  delete file
#  > returns True|False
def deleteFiles(filelist) -> bool:
    
    for files in filelist:
        
        try:
            os.remove(files[0]) 

        except IsADirectoryError as i:
            p(warning, 'Removing a directory', files[0]
                     , 'is not supported, error ', i)

        except Exception as e:
            p(error, 'Deleting file', files[0], 'failed with error', 
                     e, 'Do you have sufficient rights?')

    return True

#  ********
#  rename file
#  > returns True|False
def renameTheFiles(filelist: list) -> bool:
    
    global deleteSourceFile
    
    n=0
    t=1
    for files in filelist:
        if n == 0 or n==50:
            p(warning,'Renaming (or copying) files from  files list'
                , t, 'of', len(filelist))
            n=0
        n+=1
        if files[0][:1] == files[1][:1]: 
            try:
                os.rename(os.path.join(files[0]), os.path.join(files[1])) 
            except WindowsError as w:
                p(error, 'File', files[0], 'gives me a message while \
                            renaming', w)
            except Exception as e:
                p(error, 'Renaming file', os.path.join(files[0])
                         , 'to', os.path.join(files[1])
                         , 'failed with error', e
                         , 'Do you have sufficient rights?')

        else:
            try:
                shutil.copy2(files[0], files[1])
                if os.path.isfile(files[1]):
                    if settings["sourcedelete"]:
                        deleteFile = []
                        deleteFile.append(files)
                        deleteFiles(deleteFile)
                else:
                    p(info, 'No erros but file doesn\'t exist. Bummer.')
            except Exception as c:
                p(error, 'This didn\'t work, sorry: ', c)

        t+=1

    return True


#  ********
#  write results to files
def writeResultsToCsv(list: list, outputfile) -> bool:
    try:
        with open(outputfile, "w", newline="") as f:
            writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_ALL)
            writer.writerows(list)
        f.close()
        return True
    except Exception as e:
        p(error, 'Saving file', outputfile, 'with', len(list)
                 , 'records failed with error', e
                 , 'Do you have sufficient rights?')
        return False

#  ********
#  load results from files
def loadResultsFromCsv(filename) -> list:
    try:
        with open(filename, "r", newline="") as f:
            reader = csv.reader(f, delimiter='\t')
            csvdata = list(reader)
        f.close()
        return csvdata
    except Exception as e:
        p(error, 'Loading results file', filename
                 , 'failed with error', e
                 , 'Do you have sufficient rights?')
        return False

#  ********
# remove duplicates from list
def removeDuplicates(inlist)->list:
    # insert the list to the set
    list_set = set(inlist)
    # convert the set to the list
    unique_list = (list(list_set))
    return unique_list

#  ********
#  check if dir exists
#  if not create it
#  > returns True|False
def doDirCreate(folders: list) -> bool:

    # remove duplicates
    folders=removeDuplicates(folders)
    n=0
    for folder in folders:
        if n == 0 or n == 50: 
            p(warning,'Creating folders in folder list'
                , n, 'of', len(folders)) 
            n=0
        n+=1
        target=settings["foldertarget"] 
        drive, dirs = os.path.splitdrive(folder[0].replace(target,''))
        splitdirs = dirs.split('\\')[1:]
        if len(splitdirs)==0:
            drive, dirs = os.path.splitdrive(str(folder).replace(target,''))
            splitdirs = dirs.split('\\')[1:]
            
        p(allmsg,'Target root', target, 'folder', str(folder[0]), 
                 'drive', drive, 'path', dirs)
        
        for dir in splitdirs:
            target = target+'\\'+dir
            p(allmsg,'Target for folder creation', target)
            if not os.path.isdir(target):
                try:
                    os.mkdir(target)
                    p(verbose,'Creation of', target, 'succeeded.')
                except Exception as e:
                    p(error,'Creation failed with error message:',e)
                    pass

    return True

#  ********
#  check files from filelist
#  against existing files
def hashfile(filepath:str):
    
    with open(filepath, 'rb') as inputfile:
        data = inputfile.read(8196)
    
    return hashlib.md5(data).hexdigest()
    
#  ********
#  check files from filelist
#  against existing files
def checkFiles(fileList, verificationType) -> bool:

    global now
    
    rootFolder = settings["foldertarget"]
    # 1. does file exist in foldertarget?
    renameFiles = []
    noFolder = []
    existsButDifferent = []
    deleteSourceFile = []
    
    n=0
    for file in fileList:
        # file[0] = 'hashedvalue'
        # file[1] = 'filepathname'
        # file[2] = 'filename'
        # file[3] = 'creationDate'
        if n == 0: 
            p(verbose,'\nEvaluating', len(fileList), 'files \
                in files list, busy with ', n)
        n+=1
        if verificationType == 'ymd_structure':
            # get root folder name
            skip = False
            try:
                rootYear = file[3][0:4]
                rootMonth = file[3][4:6]
                rootDay = file[3][6:8]
                
            except TypeError as e:
                p(info,'A date type error exception occured when \
                    evaluating the file date of file', file,'Skipping \
                    this one, the error message was', e)
                skip = True
                
            if not skip:
                target_dir = os.path.join(rootFolder,rootYear,
                                rootMonth,rootDay)

                if Path(target_dir).is_dir():
                    # dir exists
                    target_file = os.path.join(target_dir,file[2])
                    if Path(target_file).is_file():
                        p(verbose,'File', file[2], 'from date', file[3],
                            'exists in', target_dir)
                        # verify md5 hash
                        hashedvalue = hashfile(target_file)
                        
                        if not file[0] == hashedvalue:
                            p(verbose,'File', file[2], 'from date', file[3], 
                                'exists in', target_dir, 'but has different \
                                hash value')
                            existsButDifferent.append((file[1],target_file))
                        else:
                            # file is the same
                            deleteSourceFile.append((file[1],file[3]))
                    else:
                        p(verbose,'File', file[2], 'from date', file[3], 
                            'does not exists in', target_dir)
                        renameFiles.append((file[1], target_file))
                else:
                    p(verbose, 'Folder', target_dir, 'for file', file[2], \
                        'with date', file[3], 'does not exist.')
                    noFolder.append((target_dir))
                    # and add file as well to the list
                    renameFiles.append((file[1], 
                                os.path.join(target_dir,file[2])))
        if n==50:
            n=0            

    p(info,'')
    p(info, 'Files that are already present in \
        target directory:', len(deleteSourceFile))
    p(info, 'Files that are NOT present in \
        target directory:', len(renameFiles))
    p(info, 'Non existing TARGET directories:', len(noFolder))
    p(info, 'Existing but from source different files (md5 hash) in \
        TARGET directory:', len(existsButDifferent))
    
    if settings["resultssave"] or settings["action"]:
        p(info,'Saving results due to argument --saveresults (exit) or \
            --action (continue).')
        writeResultsToCsv(deleteSourceFile, now+"_deleteSourceFile.csv")
        writeResultsToCsv(renameFiles, now+"_renameFiles.csv")
        writeResultsToCsv(noFolder, now+"_noFolder.csv")
        writeResultsToCsv(existsButDifferent, now+"_existsButDifferent.csv")
        if not settings["action"]: 
            raise SystemExit(0)
        
    if (settings["foldercreate"] or 
        settings["sourcerename"] or 
        settings["sourcedelete"] ) and \
        not settings["action"]:
            p(info, 'For actions to be performed you *must* include \
                argument "-a"')
    else:
        if settings["foldercreate"] and len(noFolder)>0:
            p(info,'Creating folders in ', settings["foldertarget"])
            doDirCreate(noFolder)

        if settings["sourcerename"] and len(renameFiles)>0:
            p(info,'Renaming (moving) files to structure \
                in/under', settings["foldertarget"])
            renameTheFiles(renameFiles)

        if settings["sourcedelete"] and len(deleteSourceFile)>0:
            p(info,'Deleting source files under', 
                settings["folderinput"])
            deleteFiles(deleteSourceFile)

    if len(settings["resultsuse"])>0:
        now=settings["resultsuse"]

    return True

#  ********
#  is it a date?
def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try: 
        parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False

#  ********
#  return datetime object
def getDateFromFilename(filepath: str):
    
    dt = datetime.datetime.now()
    skip = False
    
    if os.path.isfile(filepath):
        try:
            file_path, filename = os.path.split(filepath)

        except Exception as e:
            p(error, 'Unable to get filename from', filepath, 
                    'The received error is', e)
            return None

        datepatterns = [(r'\d{4}-\d{2}-\d{2}','%Y-%m-%d'), 
                        (r'\d{4}\d{2}\d{2}','%Y%m%d'),
                        (r'\d{2}\d{2}\d{4}','%d%m%Y'),
                        (r'\d{2}\d{2}\d{4}','%m%d%Y'),
                        (r'\d{2}-d{2}-d{4}','%m-%d-%Y')]
                        
        for r in datepatterns:
            try:
                datepattern = re.search(r[0], filename)
                if datepattern: 
                    if is_date(datepattern.group()):
                        skip = True
                        dt = datetime.datetime.strptime(
                                datepattern.group(), r[1]).date()
                        break

                else:
                    pass

            except ValueError as v:
                pass
                
            except AttributeError as a:
                pass

        if not skip:
            try:
                dt = datetime.datetime.fromtimestamp(
                            os.path.getmtime(filepath))
                            
            except Exception as f:
                p(error, 'Unable to get system date from file.\
                    Do you have enough rights to read the file? \
                    The respons was', f)
                return None


        dt = datetime.datetime.strftime(dt, '%Y%m%d')
        
        return dt

#  ********
#  
def getMovieProperties(filepath: str):
    try:
        properties = propsys.SHGetPropertyStoreFromParsingName(filepath)
        dt = properties.GetValue(pscon.PKEY_Media_DateEncoded).GetValue()

        if not isinstance(dt, datetime.datetime): 
            if not isinstance(dt, type(None)):
                dt = datetime.datetime.fromtimestamp(int(dt))
                dt = dt.replace(tzinfo=pytz.timezone('UTC'))
                
    except Exception as e:
        p(warning,'File',filepath,'could not be found',e)
        pass
    
    if dt == None:
        dt = getDateFromFilename(filepath)

    return dt

# ********
# 
def getPictureInfo(filepath):
    
    date_taken_tags = [ 'EXIF DateTimeOriginal', 'DateTimeOriginal', 
                'EXIF DateTimeDigitized', 'DateTimeDigitized', 
                'EXIF DateTime', 'DateTime' ]
    skip = False

    try:
        file = open(filepath, 'rb')
        tags = exifread.process_file(file)
        file.close()

    except Exception as e:
        p(verbose, '\t\tCould not read exif data file, error', e)
        skip = True
        
    date_taken = None
    if not skip:
        for tag in date_taken_tags:
            if tag in tags:
                date_taken = tags[tag]
                break
    
    if date_taken == None:
        date_taken = getDateFromFilename(filepath)
    else:
        if str(date_taken).find(':') > 0:
            try:
                date_taken = re.search(r'\d{4}:\d{2}:\d{2}', str(date_taken))
                date_taken = datetime.datetime.strptime(
                                date_taken.group(), '%Y:%m:%d').date()
                date_taken = datetime.datetime.strftime(date_taken,'%Y%m%d')
            except Exception as e:
                p(warning,'Following error while evaluating EXIF data\n', 
                    type(date_taken), date_taken, '\n', e)
                date_taken = None

    return date_taken

# ********
# returns list of DirEntry object
def getListOfFiles(dirName):
    # create a list of files 
    # from the given directory 
    listOfFiles = []
    try:
        for entry in os.scandir(dirName):
            if entry.is_file():
                listOfFiles.append(entry)
    except Exception as e:
        p(error, e)

    return listOfFiles

# ********
# returns list of DirEntry object
def getListOfFolders(dirName, listOfFolder):
    # create a list of sub directories 
    # names in the given directory 
    p(allmsg,dirName)
    try:        
        for entry in os.scandir(dirName):
            if entry.is_dir():
                listOfFolder.append(os.path.join(entry))
                listOfSubdirs = getListOfFolders(entry,listOfFolder)
    except Exception as e:
        p(error, e)

    return listOfFolder

# ********
# do the search
def performSearch():

    fileList = []
    folderList = []
    listOfFolders = []

    p(info, 'Searching for files in', '"'+settings["folderinput"]+'"', 
        'and folderssub' if settings["folderssub"] else '')

    listOfFolders = getListOfFolders(settings["folderinput"],
                                    [settings["folderinput"]])

    if len(listOfFolders) <= 1:
        listOfFolders.append(settings["folderinput"])
        listOfFolders=removeDuplicates(listOfFolders)

    p(info,'Found', len(listOfFolders), 'folders to process.')

    #  what extensions should be evaluated
    unknownExt = ['thm','db']   # skipped
    pictureExtensions = ['jpg', 'srw', 'jpeg', 'png', 'mp4','3gp']
    soundExtensions = ['aac','opus']
    #  if not these then movies

    a=0
    print()
    for folder in listOfFolders:
        a+=1
        p(info, 'Processing folder', folder)
        filesInFolder = getListOfFiles(folder)
        p(info, '\t... total of', len(filesInFolder), 'files found. \
            After this one another', len(listOfFolders)-a, 'folders to go.')

        b = 0
        t = 0
        n = 0
        begin = time.time()
        for file in filesInFolder:
            p(verbose, '\t\tprocessing file', file.name, 'as', t, 'of',
                len(filesInFolder))
            donotInclude = False
            skip = False
            if not file.is_file:
                foundFile = False
            else:
                foundFile = True
                
            if foundFile:
                t+=1
                n+=1
                filename = file.name
                filepath = file.path
                file_extension = filename.split('.')[-1:][0]
                p(allmsg,'File', filename, 'Path', 
                        filepath, 'Ext', file_extension)
                hashedvalue = hashfile(filepath)
                
                try:
                    unknownExt.index(
                        file_extension.lower() if sys.platform == 'win32' 
                        else file_extension)
                    skip = True
                    donotInclude = True

                except ValueError as v:
                    pass
                    
                if not skip:
                    try:
                        pictureExtensions.index(
                            file_extension.lower() if sys.platform == 'win32' 
                            else file_extension)
                        p(allmsg,'Getting pic info because of v1')
                        date_taken = getPictureInfo(filepath)
                        skip = True
                        
                    except ValueError as v:
                        pass

                if not skip:
                    try:
                        p(allmsg,'Getting sound info because of v2')
                        soundExtensions.index(file_extension.lower() 
                        if sys.platform == 'win32' else file_extension)
                        date_taken = getPictureInfo(filepath)
                        donotInclude = True
                        skip = False
                        
                    except ValueError as v:
                        pass
                
                if not skip:
                    try:
                        # must be something else
                        p(allmsg,'Getting movie info because of v3')
                        date_taken = getMovieProperties(filepath)
                        skip = True
                        
                    except ValueError as v:
                        pass
                
                if skip:
                    p(allmsg,date_taken)

                hashedvalue = hashfile(filepath)

                if not donotInclude:
                    fileList.append((hashedvalue, 
                                        filepath, 
                                        filename,
                                        date_taken))
            else:
                b+=1

            if n==50:
                end = time.time() 
                elapsed_time = round(end - begin, 2)   
                p(info,'\t\t... checked', t, 'files of', len(filesInFolder), 
                    '('+ str(b),'files skipped), expected another', 
                    round(((elapsed_time/n)*(len(filesInFolder)-t)/60),2), \
                    'minutes.')
                begin = time.time()
                n=0
                if int(settings["number"]) > 0 and int(settings["number"]) <= t:
                    break
                
    p(info, 'There are', len(fileList), 'results in the list...')
    # todo, something about duplicates
    return fileList

if __name__ == "__main__":

    #  --------
    #  loglevels CONSTANTS
    loglevels = ["silent","critical","error","warning",
                    "info","verbose","allmsg"]
    silent = 0
    critical = 1
    error = 2
    warning = 3
    info = 4
    verbose = 5
    allmsg = 6

    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    initialize()

    if settings["resultsuse"]:
        if settings["action"]:
            now = settings["resultsuse"]
            try:
                if settings["foldercreate"]:
                    p(info,'Going to create folders (if any)')
                    csvdata = loadResultsFromCsv(now+"_noFolder.csv")
                    result=doDirCreate(csvdata)
            except Exception as e:
                p(critical,'Something is serious wrong, error', e)

            try:
                if settings["sourcerename"]:
                    p(info,'Going to rename files (if any)')
                    csvdata = loadResultsFromCsv(now+"_renameFiles.csv")
                    result=renameTheFiles(csvdata)
            except Exception as e:
                p(critical,'Something is serious wrong, error', e)

        #try:
            if settings["sourcedelete"]:
                p(info,'Going to delete source files (if any)')
                csvdata = loadResultsFromCsv(now+"_deleteSourceFile.csv") 
                result=deleteFiles(csvdata)
        #except Exception as e:
        #    p(critical,'Something is serious wrong, error', e)
                    
            p(info, 'Finished performing actions with saved csv data \
                        from date', now)
                
            raise SystemExit(0)

    fileList = performSearch()

    if settings["foldertarget"]:
        checkFiles(fileList, settings["folderpattern"])
    else:
        p(info, 'Use the argument --output to check the file list'\
            ' against files in that folder structure.')
    p(info,'Finished.')
