#!/usr/bin/env python 

#This script will use output files (*manualpicks.spi) to output .box files
#
#TEM|pro - mcianfrocco

import optparse
from sys import *
import os,sys,re
from optparse import OptionParser
import glob
import subprocess
from os import system
import linecache
import time


#=========================
def setupParserOptions():
        parser = optparse.OptionParser()
        parser.set_usage("%prog -p <picks> --boxsize=<box>")
        parser.add_option("-p",dest="picks",type="string",metavar="FILE",
                help="Wildcard with .spi output files from ApTiltPicker ('*manualpicks.spi') By default the program will remove the string '-manualpicks.spi'")
	parser.add_option("--boxsize",dest="box",type="int", metavar="INT",default=0,
                help="Box size")	
        parser.add_option("-d", action="store_true",dest="debug",default=False,
                help="debug")
        options,args = parser.parse_args()

        if len(args) > 0:
                parser.error("Unknown commandline options: " +str(args))

        if len(sys.argv) < 3:
                parser.print_help()
                sys.exit()
        params={}
        for i in parser.option_list:
                if isinstance(i.dest,str):
                        params[i.dest] = getattr(options,i.dest)
        return params

#==============================
def makebox_tilts(params):

	microlist = glob.glob(params['picks'])

	for micro in microlist:

		img1,img2 = parse_outputpicks(micro)
		
		spi_to_box(img1,'%s.box' %(img1[:-4]),1,params['box'])
		spi_to_box(img2,'%s.box' %(img2[:-4]),1,params['box'])	


#==============================
def parse_outputpicks(picks):

	f1 = open(picks,'r')

	counter = 1

	#Determine line numbers for beginning & end of untilted and tilted coordinates
	for line in f1:

		l = line.split()
		if len(l) > 1: 
			if l[1] == 'LEFT':
				untilt_begins = counter + 1	
				untiltmicro = l[4]
		if len(l) > 1:
                        if l[1] == 'RIGHT':
                                tilt_begins = counter + 1
				tiltmicro = l[4]
		counter = counter + 1

	f1.close()

	tilt_ends = len(open(picks,'r').readlines())
	untilt_ends = tilt_begins-2
	f1.close()

	#Read lines & write into new files
	counter = 1
	f1 = open(picks,'r')

	img1=open('%s_manual.spi' %(untiltmicro[:-4]),'w')
	img2=open('%s_manual.spi' %(tiltmicro[:-4]),'w')

	for line in f1:

		if counter <= untilt_ends:
			if counter >= untilt_begins:
				img1.write(line)

		if counter <= tilt_ends:
                        if counter >= tilt_begins:
                                img2.write(line)
		counter = counter + 1
	img1.close()
	img2.close()
	return '%s_manual.spi' %(untiltmicro[:-4]),'%s_manual.spi' %(tiltmicro[:-4])

#==============================
def box_to_spi(boxfile,spdfile,binning):

	f = open(boxfile,'r')

	o1 = open(spdfile,'w')

	loop = 1

	for line in f:

		l = line.split()

		x=l[0]
		y=l[1]
		box=int(l[2])

		x = round((int(x)+box/2)/binning)
		y = round((int(y)+box/2)/binning)

		o1.write('%i\t2\t%i\t%i\n' %(loop,x,y))

		loop = loop + 1	

	return box

#==============================
def spi_to_box(spifile,boxfile,binning,boxsize):

	f = open(spifile,'r')

        o1 = open(boxfile,'w')

        for line in f:

                l = line.split()

                x=l[3]
                y=l[4]

                x = round((float(x)*binning))-boxsize/2
		y = round((float(y)*binning))-boxsize/2

                o1.write('%i\t%i\t%i\t%i\n' %(x,y,boxsize,boxsize))

#==============================
if __name__ == "__main__":

        params=setupParserOptions()
	makebox_tilts(params)
