"""
eyeanalysis.py
package eyebrowserpy 
version 2.0
created by AndrewJKing.com|@andrewsjourney

This code maps and analyzes the output from eyebrowser.js and eyebrowser.py.
It uses timestamps to map the two fields together.
An area of interest (I-AOT) algorithm is used. The other option is dispersion (I-DT). 
The mapping results in an interaction stream file. This file is then analysed to summarize the eye interaction. 

TODO:
Determine format for generalizing this approach.

"""

import time
import sys
import os.path
from os import walk
import numpy as np
import pickle

t = False
 
if os.path.isdir("../../models/"):   # set this to your output directory
    local_dir = os.getcwd() + "/../../models/"

out_file = None


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
            print '***caught def overlap IndexError ' + str(pos) + '***'
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


class calibration_matrix:
    """
    Calibration class
    """
    # ## Matrix used for calibration
    def __init__(self, curr_directory):
        self.An = 1.0
        self.Bn = 1.0
        self.Cn = 0.0
        self.Dn = 1.0
        self.En = 1.0
        self.Fn = 0.0

        self.es_dir = False
        self.clean_calibration = True  # changed to false if any of the calibration boxes throw a warning 
        self.directory = curr_directory
        self.run = curr_directory.split('/')[-3]
        return

    def __str__(self):
        return "Matrix: [" + str(self.An) + ', ' + str(self.Bn) + ', ' + str(self.Cn) + ', '\
               + str(self.Dn) + ', ' + str(self.En) + ', ' + str(self.Fn) + '] Clean Calibration: ' + str(self.clean_calibration)

    def calc_calibration_values(self, eye_streams):
        # load calibration pixelmap file to data structure
        box_start_times = []
        box_x_centers = []
        box_y_centers = []
        box_end_times = []
        cal_pixelmap_file = open(self.directory, 'r')
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

        # ## find appropriate stream file
        for eye_stream in eye_streams:
            if eye_stream.start_time < box_start_times[0] and box_end_times[-1] < eye_stream.end_time:
                self.es_dir = eye_stream.directory
      
        if not self.es_dir:
            print "no eye_stream in time range"
        else:
            # ## loop thorugh eye stream line by line
            es_file = open(self.es_dir, 'r')
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
                        # print "***WARNING this calibration box might not have worked: " + str(current_box) + " ***"
                        self.clean_calibration = False
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
                print '***caught def calc_calibration_values LinAlgError***'
                self.clean_calibration = False  # This exception should not occur, but calibration box warnings are common

        return

    def get_fixed_display_point(self, x, y):
        new_x = ((self.An * x) + (self.Bn * y) + self.Cn)
        new_y = ((self.Dn * x) + (self.En * y) + self.Fn)
        return int(round(new_x)), int(round(new_y))


class eye_stream:
    """
    This class stores all the data from an eye stream file
    """
    def __init__(self, stream_directory, is_calibration):
        self.is_calibration = is_calibration
        self.directory = stream_directory
        interaction_id, start_time = stream_directory.rstrip('.txt').split('/')[-1].split('_')
        self.interaction_id = interaction_id
        self.start_time = float(start_time)
        with open(stream_directory, 'r') as myfile:
            all_lines = myfile.readlines()
            self.end_time = float(all_lines[-1].rstrip().split(',')[2])
        return


class pixelmap:
    """
    This class stores a instance of a pixelmap (the location of onscreen objects for a particular period of time). One or more pixelmaps for a sub_interaction. 
    """
    def __init__(self, stime, pixelmap, etime):
        self.start_time = stime
        self.end_time = etime
        self.items = pixelmap
        return

    def duration(self):
        return self.end_time - self.start_time

class sub_interaction:
    """
    This class stores a series of pixelmaps that make up a particular task. Multiple sub_interactions make up a full interaction. 
    """
    def __init__(self, ptimes, pitems, type_idx):
        self.pixelmaps = []
        self.sub_interaction_duration = 0
        self.type_idx = type_idx
        self.items_present = []
        self.item_gaze_weights = {}
        self.item_gaze_weights_cal = {}
        if len(ptimes):
            self.has_data = True
            self.sub_interaction_start_time = ptimes[0]
            self.sub_interaction_start_time = ptimes[-1]
        else:
            self.has_data = False
            self.sub_interaction_start_time = 0
            self.sub_interaction_start_time = 0
        
        # ## create each pixelmap
        for i in range(len(pitems)):
            self.pixelmaps.append(pixelmap(ptimes[i], pitems[i], ptimes[i+1]))
            self.sub_interaction_duration += self.pixelmaps[-1].duration()
            # ## fill items present
            for pitem in pitems[i]:
                if pitem not in self.items_present:
                    self.items_present.append(pitem)

    def get_duration(self):
        return self.sub_interaction_duration

