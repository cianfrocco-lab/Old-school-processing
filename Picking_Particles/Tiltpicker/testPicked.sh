#!/bin/sh

#this is a file for neil to test tiltpicker without Appion/Leginon installed

cp -v /home/vossman/myami/appion/bin/ApTiltPicker.py .
unset PYTHONPATH
#./ApTiltPicker.py -l data/rawu049b.jpg -r data/rawu048b.jpg -p data/rawu0picks.spi
./ApTiltPicker.py -l data/rawu049b.jpg -r data/rawu048b.jpg
source /etc/bashrc
