import matplotlib.pyplot as plt
import numpy as np
import simpleaudio as sa
from datetime import datetime
import time
import pathlib
import glob
import os
import csv
import subprocess
from prompt_toolkit import prompt

def main(project_root, data_dir):
	master_dir   = '{}/MASTER_DAQ'.format(data_dir)
	slave_dir    = '{}/SLAVE_DAQ'.format(data_dir)
	# sleep and let daq collect data without tone
	print('About to sleep for 4 seconds to allow the daq to collect data without the tone')
	time.sleep(4)

	filename = 'singletone.wav'

	wave_obj = sa.WaveObject.from_wave_file(filename)

	# get start time for tone
	start_t = time.time()
	# import ipdb; ipdb.set_trace() # BREAKPOINT
	play_obj = wave_obj.play()

	# TODO confirm wav file is long enough (this one is 20 sec)
	print('About to sleep for 10 seconds to allow the daq to collect data WITH the tone')
	time.sleep(10)
	# get stop time for tone
	stop_t = time.time()

	# import ipdb; ipdb.set_trace() # BREAKPOINT
	master_files = sorted(pathlib.Path(master_dir).glob('1*.txt'))
	slave_files  = sorted(pathlib.Path(slave_dir).glob('1*.txt'))

	file_with_tone = {
		'MASTER': None,
		'SLAVE': None,
		}

	# print(master_dir)
	print('length of master files list: {}'.format(len(master_files)))
	# print(slave_dir)
	print('length of slave files list: {}'.format(len(slave_files)))
	# find file closest to start of tone ---------> MASTER
	for file in master_files:
		# print(file.name)
		# print(start_t)
		if str(file.name) <= str(start_t):
			file_with_tone['MASTER'] = file
		else:
			break

	# find file closest to start of tone ---------> SLAVE
	for file in slave_files:
		# print(file.name)
		# print(start_t)
		if str(file.name) <= str(start_t):
			file_with_tone['SLAVE'] = file
		else:
			break

	try:
		t_start_slave = float(file_with_tone['SLAVE'].stem)
		t_start_master = float(file_with_tone['MASTER'].stem)
	except Exception as e:
		import ipdb; ipdb.set_trace() # BREAKPOINT

	master = []
	slave = []

	with open(file_with_tone['MASTER']) as csvfile:
		master = [float(x[0]) for x in csv.reader(csvfile)]

	with open(file_with_tone['SLAVE']) as csvfile:
		slave = [float(x[0]) for x in csv.reader(csvfile)]

	time_vector_m = np.linspace(0.0, 1.0, len(master))
	time_vector_s = np.linspace(0.0, 1.0, len(slave))

	plt.plot(time_vector_m, master, 'r')
	# plt.plot((time_vector_s+t_start_slave-t_start_master), slave, 'b')
	plt.plot(time_vector_s, slave, 'b')
	plt.show()


if __name__ == '__main__':
	project_root = pathlib.Path(os.getcwd())
	project_root = project_root.parent

	data_dir     = '{}/data'.format(str(project_root))

	try:
		prompt('Hit enter when the test leads are connected to the payload box and the DAQs are running.')
		main(project_root, data_dir)
	finally:
		print('Leaving test!\n')


