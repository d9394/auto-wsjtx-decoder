#!/usr/bin/env python3
#
# Script to split stream from stdin into files with x seconds of data 
# 

import datetime
import time
import getopt
import sys
#import time
import threading
#import uuid
import wave
#import os
import subprocess
#from basicft8 import *
from socket import * 
import pskreport
import re

def decoder(wav_file) :
	space="-\\|/"[int(int(wav_file[-6:-4])/15)]
	if config['delay'] > 0 :
		print("%s Decode delay %d seconds" % (space,config['delay']))
		time.sleep(config['delay'])
	if config['verbose'] :
		print("%s Start decode WAV file %s @ %s" % (space, wav_file, datetime.datetime.now()))
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
	if config['verbose'] :
		print("%s End decode WAV file %s @ %s" % (space, wav_file, datetime.datetime.now()))

def udp_send(result) :
	global nmSocket, ip_port
#	nmSocket.sendto('Start Decode {}-{}-{}'.format(config['frequency'], config['mode'], config['callsign']).encode('utf-8'),ip_port)
	iq = open('/dev/shm/ft8.txt', "a")
	for line in result.decode("utf-8").split("\n") :
		try:
			detail=line.split()
			a = int(detail[0])
			adif = ''
			if config['verbose'] :
				print("+++++ %s" % line)
			iq.write(line + '\n')
			nmSocket.sendto(line.encode('utf-8'),ip_port)
		except :
			a = 0
#			print("----- %s" % line)
	iq.close()
#	nmSocket.sendto('End Decode {}-{}-{}'.format(config['frequency'], config['mode'], config['callsign']).encode('utf-8'),ip_port)

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
					if config['verbose'] :
						print("pskr {}, {}, {}, {}, {}".format(mm.group(1), hz, "FT8", mm.group(2), tm))
					pskr.got(mm.group(1), hz, "FT8", mm.group(2), tm)
			mm = re.search(r'^([0-9A-Z/]+) ([0-9A-Z/]+) ([A-R][A-R][0-9][0-9])$', txt)
			if mm != None and iscall(mm.group(1)) and iscall(mm.group(2)):
				if pskr != None:
					if config['verbose'] :
						print("pskr {} {}, {}, {}, {}, {}".format(mm.group(1),mm.group(2), hz, "FT8", mm.group(3), tm))
					pskr.got(mm.group(2), hz, "FT8", mm.group(3), tm)

def main():
	global nmSocket, ip_port, pskr, config
	config = {
		'verbose' : False,
		'nametag' : '',
		'tmp_path' : '/dev/shm',
		'frequency' : 14074000,
		'mode' : 'FT8',
		'callsign' : 'your-callsign',
		'grid' : 'AA00',
		'udp_server_ip' : '192.168.103.1',
		'udp_server_port' : 5556,
		'delay' : 0,
	}

	#print("ARGV:", sys.argv[1:])
	options, remainder = getopt.getopt(sys.argv[1:], 't:vf:m:c:g:s:i:d:', ['tag=', 'verbose', 'frequency=', 'mode=', 'callsign=', 'grid=', 'udp-server-ip=', 'udp-server-port=', 'delay='])

	for opt, arg in options:
		if opt in ('-t', '--tag'):
			config['nametag'] = '-' + arg
		elif opt in ('-v', '--verbose'):
			config['verbose'] = True
		elif opt in ('-c', '--callsign'):
			config['callsign'] = arg.upper()
		elif opt in ('-f', '--frequency'):
			config['frequency'] = int(arg)
		elif opt in ('-m', '--mode'):
			config['mode'] = arg.upper()
		elif opt in ('-g', '--grid'):
			config['grid'] = arg.upper()
		elif opt in ('-s', '--udp-server-ip'):
			config['udp_server_ip'] = arg
		elif opt in ('-i', '--udp-server-port'):
			config['udp_server_port'] = int(arg)
		elif opt in ('-d', '--delay'):
			config['delay'] = int(arg)
	if config['verbose'] :
		print("config : %s" % config)
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
	ip_port = (gethostbyname(config['udp_server_ip']), config['udp_server_port'])
	nmSocket.sendto('Start Decode {}-{}-{}'.format(config['frequency'], config['mode'], config['callsign']).encode('utf-8'),ip_port)
	pskr = pskreport.T(config['callsign'], config['grid'], "ft8-decoder", testing=False)
	
	while True:
		data = sys.stdin.buffer.read(chunksize)
		block.extend(data)

		if datetime.datetime.now() > endtime:
			if config['verbose'] :
				print("Buffersize", len(block))
			fname = config['tmp_path'] + "/file" + config['nametag'] + "-" + starttime.strftime("%Y%m%d%H%M%S")+".wav"

			if not first:
				if config['verbose'] :
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
				t = threading.Thread(target=decoder,args=(fname,), name=datetime.datetime.now().strftime('%s'))
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
