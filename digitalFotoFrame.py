# -*- coding: utf-8 -*-
"""
-------------------------------------------------------------------
Digital Photo Frame in python

Created on Sun Jan 15 2023

@author: DeanG

Python implementation of a photo slide show of pictures
from a given folder (folder tree)

- Photos are shown with a programmable pause per photo
- Photos are shown in some semi-random order
- Photos are stored in a folder tree under a single top-level folder

- there is a config file that configures the location of the photos,
- the wake and sleep hours (display will go dark during sleep time)
- the delay (in seconds) while each photo is displayed

Tested with Windows 11 and Raspberian Linux.
- Dependencies 
   - python 3
   - standard python 3 packages (os, datetime, random, sys, time)
   - opencv python platform (cv2) - install with pip using
      
        pip3 install opencv-python

Sample config file, four line text file with key=value format

DELAY=3.5
WAKE=6
SLEEP=21
PATH=/media/pi/photoframe

DELAY is delay in seconds while each photo is being shown
WAKE is the wake-up hour when photos will start showing
SLEEP is the sleep hour when photos will stop showing
PATH is the path to the folder tree where the photos are to be found

jpg and png files stored in the specified location will be shown
    
-------------------------------------------------------------------
"""

# Version 1.0 - 27-Nov-2023 - deangi - initial version

# imports - all standard python modules except for cv2
import os
import datetime
import cv2 # opencv - pip3 install opencv-python
import random
import sys
import time

#-------------------------------------------------------------
#--- scan a folder tree (recursively) for jpg or png files
#-------------------------------------------------------------
def scanForFiles(folder):
    pictureFiles=[]
    itr=os.scandir(folder)
    for entry in itr:
        if entry.is_file():
            fn=entry.name.lower()
            if fn.endswith('.jpg') or fn.endswith('.png'):
                pictureFiles.append(entry.path)
        if entry.is_dir(): # recurse for sub-folders
            x=scanForFiles(entry.path)
            pictureFiles.extend(x)
    #itr.close()
    return pictureFiles


#-------------------------------------------------------------
#--- Try to open a control file and read settings from it
#-------------------------------------------------------------
#-------------------------------------------------------------
def checkForControlFile(controlFn,delay,wakeHour,bedtimeHour,photoFolder):
    #
    #   Sample control file has four lines in KEY=VALUE format
    #   - delay in seconds
    #   - wake hour (0..23)
    #   - sleep hour (0..23)
    #   - path to find picures and control file
    #   
    #   File is deposited into the top folder where the picures are stored (PATH)
    #   File is named instructions.ini
    #   File has 4 lines
    #   
    #   Control file will be read hourly
    #   
    #DELAY=3.5
    #WAKE=6
    #SLEEP=21
    #PATH=/media/pi/photoframe
    #
    result=[delay,wakeHour,bedtimeHour,photoFolder,False]
    readparams=0 # bitwise log of keywords found to verify we had a full
    # configuration file with every line in it that we expect
    #print(controlFn)
    try:
        with open(controlFn,'r') as finp:
            print(datetime.datetime.now(),'Reading configuration file')
            for line in finp:
                print(line)
                if line.startswith('DELAY='):
                    x=float(line[6:])
                    x=max(1.,x)
                    x=min(60.,x) # limit 1..60
                    result[0]=x
                    readparams=readparams | 1
                if line.startswith('WAKE='):
                    x=float(line[5:])
                    x=max(0.,x)
                    x=min(10.,x) # limit 0..60
                    result[1]=int(x)
                    readparams=readparams | 2
                if line.startswith('SLEEP='):
                    x=float(line[6:])
                    x=max(0.,x)
                    x=min(23.,x) # limit 0..60
                    result[2]=int(x)
                    readparams=readparams | 4
                if line.startswith('PATH='):
                    result[3]=line[5:-1] # strip off new line at end
                    readparams=readparams | 8

    except:
        pass
    print('Read configuration file results ',result)
    if (readparams == 15):
        result[4] = True # read file properly, all 4 bits set = 1111 = 0xf = 15
    return result