class interaction:
    """
    This class stores a series of sub_interactions.
    """
    def __init__(self, interaction_directory):
        self.directory = interaction_directory
        self.run = interaction_directory.split('/')[-3]
        self.interaction_id = interaction_directory.rstrip('.txt').split('_')[-1]
        self.sub_interactions = []  
        self.calibration_matrix = None
        self.eye_streams = []
        self.load_pixelmap_index = 0
        self.med_mappings = {}
        with open(interaction_directory, 'r') as f:
            for line in f:
                if line[0:3] == '>>>':
                    pixelmap_start_time = float(line.rstrip().lstrip('>>>'))
                    break
                else:
                    continue
        # ## use study specific load_pixelmap_ mehtods
        if pixelmap_start_time < 1514782800:  # subject from before 2018 --> labeling study
            self.load_pixelmap_index = 1
            self.med_mappings = self.load_interaction_meds_mapping('D:/models/labeling_study/cases_t2/'+str(self.interaction_id))
            ptimes_list, pitems_list = load_pixelmap_labeling_study(interaction_directory, self.med_mappings)
            for i in range(3):
                self.sub_interactions.append(sub_interaction(ptimes_list[i], pitems_list[i], i))
        else:
            self.load_pixelmap_index = 2
            self.med_mappings = self.load_interaction_meds_mapping('C:/Users/ajk77/Bitnami Django Stack projects/models/evaluation_study/cases_t2/'+str(self.interaction_id))
            ptimes_list, pitems_list = load_pixelmaps_evaluation_study(interaction_directory, self.med_mappings)
            for i in range(7):
                self.sub_interactions.append(sub_interaction(ptimes_list[i], pitems_list[i], i))

        return

    def set_calibration_matrix(self, curr_matrices):
        for curr_matrix in curr_matrices:
            if curr_matrix.run == self.run:
                self.calibration_matrix = curr_matrix
        return

    def load_interaction_meds_mapping(self, experiment_case_dir):
        mappings = {}
        with open(experiment_case_dir+'/med-display-id_to_name.txt', 'r') as f:
            for full_line in f:
                line = full_line.rstrip()
                if line:
                    split_line = line.split('\t')
                    mappings[split_line[0]] = split_line[1]
        return mappings

    
    def get_durations_str(self):
        durations_str = ''
        for i in range(len(self.sub_interactions)):
            durations_str += str(round(self.sub_interactions[i].get_duration(), 3)) + '|' 
        return durations_str.rstrip('|')

    def get_durations_arr(self):
        durations_arr = []
        for i in range(len(self.sub_interactions)):
            durations_arr.append(round(self.sub_interactions[i].get_duration(), 3))
        return durations_arr

    def get_interaction_start_time(self):
        try:
            start_time = self.sub_interactions[0].pixelmaps[0].start_time
        except (AttributeError, IndexError):
            print 'W: ', self.interaction_id, len(self.sub_interactions)
            start_time = 0

        return start_time

    def map_eye_stream(self, eye_streams):
        # ## find appropriate stream file
        for eye_stream in eye_streams:
            if eye_stream.interaction_id == self.interaction_id:
                self.eye_streams.append(eye_stream)

        # ## load distribution 
        distribution_4 = np.loadtxt('C:/Users/ajk77/Bitnami Django Stack projects/models/eye_tests/4_pixel.txt', delimiter=',')

        if not len(self.eye_streams):
            print "no eye_stream in time range"
        else:
            curr_out = self.directory
            t = 0
            print self.directory
            for sub_interaction in self.sub_interactions:
                curr_stream_dir = False
                for eye_stream in self.eye_streams:
                    curr_stream_dir = eye_stream.directory
                
                    if not curr_stream_dir:
                        print "not eye stream for sub_interaction\t", curr_out, t
                    else:
                        pixelmap_progress = 0 ####sub_interaction.pixelmaps
                        es_file = open(curr_stream_dir, 'r')
                        # process eye_stream file line by line
                        for line in es_file:
                            x, y, time = [float(x) for x in line.rstrip().split(',')]

                            if not len(sub_interaction.pixelmaps):
                                break
                            elif time < sub_interaction.pixelmaps[pixelmap_progress].start_time: # tracking before interaction started
                                continue
                            elif time >= sub_interaction.pixelmaps[pixelmap_progress].end_time: # time past current pixelmap
                                if pixelmap_progress+1 < len(sub_interaction.pixelmaps):
                                    pixelmap_progress += 1
                                else:
                                    break
                            if x == 0.0 or y == 0.0:  # eyes were off screen
                                continue
                            else:   # time for mapping
                                x = x*1920
                                y = y*1080
                                x_cal, y_cal = self.calibration_matrix.get_fixed_display_point(x, y)
                                curr_distribution = ErrorDistribution(distribution_4, x, y)
                                curr_distribution_cal = ErrorDistribution(distribution_4, x_cal, y_cal)
                            
                                for name, pos in sub_interaction.pixelmaps[pixelmap_progress].items.iteritems():
                                    if curr_distribution.overlap(pos):
                                        curr_item_weight = curr_distribution.calc_overlap(pos)
                                        if curr_item_weight > 0:  # skip when item weight was zero.
                                            if name in sub_interaction.item_gaze_weights:
                                                sub_interaction.item_gaze_weights[name] += curr_item_weight
                                            else:
                                                sub_interaction.item_gaze_weights[name] = curr_item_weight
                                    if curr_distribution_cal.overlap(pos):
                                        curr_item_weight = curr_distribution_cal.calc_overlap(pos)
                                        if curr_item_weight > 0:  # skip when item weight was zero.
                                            if name in sub_interaction.item_gaze_weights_cal:
                                                sub_interaction.item_gaze_weights_cal[name] += curr_item_weight
                                            else:
                                                sub_interaction.item_gaze_weights_cal[name] = curr_item_weight
                        es_file.close()
                    t+=1
                print '<'+str(len(sub_interaction.item_gaze_weights))+'> ', 
            print 
        return


