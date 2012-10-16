#!/bin/bash
#
# Joue les images contenues dans le dossier 'output' du stream à un intervalle de 1 seconde.

set -e

if [ "$#" -lt 2 ]; then
	echo "Usage $0 [stream dir] [sleep time]"
	exit
fi

cd $1

while true; do
	for i in output/*.jpg; do
		cat $i > current.jpg
		sleep $2
	done
done
