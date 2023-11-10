import os
import shutil
from PIL import Image, UnidentifiedImageError
from datetime import date, datetime
from re import search
import hashlib

'''
Do a few tests to determine the year of the file. The first test is looking
if the file is a true JPEG and uses EXIF data to determine year. The next test
looks at the file name to compare to the list of year named directories looking
for a year in the name. Next it uses the file time stamps to discern a year.
This is the least accurate due to filesystem inconsistencies
'''


def move_file(year, file_to_move, base_move_path, available_paths, error_path, logfile):
    '''
    This is the move function that actually moves the files. It takes the year, the
    acutal file to move, the base path given by the user, the list of available year
    named folders in the base path, the error directory and the name of the logfile.
    '''

# Iterate the available years and move the file if the path exists
    if year in available_paths:
        try:
            full_path = f'{base_move_path}{year}\\{file_to_move}'
            if os.path.exists(full_path):
                
                # If a file with the same name exists in the destination, deconflict
                deleted, new_name = hash_check_copy(file_to_move, full_path, logfile)
                
                if not deleted:
                    shutil.move(new_name, base_move_path + year + '\\')
            else:
                try:
                    shutil.move(file_to_move, base_move_path + year + '\\')
                    logfile.write(f'Successfully moved {file_to_move} to {base_move_path} {year}\n')
                except Exception as e:
                    logfile.write(f'Could not move {file_to_move} due to {e}\n')
        
        except Exception as e:
            print(f'Did not move {file_to_move} due to {e}')
            logfile.write(f'Did not move {file_to_move} due to {e}\n')

# If the file path does not exist or there is some other error log an issue   
    else:
        #Write to the logfile that a file was not moved
        shutil.move(file_to_move, error_path)
        logfile.write(f'Failed to move {file_to_move} to {base_move_path}{year}\n')


def get_exif_data(file_to_move):
    '''
    This is the function that takes a file to move as an argument then determines
    if it is a JPEG. It will then attempt to grab the year taken from the metadata
    if it exists.
    '''

    try:
        opened = Image.open(file_to_move)
        if opened.format == 'JPEG':
            exif_data = opened.getexif()
            for key in exif_data:
                if key == 306:
                    year = exif_data.get(key)[0:4]
                    return year
    
    #Catch an error when the file is not an image
    except UnidentifiedImageError:
        pass


def regex_file(file_to_move, available_paths):
    '''
    This is a regex through the filename to try and discern if a year is within.
    Some applications create an image with a name like 20207543232_001.jpg where
    2020 is the year. This can put images in the wrong dir because of arbitrary
    naming.
    '''
    for year in available_paths:
        result = search('.*' + year + '.*', file_to_move)
        if result:
            return year


def get_file_mod_time(file_to_move):
    '''
    This takes the file to move as an argument and uses the system modified time
    stamp to determine the year. This works depending on how the images got to
    the system. It will always find a modified time but the time stamp may have
    been modified after the picture was taken based on how it got moved.
    '''
    date_object = datetime.fromtimestamp(os.path.getmtime(file_to_move))
    year = date_object.strftime('%Y %b %d').split()[0]
    return year


# If a copy is found, hash both files to check, if copies delete file to move
# If it is not a copy, it renames it and moves it
def hash_check_copy(move_file, found_file, logfile):
    '''
    This function will deconflict files with the same name. It takes in the file to move
    and the file it found in one of the storage directories. It hashes both and compares
    the hashes. If the hashes are the same it deletes the file to move, if the hashes are
    different, it renames the file to move by appending the last 2 bytes of the hash to
    the end of the filename.
    '''
    with open (move_file, 'rb') as moving_file:
        data = moving_file.read()
        first_md5 = hashlib.md5(data).hexdigest()
    with open (found_file, 'rb') as existing_file:
        data = existing_file.read()
        second_md5 = hashlib.md5(data).hexdigest()    
    if first_md5 == second_md5:
        logfile.write(f'{move_file} and {found_file} are the same, deleted {move_file}\n')
        os.remove(move_file)
        deleted = True
        return deleted, ''
    else:
        file_name = move_file.split('\\'[-1])
        isolated_name = file_name[0].split('.')[0]
        name_without_ext = isolated_name + first_md5[-4:]
        new_name = name_without_ext + '.' + file_name[0].split('.')[1]
        os.rename(move_file, new_name)
        deleted = False
        return deleted, new_name        


def main():

    # Global year variable for the year of the photo
    year = ''

# Create an empty list to store the available year paths in the base directory
    possible_paths = []

# Ask the user about some system information, including a logile name
    pic_path = input('Where are the pics to be organized located: ')
    if pic_path[-1] != '\\':
        pic_path += '\\'
    
    base_dir = input('What is the parent path where the year named folders are located: ')
    if base_dir[-1] != '\\':
        base_dir += '\\'
    
    log_name = input('Name the logfile, default is pic_org.txt which will be stored in the parent path: ')
    if not log_name:
        log_name = 'pic_org.txt'
    
    error_pic_path = input('Where to place pics where an error was encountered: ')
    if pic_path[-1] != '\\':
        pic_path += '\\'
    
    # Populate the possible_paths list
    for folder in os.listdir(base_dir):
        if folder.isnumeric():
            possible_paths.append(folder)
    
    # Open the logfile in append mode for writing
    logfile = open(base_dir + log_name, 'a')

    # Change the working directory to where the pictures are located to iterate them
    os.chdir(pic_path)
    contents = os.listdir()

    for file in contents:

        # First check for exif data if the file is true JPEG
        year = get_exif_data(file)

        # If the function returns a year, try to move the file
        if year:
            move_file(year, file, base_dir, possible_paths, error_pic_path, logfile)

        # No year returned so move on to regex the filename
        else:
            year = regex_file(file, possible_paths)

            # If this function finds a year in the filename, try to move that file
            if year:
                move_file(year, file, base_dir, possible_paths, error_pic_path, logfile)

            # No exifdata and no found year in filename, move on to system modified time
            else:
                year = get_file_mod_time(file)

                # Try to move the file based on system modified time
                if year:
                    move_file(year, file, base_dir, possible_paths, error_pic_path, logfile)
                
                # Log the fact that the file was not moved
                else:
                    try:
                        shutil.move(file, error_pic_path)
                        logfile.write(f'Moved {file} to {error_pic_path}')
                    except Exception as e:
                        logfile.write(f'\nAfter going through all functions, failed to move {pic_path}{file}')
                        logfile.write(e)

    print('Done')
        

if __name__ == "__main__":
    main()