class user:
    """
    This class stores a full user of the system. A user is made up of one or more interactions and one or more eye_streams. 
    """
    def __init__(self, user_dir):
        self.directory = user_dir
        self.user_id = user_dir.rstrip('/').split('/')[-1]
        self.interactions = []
        self.calibration_matrices = []
        self.eye_streams = []
        self.calibration_eye_streams = []
        self.time_of_initial_interaction = -1
        self.time_of_final_interaction = -1

    def add_run(self, run_directory):
        # ## first load eye_streams
        if True:  # testing skip
            for (p, d, f) in walk(self.directory + run_directory + '/eye_stream/'):
                for current_file in f:
                    if current_file[0:11] == 'calibration':
                        self.calibration_eye_streams.append(eye_stream(p+current_file, True))
                    else:
                        self.eye_streams.append(eye_stream(p+current_file, False))
        
        # ## next load pixelmaps
        if True:  # testing skip
            for (p, d, f) in walk(self.directory + run_directory + '/pixelmaps/'):
                for current_file in f:
                    if current_file[-15:] == 'calibration.txt':
                        curr_calibration_matrix = calibration_matrix(p+current_file)
                        curr_calibration_matrix.calc_calibration_values(self.calibration_eye_streams)
                        self.calibration_matrices.append(curr_calibration_matrix)
                    else:
                        self.interactions.append(interaction(p+current_file))

        # ## set calibration matrix for each interaction
        for curr_interaction in self.interactions:
            curr_interaction.set_calibration_matrix(self.calibration_matrices)
        return

    def run_mapping(self):
        print '_________', self.user_id, '_________________'
        for curr_interaction in self.interactions:
            curr_interaction.map_eye_stream(self.eye_streams)
        return

    def get_interaction_ids(self):
        return [interaction.interaction_id for interaction in self.interactions]

    def get_interaction_start_times(self):
        return [interaction.get_interaction_start_time() for interaction in self.interactions]
                        