#-------------------------------------------------------------
# main photo frame loop
#
# - Run the photo frame code continuously displaying photos
#   from the specified folder.   
# - Go dark at bedtimehour and light up again at wakehour
# - Check every hour for a new instructions.ini file with 
#   parameter updates.
# - Rescan for pictures every hour in case user has deleted 
#   or added pictures
# - One idea is that an FTP server or SAMBA remote disk mount
#   could be used to update the photos to be shown and to 
#   update the instructions.ini file to change parameters
#-------------------------------------------------------------
def runFotoFrame(params):

    # grab our parameters that control operation of the
    # digital foto frame
    delay=params[0]         # delay in seconds to show each picture
    wakehour=params[1]      # hour (int 24 hr format 0..23) to start showing
    bedtimehour=params[2]   # hour (in 24 hr format 0..23) to stop showing
    photoFolder=params[3]   # be real careful when changing this in config file
    configfn=params[4]      # name of config file to look for in top level folder 
    
    # determine if this is a windows OS based system
    isWindows=sys.platform.startswith('win') # 'win32' or 'linux2' or 'linux'

    # initialize a CV2 frame to cover the entire screen
    cv2frame='frame'
    cv2.namedWindow(cv2frame, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(cv2frame, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    # let's find out what size of display we're working with    
    tmp=cv2.getWindowImageRect(cv2frame)
    wid=float(tmp[2])
    hgt=float(tmp[3])
    # sometimes the getWindowImageRect returns nonsense like
    # width or height of -1 or some other non useful value
    if hgt<480. or wid<640.:
        hgt=1080. # assume a 9h x 16w form factor
        wid=1920.
    #print(hgt,wid)
    
    # scan the photoFolder for a list of picture files
    pictureFiles=scanForFiles(photoFolder)
    random.shuffle(pictureFiles) # randomly shuffle the picture files
    print(datetime.datetime.now(),'Scan found',len(pictureFiles),'files')

    # initialize for hourly and sleep processing    
    lastHour=datetime.datetime.now().hour
    sleeping=False
    done=False
    if not isWindows:
        os.system("xset s off") # screen blanking off
    
    # and loop forever (until some key is hit)
    while not done:
        
        # during waking hours, display pictures
        # during sleeping hours, keep display blanked
        for fn in pictureFiles:

            # let's see if it's time to do hourly tasks
            now=datetime.datetime.now()
            hour=now.hour
            if not isWindows:
                os.system("xset dpms force on");

            #-- hourly tasks, only done when not sleeping            
            if hour!=lastHour and not sleeping:
                lastHour=hour
                if not isWindows:
                    os.system("xset s off") # screen blanking off
                # try to read configuration file instructions.ini
                controlFn=os.path.join(photoFolder,configfn)
                result=checkForControlFile(controlFn,delay,wakehour,bedtimehour,photoFolder)
                if result[4]: # set to true for successful config file read
                    delay=result[0]
                    wakehour=result[1]
                    bedtimehour=result[2]
                    photoFolder=result[3]
                # rescan folder
                pictureFiles=scanForFiles(photoFolder)
                random.shuffle(pictureFiles)
                print(datetime.datetime.now(),'Scan found',len(pictureFiles),'files')

            #--- run always, do wake up tasks or sleep tasks
            #
            # for example wakehour might be 9am and bedtimehour might be 9pm
            # wakehour=9 and bedtimehour=21 (12+9)
            if hour>=wakehour and hour<bedtimehour:
                # we are in wake up time of day

                #--- if we were sleeping, then it is time to wake up
                if sleeping:
                    print(datetime.datetime.now(),'Wake up')
                    if not isWindows:
                        os.system("xset s off") # screen blanking off
                        os.system("xset dpms force on");
                    sleeping=False

                #--- display a photo
                # handle fault in loading a picture
                gotImg=False
                try:
                    print('loading',fn)
                    img = cv2.imread(fn, 1)
                    if len(img)>0:
                        gotImg=True
                except:
                    gotImg=False
                if not gotImg:
                    continue
    
                #-- now, maybe resize image so it shows up well without changing the aspect ratio
                #   add a border if the aspect ratio is different than the screen
                # so we upscale or downscale so it maxes out either the
                # horizontal or vertical portion of the screen
                # then add a border around it to make sure any left-over
                # parts of the screen are blacked out
                widratio=wid/img.shape[1]
                hgtratio=hgt/img.shape[0]
                ratio=min(widratio,hgtratio)
                dims=(int(ratio*img.shape[1]),int(ratio*img.shape[0]))
                #print(fn,img.shape,ratio,dims[1],dims[0])
                imgresized=cv2.resize(img,dims,interpolation = cv2.INTER_AREA)
                #print(imgresized.shape)
                # now, one dimension (width or height) will be same as screen dim
                # and the other may be smaller than the screen dim.
                # we're going to use cv.copyMakeBorder to add a border so we
                # end up with an image that is exactly screen sized
                widborder=max(1,int((wid-imgresized.shape[1])/2))
                hgtborder=max(1,int((hgt-imgresized.shape[0])/2))
                #print(hgtborder,widborder)
                imgbordered=cv2.copyMakeBorder(imgresized,hgtborder,hgtborder,widborder,widborder,cv2.BORDER_CONSTANT)
                #print('resized,bordered',imgbordered.shape)

                # and now show the image that has been resized and bordered
                cv2.imshow(cv2frame, imgbordered)
                #--- now we pause while the photo is displayed, we do this
                #    by waiting for a key stroke.
                k = cv2.waitKey(int(delay*1000)) & 0xff
                # 255 if no key pressed (-1) or ascii-key-code (13=CR, 27=esc, 65=A, 32=spacebar)
                if k!=0xff:
                    # if a key was pressed, exit the photo frame program
                    done=True
                    break  
            else:
                #-- during sleep time we go here
                # during sleep time, blank the screen
                if not sleeping:
                    print(datetime.datetime.now(),'Going to sleep')

                if not isWindows:
                    os.system("xset dpms force standby");
                sleeping=True
                k = cv2.waitKey(300*1000) & 0xff # wait 300 seconds
                # 255 if no key pressed (-1) or ascii-key-code (13=CR, 27=esc, 65=A, 32=spacebar)
                if k!=0xff:
                    done=True
  
    # when the photo display session ends, 
    # we need to clean up the cv2 full-frame window
    cv2.destroyWindow(cv2frame)

#------------------------------------------------------------
# top-level python script
#
# set up some global variables to default values.
# The config file sets these values on startup
#
# later on, these may be read and changed by a control
# file that is looked for every hour or two in the scanned
# folder.   If you want to change these while the pix frame
# is running, you can change this file at any time.
#
# command line:
#    python3 digitalFotoFrame.py configfile.txt
#-------------------------------------------------------------

if __name__ == "__main__":

    #----------------------------------    
    #---- default parameter values ----
    #----------------------------------
    photoFolder='/media/HDD'    # top level folder for pictures
    delay=4                     # seconds for each displayed picture
    wakehour=7                  # 07am = 0700 = 7, start showing pictures
    bedtimehour=21              # 10pm = 2100hrs = 21, stop showing pictures

    print("---- Digital Foto Frame - Starting ----")

    configFileRead=False
    configfn="photoframe.ini" # default name to look for hourly in top level folder
    # search arg list for
    if len(sys.argv)>1:
        configfn=sys.argv[1]

    print("reading config file: ",configfn)
    result=checkForControlFile(configfn,delay,wakehour,bedtimehour,photoFolder)
    if result[4]: # set to true if successfull read of config file
        delay=result[0]
        wakehour=result[1]
        bedtimehour=result[2]
        photoFolder=result[3]
        configFileRead=True
        print("Config file read: ",delay,wakehour,bedtimehour,photoFolder)
    time.sleep(3) # wait just a bit to read messages if any
    if not configFileRead:
        print("\n--- Unable to read config file ---\n")
    else:
        # and then, let's get this show on the road
        params=[delay,wakehour,bedtimehour,photoFolder,configfn]
        runFotoFrame(params)
        
    
