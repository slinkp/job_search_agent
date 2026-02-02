#!/bin/bash

PIDS=$(ps wax | grep research_daemon | grep ython | grep -v grep | cut -d ' ' -f 1-2)
if [ -z "$PIDS" ]; then
	echo None to kill
else
	for P in `echo "$PIDS"`; do
		echo "Killing $P ..."
		kill $P
	done
	echo "done"
fi