def load_pixelmaps_evaluation_study(curr_dir, med_mappings):
    def test_for_consistency(ptimes, pitems):
        for i in range(7):
            if len(ptimes[i]):
                try:
                    assert (len(ptimes[i])-1 == len(pitems[i]))  # times include an end time so it has one additional value
                except AssertionError:
                    pitems[i] = pitems[i][0:-1]
            else:
                assert (len(pitems[i]) == 0)
        return

    try:
        incomplete_patient = True
        curr_pixelmap_file = open(curr_dir, 'r')  # open file
        pixelmap_times = [[], [], [], [], [], [], []]  # [[task A], [B], [C], [D], [E], [F], [G]]
        pixelmap_items = [[], [], [], [], [], [], []]  # interaction wide
        # ## tasks: A=familiar, B=prepare, C=present, D=complexity, E=select, F,=revise, G=impact
        curr_timestamp = 0
        i = 0  # 0 = task A, 1 = task B, ...
        last_line = ''
        curr_line = ''
        line_number = 0
        for line in curr_pixelmap_file:
            curr_line = line
            line_number += 1
            #print line_number
            #line_number += 1
            if line == '#refresh\n':  # new stage
                continue
            elif line[:5] == "Pause":  # PausedScreen
                continue
            elif line[:5] == "loadi":  # PausedScreen
                continue
            elif not line.rstrip():
                continue
            elif line[:5] == '#end:':  # end of stage
                interaction_end_time = float(line[5:].rstrip())
                pixelmap_times[i].append(interaction_end_time)
                if i == 0:
                    i = 1  # advance to first view
                else:
                    break
            elif line[0:3] == '>>>':
                curr_timestamp = float(line[3:])
            elif line[:5] == "Round":  # RoundingReport
                #if line.index('>>>'):

                pixelmap_times[i].append(curr_timestamp)  # end old interaction
                i = 2
                pixelmap_times[i].append(curr_timestamp)  # start new interaction
                pixelmap_items[i].append(pixelmap_items[i - 1][-1])  # start new interaction with last screen positions
            elif line[:5] == "Compl":  # ComplexityRating
                pixelmap_times[i].append(curr_timestamp)
                i = 3
                pixelmap_times[i].append(curr_timestamp)
                pixelmap_items[i].append(pixelmap_items[i - 1][-1])
            elif line[:5] == "Selec":  # SelectionScreen
                pixelmap_times[i].append(curr_timestamp)
                i = 4
                pixelmap_times[i].append(curr_timestamp)
                pixelmap_items[i].append(pixelmap_items[i - 1][-1])
            elif line[:5] == "Revis":  # ReviseReport
                pixelmap_times[i].append(curr_timestamp)
                i = 5
                # revise report will always have a SecondView line at the start
                # ^so there is no need to append an initial timestamp and pixelmap here
            elif line[:5] == "Clini":  # ClinicalImpact
                pixelmap_times[i].append(curr_timestamp)
                i = 6
                pixelmap_times[i].append(curr_timestamp)
                pixelmap_items[i].append(pixelmap_items[i - 1][-1])
            elif line[:5] == 'First' or line[:5] == 'Secon':
                if ('>') in line:  # crossed lines
                    line = line[0:line.index('>')]  # only keep first part of line

                pixelmap_item_builder = {}  # pixelmap wide
                split_line = line.rstrip().split(',')[5:]  # skip the descriptor item
                for q in range(0, len(split_line), 5):
                    #print line
                    try:
                        if split_line[q] in med_mappings:
                            split_line[q] = med_mappings[split_line[q]]
                        pixelmap_item_builder[split_line[q]] = [int(x) for x in split_line[q+1:q+5]]
                    except ValueError:
                        break
                pixelmap_times[i].append(curr_timestamp)
                if len(pixelmap_item_builder):
                    pixelmap_items[i].append(pixelmap_item_builder)
                    incomplete_patient = False
                else:
                    print 'b', last_line, line, 'b'
            else:
                pass
                # some pixelmap information will be lost here if it were not all printed to a single line

            last_line = line


    except (IndexError, ValueError):
        print last_line, curr_line
        print '***Caught IndexError. Likely from an unauthorized reload***'

    if incomplete_patient:
        # print 'skipping\t', [len(x) for x in pixelmap_times], [len(x) for x in pixelmap_items]
        pass
    else:
        # print [len(x) for x in pixelmap_times], [len(x) for x in pixelmap_items]
        test_for_consistency(pixelmap_times, pixelmap_items)
    
    return [pixelmap_times, pixelmap_items]


