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
#from basicft8 import *
from socket import * 
import pskreport
import re

def decoder(wav_file) :
#	print("WAV file %s" % wav_file)
	"""
	r = FT8()
	p = r.gowav(wav_file, 0)
	"""
	p = subprocess.check_output(["jt9","-8","-d","3","-t","/dev/shm/","-a","/dev/shm/",wav_file])

#	print("%s" % p.decode('utf-8').split("\n"))
	if p != 0 :
		udp_send(p)
		psk_send(p)
		subprocess.call(['rm','-f',wav_file])
#	os.remove(wav_file)

def udp_send(result) :
	global nmSocket, ip_port
	nmSocket.sendto('Start Decode 14074000-FT8-Raspberry159'.encode('utf-8'),ip_port)   #send Identification of this decoder
	iq = open('/dev/shm/ft8.txt', "a")            #log write to a file for debug or other program use.
	for line in result.decode("utf-8").split("\n") :
		try:
			detail=line.split()
			a = int(detail[0])
			adif = ''
			print("+++++ %s" % line)
			iq.write(line + '\n')
			nmSocket.sendto(line.encode('utf-8'),ip_port)      #send to my udp2telnet server
		except :
			a = 0      #nothing
#			print("----- %s" % line)
	iq.close()
	nmSocket.sendto('End Decode FT8-Raspberry159'.encode('utf-8'),ip_port)     #nothing only for Identification of this decoder

def iscall(call):
	if len(call) < 3:
		return False
	if re.search(r'[0-9][A-Z]', call) == None:
		# no digit
		return False
	#if self.sender.packcall(call) == -1:
		# don't know how to encode this call, e.g. R870T
	#	return False
	return True
		
def psk_send(result) :
	global pskr
	for line in result.decode("utf-8").split("\n") :
		detail=line.split()
		#try:
		if len(detail) > 5 :
#			print("line %s" % detail)
			txt = line[24:60]
			hz = int(line[16:20].strip()) + int(14074000.0)
			tm = int(datetime.datetime.now().strftime('%s'))

			txt = txt.strip()
			txt = re.sub(r'  *', ' ', txt)
			txt = re.sub(r'CQ DX ', 'CQ ', txt)
			txt = re.sub(r'CQDX ', 'CQ ', txt)
			mm = re.search(r'^CQ ([0-9A-Z/]+) ([A-R][A-R][0-9][0-9])$', txt)

			if mm != None and iscall(mm.group(1)):
				if pskr != None:
#					print("pskr {}, {}, {}, {}, {}\n".format(mm.group(1), hz, "FT8", mm.group(2), tm))
					pskr.got(mm.group(1), hz, "FT8", mm.group(2), tm)
			mm = re.search(r'^([0-9A-Z/]+) ([0-9A-Z/]+) ([A-R][A-R][0-9][0-9])$', txt)
			if mm != None and iscall(mm.group(1)) and iscall(mm.group(2)):
				if pskr != None:
#					print("pskr {} {}, {}, {}, {}, {}\n".format(mm.group(1),mm.group(2), hz, "FT8", mm.group(3), tm))
					pskr.got(mm.group(2), hz, "FT8", mm.group(3), tm)
		#except Exception as e:
		#	print("psk send error %s" % e)
	
	
def main():
	global nmSocket, ip_port, pskr
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

	nmSocket = socket(AF_INET,SOCK_DGRAM)
	ip_port = (gethostbyname('192.168.1.1'), 5556)    #send udp to my udp2telnet server
	
	pskr = pskreport.T("callsign", "aa11", "ft8-decoder", testing=False)    #send udp to pskreporter.info
	
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
	nmSocket.close()

if __name__ == '__main__':
	main()
