#!/usr/bin/env python3
#
# Script to split stream from stdin into files with x seconds of data 
# 

import datetime
import getopt
import sys
#import time
import threading
import uuid
import wave
#import os
import subprocess
from socket import * 

#from basicft8 import *

def decoder(wav_file) :
#	print("WAV file %s" % wav_file)
	"""
	r = FT8()
	p = r.gowav(wav_file, 0)
	"""
	p = subprocess.check_output(["jt9","-8","-d","3",wav_file])

#	print("%s" % p.decode('utf-8').split("\n"))
	if p != 0 :
		nmSocket = socket(AF_INET,SOCK_DGRAM)
		ip_port = (gethostbyname('192.168.103.1'), 5556)
		nmSocket.sendto('Start Decode FT8-Raspberry-159'.encode('utf-8'),ip_port)
		iq = open('/dev/shm/ft8.txt', "a")
		for line in p.decode("utf-8").split("\n") :
			try:
				detail=line.split(' ')
				a = int(detail[0])
				adif = ''
				print("+++++ %s" % line)
				iq.write(line + '\n')
				nmSocket.sendto(line.encode('utf-8'),ip_port)
			except :
				print("----- %s" % line)
		iq.close()
		nmSocket.sendto('End Decode FT8-Raspberry-159'.encode('utf-8'),ip_port)
		nmSocket.close()
		subprocess.call(['rm','-f',wav_file])
#	os.remove(wav_file)

	
def main():
	verbose = False
	nametag = ''
	tmp_path = '/dev/shm'

	print("ARGV:", sys.argv[1:])
	options, remainder = getopt.getopt(sys.argv[1:], 't:v', ['output=', 'verbose',])

	for opt, arg in options:
		if opt in ('-t', '--tag'):
			nametag = '-' + arg
		elif opt in ('-v', '--verbose'):
			verbose = True

	blocktime = 15
	blocktimeoffset = datetime.timedelta(milliseconds=200)
	samplerate = 12000
	chunksize = 32768


	block = bytearray(0)
	time1 = int(int(datetime.datetime.now().strftime('%s')) / blocktime) * blocktime
	starttime = datetime.datetime.fromtimestamp(time1)
	endtime = datetime.datetime.fromtimestamp(time1+15)
	print(starttime, endtime)

	first=True

	while True:
		data = sys.stdin.buffer.read(chunksize)
		block.extend(data)

		if datetime.datetime.now() > endtime:
			print("Buffersize", len(block))
			fname = tmp_path + "/file"+nametag+"-"+starttime.strftime("%Y%m%d%H%M%S")+".wav"

			if not first:
				print("Writing: ",fname)
				"""
				iq = open(fname, "wb")
				iq.write(block)
				iq.close()
				"""
				wf =  wave.open(fname, "wb")
				wf.setnchannels(1)
				wf.setsampwidth(2)
				wf.setframerate(samplerate)
				wf.writeframes(block)
				wf.close()
				t = threading.Thread(target=decoder,args=(fname,), name=uuid.uuid1())
				t.start()
			else:
				print("Unfilled block. Ditching data")
				first=False
				
			time1 = int(int(datetime.datetime.now().strftime('%s')) / blocktime) * blocktime
			starttime = datetime.datetime.fromtimestamp(time1)
			endtime = datetime.datetime.fromtimestamp(time1+15)
			block = bytearray(0)

if __name__ == '__main__':
	main()