def load_pixelmap_labeling_study(curr_dir, med_mappings):
    def test_for_consistency(ptimes, pitems):
        for i in range(3):
            if len(ptimes[i]):
                try:
                    assert (len(ptimes[i])-1 == len(pitems[i]))  # times include an end time so it has one additional value
                except AssertionError:
                    pitems[i] = pitems[i][0:-1]
            else:
                assert (len(pitems[i]) == 0)
        return

    try:
        incomplete_patient = True
        curr_pixelmap_file = open(curr_dir, 'r')  # open file
        pixelmap_times = [[], [], []]  # [[stage 1], [stage 2], [selection screen]]
        pixelmap_items = [[], [], []]  # interaction wide
        curr_timestamp = 0
        i = 0  # 0 = stage 1, 1 = stage 2, 2 = selection screen
        last_line = ''
        curr_line = ''
        line_number = 0
        for line in curr_pixelmap_file:
            if line == '#refresh\n':  # new interaction
                continue
            elif line[:5] == '#end:':  # end of interaction
                interaction_end_time = float(line[5:].rstrip())
                pixelmap_times[2].append(interaction_end_time)
            elif line[0:3] == '>>>':
                curr_timestamp = float(line[3:])
            else:
                pixelmap_item_builder = {}  # pixelmap wide
                split_line = line.rstrip().split(',')
                if split_line[0] == 'PausedScreen':
                    continue
                elif i == 0:
                    if split_line[0] != 'FirstView':  # handle first second view
                        pixelmap_times[0].append(curr_timestamp)  # close stage 1
                        i = 1  # advance to stage 2
                    else:
                        split_line = split_line[5:]  # skip the first view item
                elif i == 1 and split_line[0] == 'SelectionScreen':
                    pixelmap_times[1].append(curr_timestamp)  # close stage 2
                    i=2
            
                for q in range(0, len(split_line), 5):
                    try:
                        if split_line[q] in med_mappings:
                            split_line[q] = med_mappings[split_line[q]]
                        pixelmap_item_builder[split_line[q]] = [int(x) for x in split_line[q+1:q+5]]
                    except ValueError:
                        break
                if len(pixelmap_item_builder):
                    incomplete_patient = False
                pixelmap_items[i].append(pixelmap_item_builder)
                pixelmap_times[i].append(curr_timestamp)
    except IndexError:
        print '***Caught IndexError. Likely from an unauthorized reload***'

    if incomplete_patient:
        #print 'skipping\t', [len(x) for x in pixelmap_times], [len(x) for x in pixelmap_items]
        pass
    else:
        #print 'training: ', [len(x) for x in pixelmap_times], [len(x) for x in pixelmap_items]
        test_for_consistency(pixelmap_times, pixelmap_items)

    return [pixelmap_times, pixelmap_items]


def print_times_to_file(users, print_times_file):
    # user_id, case_id, task1 time, task2 time, task3 time, ...
    with open(print_times_file, 'w') as out_file:
        for curr_user in users:
            for curr_interaction in curr_user.interactions:
                out_file.write(curr_user.user_id + ',' + curr_interaction.interaction_id + ',' + ','.join([str(x) for x in curr_interaction.get_durations_arr()]) + '\n') 


def print_mappings_to_file(users, print_mappings_file, sorted_uil_keys):
    # sorted_uil_keys = sorted universal item list keys
    # item, [user id, case id, task2 weights...]
    with open(print_mappings_file, 'w') as out_file:
        out_file.write('curr_user.user_id,curr_interaction.interaction_id,' + ','.join(sorted_uil_keys)+'\n')
        for curr_user in users:
            for curr_interaction in curr_user.interactions:
                if len(curr_interaction.sub_interactions[1].item_gaze_weights):
                    # ## output gaze weights to a file
                    out_file.write(curr_user.user_id + ',' + curr_interaction.interaction_id)
                    for key in sorted_uil_keys:
                        if key in curr_interaction.sub_interactions[1].item_gaze_weights:
                            out_file.write(','+str(curr_interaction.sub_interactions[1].item_gaze_weights[key]))
                        else:
                            out_file.write(','+str(0.0))
                    out_file.write('\n')
                else:
                    print 'no sub interaction items for ', curr_user.user_id, curr_interaction.interaction_id


def print_items_present_to_file(users, print_items_file, sorted_uil_keys):
    # sorted_uil_keys = sorted universal item list keys
    # item, [user id, case id, task2 weights...]
    with open(print_items_file, 'w') as out_file:
        out_file.write('curr_user.user_id,curr_interaction.interaction_id,' + ','.join(sorted_uil_keys)+'\n')
        for curr_user in users:
            for curr_interaction in curr_user.interactions:
                if len(curr_interaction.sub_interactions[1].items_present):
                    # ## output gaze weights to a file
                    out_file.write(curr_user.user_id + ',' + curr_interaction.interaction_id)
                    for key in sorted_uil_keys:
                        if key in curr_interaction.sub_interactions[1].items_present or key in curr_interaction.sub_interactions[0].items_present:
                            out_file.write(',1')
                        else:
                            out_file.write(',0')
                    out_file.write('\n')
                else:
                    print 'no items present for ', curr_user.user_id, curr_interaction.interaction_id


def add_to_universal_item_list(users, uil):
    # uil = universal_item_list
    for curr_user in users:
        for curr_interaction in curr_user.interactions:
            if len(curr_interaction.sub_interactions[1].item_gaze_weights):                
                # ## store all unique keys
                for key in curr_interaction.sub_interactions[1].item_gaze_weights:
                    if key not in uil:
                        uil[key] = 0
                    uil[key] += curr_interaction.sub_interactions[1].item_gaze_weights[key]
    return uil

