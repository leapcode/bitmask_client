#!/bin/zsh
if (( ! $# )); then
    echo "Usage: $0:t <PID> <minutes to monitor>" >&2
    return 1;
fi

OUT="$1-usage.data"
GRAPH="bitmask-resources.png"
MAX=150
let "ticks=$2*60/3"
echo "cpu mem" >> $OUT
for i in {1..$ticks}; do;
    cpu=$(ps -p $1 -o pcpu | grep -v %)
    mem=$(ps wuh -p $1 | awk '{print $4}')
    echo "$cpu $mem" >> $OUT;
    sleep 3;
    echo $i / $ticks;
done;

gnuplot -e "set term dumb; \
set key outside; set yrange [0:$MAX]; \
plot for [col=1:2] '$OUT' using 0:col title columnheader s c"

gnuplot -e "set term png; set output '$GRAPH'; \
set key outside; set yrange [0:$MAX]; \
plot for [col=1:2] '$OUT' using 0:col with lines title columnheader"
