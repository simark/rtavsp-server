 #!bin/bash

set -e

pids=()

function int_handler() {
	for pid in ${pids[@]}; do
		echo "Killing pid $pid"
		pkill -P $pid
	done
}

trap int_handler INT

for i in stream-*; do
	./play.sh $i 5 &
	pid=$!
	echo "Spawned $i with pid $pid"
	pids+=($pid)
done

wait
