#!/bin/bash
set -e
while true
do
	_term() {
		echo "Caught signal!" 
		kill -9 -TERM "$child" 2>/dev/null
	}
		
	trap _term SIGTERM SIGINT

	#netcat -l -p 1234 | python3 splitter.py &
	aa=$(netstat -nt | grep 5678 | wc -l)
	if [ $aa -eq 0 ]; then
		rtl_fm -f 64074000 -M usb - | sox -t raw -b 16 -c 1 -r 24k -es -V1 - -t wav -r 12k - | nc -k -l -p 5678 &
	fi
	sleep 1
	bb=$(ps aux | grep -v grep | grep python3 | grep ft8-decoder | wc -l)
	if [ $bb -eq 0 ]; then
		nc 127.0.0.1 5678 | python3 -u /root/ft8-decode/ft8-decoder.py -c ba7ib-2 -f 14074000 -m ft8 -g ol63 -d 3 -v
	fi
	child=$! 
	wait "$child"

done
