#!/bin/bash
# Simple script to echo back what came in.

echo "Starting"
read DATALINE
while test -n "$DATALINE" ; do
  echo "Got [$DATALINE]"
  read DATALINE
done
echo "Ending"
