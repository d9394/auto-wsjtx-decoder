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
	rtl_fm -f 64074000 -M usb - | sox -t raw -b 16 -c 1 -r 24k -es -V1 - -t wav -r 12k - | \
	  python3 -u ft8-decoder.py &

	child=$! 
	wait "$child"

done
