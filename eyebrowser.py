"""
eyebrowser.py
version 2.1
package github.com/ajk77/EyeBrowserPy
Created by AndrewJKing.com|@andrewsjourney

This code has functions to start and stop and Tobii EyeX eye tracker. 
It also processes and stores posts from eyebrowser.js.
The code for mapping and analysing the output of this file is in eyeanalysis.py.

DEPENDENCIES:
To connect to the eye tracking you must have the gazesdk code from: https://github.com/balancana/gazesdk
^This code requires you to put TobiiGazeCore32.dll into your /python/lib/site-packages/

---LICENSE---
This file is part of EyeBrowserPy

EyeBrowserPy is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or 
any later version.

EyeBrowserPy is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with EyeBrowserPy.  If not, see <https://www.gnu.org/licenses/>.
"""
# URL handling

# Views.py handling (skipped directly to the below functions, if possible)

# stop and stop eye tracker handling.

from gazesdk import *
import time
import sys
import os.path
from os import walk
import numpy as np

t = False

if os.path.isdir("../../models/"):  # set this to your output directory
    local_dir = os.getcwd() + "/../../models/"

out_file = None

def start_eye_stream(pat_id='0'):
    """
    Code for running eye tracker.
        ->Should be started when on LEMR home screen.
        ->Should be terminated after user unloads page of the last desired patient case.
    """
    global t
    global out_file
    # should be started before going to patient case.
    # could look to see if there is a calibration code bindings
    try:
        url = get_connected_eye_tracker()
        t = Tracker(url)
        t.run_event_loop()
        out_file = open(local_dir + 'eye_stream/'+pat_id+'_'+str(time.time()) + '.txt', 'w+')
        t.connect()
        t.start_tracking()

        try:
            while True:
                curr_time = time.time()
                data = t.event_queue.get()
                left_x = data.left.gaze_point_on_display_normalized[0]
                right_x = data.right.gaze_point_on_display_normalized[0]
                left_y = data.left.gaze_point_on_display_normalized[1]
                right_y = data.right.gaze_point_on_display_normalized[1]
                if left_x != 0.0:
                    if right_x:
                        x = (left_x+right_x)/2.0
                    else:
                        x = left_x
                else:
                    x = right_x
                if left_y != 0.0:
                    if right_y:
                        y = (left_y+right_y)/2.0
                    else:
                        y = left_y
                else:
                    y = right_y

                out_file.write(str(x)+','+str(y)+','+str(curr_time)+'\n')

                t.event_queue.task_done()
        except KeyboardInterrupt:
            print 'eye tracking terminated'

        t.stop_tracking()
        t.disconnect()
        out_file.close()

        t.break_event_loop()
    except TrackerError:
        print '***cannot connect to the eye tracker***'
        return False
    return True


def stop_eye_stream():
    """
    Stops the eye stream output and closes file.
    """
    global t
    global out_file

    if t:
        t.stop_tracking()
        t.disconnect()
        out_file.close()
        t.break_event_loop()
        t = False
    return

# catch and print container location handling. 