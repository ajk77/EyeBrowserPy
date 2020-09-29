"""
DEPRECIATED - old_eyeanalysis.py
version 2.1
package github.com/ajk77/EyeBrowserPy
Created by AndrewJKing.com|@andrewsjourney
This code maps and analyzes the output from eyebrowser.js and eyebrowser.py.
It uses timestamps to map the two fields together.
An area of interest (I-AOT) algorithm is used. The other option is dispersion (I-DT). 
The mapping results in an interaction stream file. This file is then analysed to summarize the eye interaction. 
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

import time
import sys
import os.path
from os import walk
import numpy as np


if os.path.isdir("../../models/"):
    local_dir = os.getcwd() + "/../../models/"


class ErrorDistribution:
    """
    Code for each error distribution. Each eye stream data point has its own based off of the x,y coordinate.
      Each inner cell is organized in a 1 dimensional list.
    """
    def __init__(self, distribution, x, y):
        self.pos = [y-50, x-50, y+50, x+50]
        self.D = distribution

    def overlap(self, pos):
        try:
            if self.pos[0] > pos[2] or self.pos[1] > pos[3] or self.pos[2] < pos[0] or self.pos[3] < pos[1]:
                return False
            else:
                return True
        except IndexError:
            print ('***caught def overlap IndexError ' + str(pos) + '***')
            return False

    def calc_overlap(self, pos):
        cols = [-1, -1]
        rows = [-1, -1]
        for i in range(100):
            if cols[0] == -1:
                if self.pos[1] + i >= pos[1]:
                    cols[0] = i
            elif cols[1] == -1:
                if self.pos[1] + i > pos[3]:
                    cols[1] = i-1
            if rows[0] == -1:
                if self.pos[0] + i >= pos[0]:
                    rows[0] = i
            elif rows[1] == -1:
                if self.pos[0] + i > pos[2]:
                    rows[1] = i-1
        if cols[0] == -1:
            cols[0] = 0
        if cols[1] == -1:
            cols[1] = 100
        if rows[0] == -1:
            rows[0] = 0
        if rows[1] == -1:
            rows[1] = 100

        return self.D[rows[0]:rows[1], cols[0]: cols[1]].sum()


class Matrix:
    """
    Matrix used for calibration
    """
    def __init__(self):
        self.An = 1.0
        self.Bn = 1.0
        self.Cn = 0.0
        self.Dn = 1.0
        self.En = 1.0
        self.Fn = 0.0

    def __str__(self):
        return "Matrix: [" + str(self.An) + ', ' + str(self.Bn) + ', ' + str(self.Cn) + ', '\
               + str(self.Dn) + ', ' + str(self.En) + ', ' + str(self.Fn) + ']'

    def calc_calibration_values(self, dir, stream_file):
        # load calibration pixelmap file to data structure
        box_start_times = []
        box_x_centers = []
        box_y_centers = []
        box_end_times = []
        cal_pixelmap_file = open(dir + 'pixelmaps/pat_calibration.txt', 'r')
        for q in range(9):
            box_start_times.append(float(cal_pixelmap_file.readline()[3:]))
            location = [int(x) for x in cal_pixelmap_file.readline().split(',')]
            box_x_centers.append(int(location[1]+(location[3]-location[1])/2))  # will be within a pixel of truth
            box_y_centers.append(int(location[0]+(location[2]-location[0])/2))
            box_end_times.append(float(cal_pixelmap_file.readline()[3:]))
            discard = cal_pixelmap_file.readline()
            del q, discard
        cal_pixelmap_file.close()

        # find error in calibration file
        current_box = 0  # the current red box number
        x_es_points = []  # list of eye_stream points for a red box
        y_es_points = []
        x_medians = []  # list of median eye_steam points for each red box
        y_medians = []
        es_file = open(dir + 'eye_stream/' + stream_file, 'r')
        # process eye_stream file line by line
        for line in es_file:
            x, y, time = [float(x) for x in line.rstrip().split(',')]
            x = x * 1920
            y = y * 1080

            if time < box_start_times[current_box]:
                continue  # tracking before interaction started
            elif time >= box_end_times[current_box]:
                # calc and store eye_stream points medians
                if x_es_points:
                    x_medians.append(np.median(np.asarray(x_es_points)))
                    y_medians.append(np.median(np.asarray(y_es_points)))
                else:
                    x_medians.append(box_x_centers[current_box])
                    y_medians.append(box_y_centers[current_box])
                    print ("***WARNING this calibration box might not have worked: " + str(current_box) + " ***")
                # reset params
                x_es_points = []
                y_es_points = []
                current_box += 1  # move to next red test box
                if current_box == 9:
                    break
            elif x == 0.0 or y == 0.0:
                continue  # eyes were off screen EyeX
            elif x == -1.0 or y == -1.0:
                continue  # eyes were off screen X2-30
            else:   # found tracking within interaction
                curr_x_e = box_x_centers[current_box] - x
                curr_y_e = box_y_centers[current_box] - y
                if abs(curr_x_e) > 100 or abs(curr_y_e) > 100:
                    continue  # skip values way out of range
                x_es_points.append(x)
                y_es_points.append(y)
        es_file.close()

        # set_calibration_matrix
        x = np.row_stack(box_x_centers)
        y = np.row_stack(box_y_centers)
        x_ = np.asarray(x_medians)
        y_ = np.asarray(y_medians)

        try:
            # calc values
            o = np.ones((x_.size, 1))
            a_ = np.column_stack((x_, y_, o))
            a_t = np.transpose(a_)
            pim = np.dot(np.linalg.inv(np.dot(a_t, a_)), a_t)  # pseudo-inverse matrix
            v_xs = np.dot(pim, x)
            v_ys = np.dot(pim, y)

            # set values
            self.An = v_xs[0, 0]
            self.Bn = v_xs[1, 0]
            self.Cn = v_xs[2, 0]
            self.Dn = v_ys[0, 0]
            self.En = v_ys[1, 0]
            self.Fn = v_ys[2, 0]
        except np.linalg.linalg.LinAlgError:
            print ('***caught def calc_calibration_values LinAlgError***')

        return

    def get_fixed_display_point(self, x, y):
        new_x = ((self.An * x) + (self.Bn * y) + self.Cn)
        new_y = ((self.Dn * x) + (self.En * y) + self.Fn)
        return int(round(new_x)), int(round(new_y))


def map_eye_stream(user_dir, distribution_file, use_extra_calibration=True, max_output=99, min_count=10):
    """
    Maps eye stream to pixelmaps and created interaction files
        > Assumes one interaction per patient
        > Assumes has calibration file
    """
    distribution = np.loadtxt(local_dir + 'eye_tests/'+distribution_file, delimiter=',')
    interaction_files = []

    # # # Identify interactions in directory and calculate calibration matrix # # #
    patient_ids = []  # holds strings of each patient id in directory
    eye_stream_files = {}  # holds the filename of each eye_scream_file in directory
    calibration_matrix = Matrix()  # the nine-point calibration matrix
    for (p, d, f) in walk(user_dir+'eye_stream/'):
        for file in f:
            curr_stream_id = file.split('_')[0]
            if curr_stream_id[0] == 'c':
                calibration_matrix.calc_calibration_values(user_dir, file)
            else:
                if curr_stream_id in patient_ids:
                    eye_stream_files[curr_stream_id].append(file)
                else:
                    patient_ids.append(curr_stream_id)
                    eye_stream_files[curr_stream_id] = [file]

    # # # Analyze eye streams # # #
    for pat_id in patient_ids:
        curr_pixelmap_file = open(user_dir+'pixelmaps/'+'pat_'+pat_id + '.txt', 'r')  # open file
        pixelmap_times = [[], []]  # [[stage 1], [stage 2]]
        pixelmap_items = [[], []]  # interaction wide
        curr_timestamp = 0
        i = 0  # 0 = stage 1 and 1 = stage 2
        for line in curr_pixelmap_file:
            if line == '#refresh\n':  # new interaction
                continue
            elif line[:5] == '#end:':  # end of interaction
                interaction_end_time = float(line[5:].rstrip())
                pixelmap_times[1].append(interaction_end_time)
            elif line[0:3] == '>>>':
                curr_timestamp = float(line[3:])
            else:
                pixelmap_item_builder = {}  # pixelmap wide
                split_line = line.rstrip().split(',')
                if split_line[0] == 'PausedScreen':
                    continue
                elif i == 0:
                    if split_line[0] != 'FirstView':
                        pixelmap_times[0].append(curr_timestamp)  # add end time to stage 1
                        i = 1  # advance to stage 2
                    else:
                        split_line = split_line[5:]  # skip the first view item
                for q in range(0, len(split_line), 5):
                    pixelmap_item_builder[split_line[q]] = [int(x) for x in split_line[q+1:q+5]]
                pixelmap_items[i].append(pixelmap_item_builder)
                pixelmap_times[i].append(curr_timestamp)

        # # # Calculate interaction stream # # #
        for i in range(2):  # stage 1 and stage 2
            #print ('\t\t\trange: ' + str(i))
            # insure pixelmap file was formatted properly with a single interaction and one pixelmap per timestamp
            if len(pixelmap_times[i]) != (len(pixelmap_items[i]) + 1):  # plus one because of end of interaction time
                print ("*** Warning, inconsistent pixelmap file. The interaction stream for " + pat_id + \
                      "_stage-" + str(i) + " was skipped! ***")
                continue

            eye_stream_file = open(user_dir+'eye_stream/'+eye_stream_files[pat_id][i], 'r')  # open eye stream file
            interaction_files.append('interaction_stream/'+pat_id+'_'+str(pixelmap_times[i][0])+
                                     '-'+str(pixelmap_times[i][-1])+'_stage-'+str(i+1)+'.txt')
            interaction_stream_file = open(user_dir+interaction_files[-1], 'w+')  # generate interaction stream file
            interaction_stream_file.write('#timestamp|X|Y|item_name>weight\n')
            #print ('\t\t\tfile: ' + eye_stream_files[pat_id][i])
            pixelmap_progress = 0
            for line in eye_stream_file:
                x, y, time = [float(x) for x in line.rstrip().split(',')]

                if time < pixelmap_times[i][pixelmap_progress]:  # tracking before interaction started
                    continue
                elif time > pixelmap_times[i][pixelmap_progress+1]:  # time past current pixelmap
                    pixelmap_progress += 1
                    if pixelmap_progress < len(pixelmap_items[i]):  # move to next pixelmap
                        interaction_stream_file.write('#scroll\n')
                    else:  # passed last pixelmap
                        interaction_stream_file.write('#end\n')
                        break
                if x == 0.0 or y == 0.0:  # eyes were off screen
                    continue
                else:   # time for mapping
                    x = x*1920
                    y = y*1080
                    if use_extra_calibration:
                        x, y = calibration_matrix.get_fixed_display_point(x, y)
                    curr_distribution = ErrorDistribution(distribution, x, y)

                    interaction_stream_file.write(str(time) + '|' + str(x) + '|' + str(y))
                    for name, pos in pixelmap_items[i][pixelmap_progress].iteritems():
                        #if eye_stream_files[pat_id][i] == '34817966_1503943426.55.txt':
                        #    print (name + '\t' + str(pos))
                        if curr_distribution.overlap(pos):
                            curr_item_weight = curr_distribution.calc_overlap(pos)
                            if curr_item_weight > 0:  # skip when item weight was zero.
                                interaction_stream_file.write('|'+name+'>'+str(curr_item_weight))
                    interaction_stream_file.write('\n')

            eye_stream_file.close()
            interaction_stream_file.close()

    # # # Summarize interaction # # #
    if use_extra_calibration:
        out_file_name = user_dir+'/calibrated_summary_'+distribution_file
    else:
        out_file_name = user_dir + '/summary_' + distribution_file
    summary_out = open(out_file_name, 'w+')
    summary_out.write('#name|weight_ratio|total_weight|hit_count\n')
    for interaction_file_name in interaction_files:
        item_name_weights = {}
        all_item_weight = 0.0
        interaction_in_file = open(user_dir + interaction_file_name, 'r')
        for line in interaction_in_file:
            if line[0] == '#':
                continue  # skip header comment
            split_line = line.split('|')
            for i in range(3, len(split_line)):
                name, weight = split_line[i].split('>')
                if name not in item_name_weights.keys():
                    item_name_weights[name] = [float(weight)]
                else:
                    item_name_weights[name].append(float(weight))
                all_item_weight += float(weight)
        interaction_in_file.close()

        summary_tuples = []
        for name in item_name_weights.keys():
            curr_ratio = round(sum(item_name_weights[name])/all_item_weight, 4)
            curr_weight = round(sum(item_name_weights[name]), 4)
            curr_count = len(item_name_weights[name])
            # if curr_weight > 1:  #####Add if I want a cut off#########################
            summary_tuples.append((name, curr_ratio, curr_weight, curr_count))
        summary_tuples.sort(key=lambda m_tup: m_tup[1], reverse=True)

        summary_out.write('\n\n>>>patient_interaction|' + interaction_file_name.split('/')[1][:-4])
        for i in range(len(summary_tuples)):
            tup = summary_tuples[i]
            summary_out.write('\n'+tup[0]+'|'+str(tup[1])+'|'+str(tup[2])+'|'+str(tup[3]))
            if tup[3] < min_count:
                break
            if i == (max_output-1):
                break
    summary_out.close()

    return


def calc_time(user_dir):
    """
    Calculates the assessment time for each case interaction.
    """
    # # # Identify interactions in directory and calculate calibration matrix # # #
    patient_ids = []  # holds strings of each patient id in directory
    eye_stream_files = {}  # holds the filename of each eye_scream_file in directory
    calibration_matrix = Matrix()  # the nine-point calibration matrix

    for (p, d, f) in walk(user_dir+'eye_stream/'):
        for file in f:
            curr_stream_id = file.split('_')[0]
            if curr_stream_id[0] == 'c':
                calibration_matrix.calc_calibration_values(user_dir, file)
            else:
                patient_ids.append(curr_stream_id)
                eye_stream_files[curr_stream_id] = file

    # # # Analyze eye streams # # #
    for pat_id in patient_ids:
        curr_pixelmap_file = open(user_dir+'pixelmaps/'+'pat_'+pat_id + '.txt', 'r')  # open file
        pixelmap_times = []  # interaction wide
        pixelmap_items = []  # interaction wide
        for line in curr_pixelmap_file:
            if line == '#refresh\n':  # new interaction
                continue
            elif line[:5] == '#end:':  # end of interaction
                interaction_end_time = float(line[5:].rstrip())
                pixelmap_times.append(interaction_end_time)
            elif line[0:3] == '>>>':
                pixelmap_times.append(float(line[3:]))
            else:
                pixelmap_item_builder = {}  # pixelmap wide
                split_line = line.rstrip().split(',')
                for i in range(0, len(split_line), 5):
                    pixelmap_item_builder[split_line[i]] = [int(x) for x in split_line[i+1:i+5]]
                pixelmap_items.append(pixelmap_item_builder)

        # insure pixelmap file was formatted properly with a single interaction and one pixelmap per timestamp
        if len(pixelmap_times) != (len(pixelmap_items) + 1):  # plus one because of end of interaction time
            print ("*** Warning, inconsistent pixelmap file. The interaction stream for " + pat_id + " was skipped! ***")
            continue

        curr_pixelmap_file.close()

        start_time = 0
        end_time = 0
        count = 0
        for i in range(len(pixelmap_times)):
            if len(pixelmap_items[i]) == 1:
                if count == 0:
                    start_time = pixelmap_times[i]
                else:
                    end_time = pixelmap_times[i]
                    break
            else:
                count += 1

        print (str(pat_id)+',' + str(count) + ',' + str(round((end_time-start_time)/60, 2)))
    return


def dispersion_call(points, dispersion_t, duration_t, curr_pixelmap):
    """
    Is the modified I-DT algorithm.
    """
    # points are [[x,y], [x,y], ...]
    # window is [top,left,bottom,right]
    def window_under_threshold(w):
        if w[2] - w[0] <= dispersion_t and w[3] - w[1] <= dispersion_t:
            return True
        else:
            return False

    def window_center(w):
        return [w[0]+(w[2]-w[0])/2, w[1]+(w[3]-w[1])/2]

    fixations = []
    fixation_counts = []
    dropped_counts = []  # used for testing
    total_num_points = len(points)  # used for testing
    window = 0
    count = 0
    while True:
        curr = points.pop()
        if window == 0:  # first point
            window = [curr[1], curr[0], curr[1], curr[0]]
            count = 1
        else:
            temp_window = [min(curr[1], window[0]), min(curr[0], window[1]),
                           max(curr[1], window[2]), max(curr[0], window[3])]
            if window_under_threshold(temp_window):
                window = temp_window
                count += 1
            else:
                if count > duration_t:
                    fixations.append(window_center(window))
                    fixation_counts.append(count)
                else:
                    dropped_counts.append(count)
                window = [curr[1], curr[0], curr[1], curr[0]]
                count = 1

        if not len(points):
            if count > duration_t:
                fixations.append(window_center(window))
                fixation_counts.append(count)
            else:
                dropped_counts.append(count)
            break
    assert (sum(fixation_counts) + sum(dropped_counts)) == total_num_points

    mapped_fixations = []
    for i in range(len(fixations)):
        fixation = fixations[i]
        fixation_mapped = False
        for name, pos in curr_pixelmap.iteritems():
            if pos[0] < fixation[1] < pos[2] and pos[1] < fixation[0] < pos[3]:  # t<y<x & l<x<r
                if fixation_mapped:
                    print ("***This fixation was mapped twice***")
                mapped_fixations.append([name, str(fixation_counts[i]), '1'])
                fixation_mapped = True
        if not fixation_mapped:
            for name, pos in curr_pixelmap.iteritems():
                if pos[0]-10 < fixation[1] < pos[2]+10 and pos[1]-10 < fixation[0] < pos[3]+10:  # t<y<x & l<x<r
                    if fixation_mapped:
                        print ("***This fixation was mapped twice in second run***")
                    mapped_fixations.append([name, str(fixation_counts[i]), '0'])
                    fixation_mapped = True

    return mapped_fixations


def aoi_call(points, duration_t, curr_pixelmap):
    """
    Is the modified I-AOI algorithm.
    """
    # points are [[x,y], [x,y], ...]
    # window is [top,left,bottom,right]
    def find_overlap(point):
        for name, pos in curr_pixelmap.iteritems():
            if pos[0] < point[1] < pos[2] and pos[1] < point[0] < pos[3]:  # t<y<x & l<x<r
                return name
        return False

    def overlap_item(point, name):
        if name in curr_pixelmap.keys():
            pos = curr_pixelmap[name]
            if pos[0] < point[1] < pos[2] and pos[1] < point[0] < pos[3]:  # t<y<x & l<x<r
                return True
        return False

    fixations = []
    fixation_counts = []
    dropped_count = 0  # used for testing
    total_num_points = len(points)  # used for testing
    curr_fixation = False
    count = 0
    while True:
        curr = points.pop()
        if not curr_fixation:
            curr_overlap = find_overlap(curr)
            if curr_overlap:
                curr_fixation = curr_overlap
                count += 1
            else:
                dropped_count += 1
        else:
            if overlap_item(curr, curr_fixation):
                count += 1
            else:
                if count > duration_t:
                    fixations.append(curr_fixation)
                    fixation_counts.append(count)
                else:
                    dropped_count += count
                curr_overlap = find_overlap(curr)
                if curr_overlap:
                    curr_fixation = curr_overlap
                    count = 1
                else:
                    curr_fixation = False
                    count = 0
                    dropped_count += 1

        if not len(points):
            if count > duration_t:
                fixations.append(curr_fixation)
                fixation_counts.append(count)
            else:
                dropped_count += count
            break

    assert (sum(fixation_counts) + dropped_count) == total_num_points

    mapped_fixations = []
    for i in range(len(fixations)):
        mapped_fixations.append([fixations[i], str(fixation_counts[i]), '1'])

    return mapped_fixations


def dispersion(user_dir, use_dispersion_call, duration_t, dispersion_t):
    """
    Code used when testing one of the fixation based algorithms
    use_dispersion_call is a selection between dispersion (I-DT) and area of interest (I-AOI)
    """
    interaction_files = []
    # # # Identify interactions in directory and calculate calibration matrix # # #
    patient_ids = []  # holds strings of each patient id in directory
    eye_stream_files = {}  # holds the filename of each eye_scream_file in directory
    calibration_matrix = Matrix()  # the nine-point calibration matrix
    for (p, d, f) in walk(user_dir + 'eye_stream/'):
        for file in f:
            curr_stream_id = file.split('_')[0]
            if curr_stream_id[0] == 'c':
                calibration_matrix.calc_calibration_values(user_dir, file)
            else:
                patient_ids.append(curr_stream_id)
                eye_stream_files[curr_stream_id] = file

    # # # Analyze eye streams # # #
    for pat_id in patient_ids:
        curr_pixelmap_file = open(user_dir + 'pixelmaps/' + 'pat_' + pat_id + '.txt', 'r')  # open file
        pixelmap_times = []  # interaction wide
        pixelmap_items = []  # interaction wide
        for line in curr_pixelmap_file:
            if line == '#refresh\n':  # new interaction
                continue
            elif line[:5] == '#end:':  # end of interaction
                interaction_end_time = float(line[5:].rstrip())
                pixelmap_times.append(interaction_end_time)
            elif line[0:3] == '>>>':
                pixelmap_times.append(float(line[3:]))
            else:
                pixelmap_item_builder = {}  # pixelmap wide
                split_line = line.rstrip().split(',')
                for i in range(0, len(split_line), 5):
                    pixelmap_item_builder[split_line[i]] = [int(x) for x in split_line[i + 1:i + 5]]
                pixelmap_items.append(pixelmap_item_builder)
        curr_pixelmap_file.close()

        # insure pixelmap file was formatted properly with a single interaction and one pixelmap per timestamp
        if len(pixelmap_times) != (len(pixelmap_items) + 1):  # plus one because of end of interaction time
            print ("*** Warning, inconsistent pixelmap file. The interaction stream for " + pat_id + " was skipped! ***")
            continue

        # # # Calculate interaction stream # # #
        eye_stream_file = open(user_dir + 'eye_stream/' + eye_stream_files[pat_id], 'r')  # open eye stream file
        interaction_files.append('interaction_stream/'+pat_id+'_'+str(pixelmap_times[0]) +
                                 '-'+str(pixelmap_times[-1])+'.txt')
        interaction_stream_file = open(user_dir+interaction_files[-1], 'w+')  # generate interaction stream file
        interaction_stream_file.write('#itemname|point_count|directly_in_item\n')

        pixelmap_progress = 0
        curr_points = []
        for line in eye_stream_file:
            x, y, time = [float(x) for x in line.rstrip().split(',')]

            if time < pixelmap_times[pixelmap_progress]:  # tracking before interaction started
                continue
            elif time > pixelmap_times[pixelmap_progress + 1]:  # time past current pixelmap
                pixelmap_progress += 1
                if pixelmap_progress == len(pixelmap_items):  # move to next pixelmap
                    break
                else:
                    if len(curr_points) > duration_t-1:
                        if use_dispersion_call:
                            mappings = dispersion_call(curr_points, dispersion_t, duration_t,
                                                       pixelmap_items[pixelmap_progress])
                        else:
                            mappings = aoi_call(curr_points, duration_t, pixelmap_items[pixelmap_progress])
                        for map in mappings:
                            interaction_stream_file.write('|'.join(map)+'\n')
                    curr_points = []
            else:
                if x == 0.0 or y == 0.0:  # eyes were off screen
                    continue
                else:  # time for mapping
                    x, y = calibration_matrix.get_fixed_display_point(x * 1920, y * 1080)
                    curr_points.append([x, y])

        eye_stream_file.close()
        interaction_stream_file.close()

        # # # Summarize interaction # # #
        if use_dispersion_call:
            summary_out = open(user_dir + '/summary_dispersion_'+str(duration_t)+'_'+str(dispersion_t)+'.txt', 'w+')
            summary_out.write('#name|ratio_of_count|point_count|fixation_count\n')
        else:
            summary_out = open(user_dir + '/summary_aoi_'+str(duration_t)+'.txt', 'w+')
            summary_out.write('#name|ratio_of_count|point_count|fixation_count\n')
        for interaction_file_name in interaction_files:
            item_name_counts = {}
            all_item_counts = 0.0
            interaction_in_file = open(user_dir + interaction_file_name, 'r')
            for line in interaction_in_file:
                if line[0] == '#':
                    continue  # skip header comment
                split_line = line.split('|')
                if split_line[0] not in item_name_counts.keys():
                    item_name_counts[split_line[0]] = [0, 0]
                item_name_counts[split_line[0]][0] += int(split_line[1])
                all_item_counts += int(split_line[1])
                item_name_counts[split_line[0]][1] += 1
            interaction_in_file.close()

            summary_tuples = []
            for name in item_name_counts.keys():
                curr_ratio = round(float(item_name_counts[name][0])/all_item_counts, 4)
                curr_points = item_name_counts[name][0]
                curr_fixations = item_name_counts[name][1]
                summary_tuples.append((name, curr_ratio, curr_points, curr_fixations))
            summary_tuples.sort(key=lambda d_tup: d_tup[1], reverse=True)

            summary_out.write('\n\n>>>patient_interaction|' + interaction_file_name.split('/')[1][:-4])
            for tup in summary_tuples:
                summary_out.write('\n' + tup[0] + '|' + str(tup[1]) + '|' + str(tup[2]) + '|' + str(tup[3]))

        summary_out.close()
    return



if __name__ == "__main__":
    user_dir = ['/resources/load_pixelmap_labeling_study-file']  
    for curr_user_dir in user_dir:
        for (p, d, f) in walk(curr_user_dir):
            for interaction_dir in d:
                print (interaction_dir)
                map_eye_stream(curr_user_dir + interaction_dir + '/', 'bivariate-data.txt')
            break  # break after top level directories

    sys.exit(0)
