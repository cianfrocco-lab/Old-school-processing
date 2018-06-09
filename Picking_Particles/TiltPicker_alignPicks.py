#!/usr/bin/env python 

#This script will use CTFTILT info and particles coordinates to align tilt mates, outputting 
#matching particles coordinates
#
#Assumes that .box files have the same basename as the micrographs (.mrc)
#
#Assumes that the two ctf parameter files from estimateCTF_CTFTILT.py are listed in the same order.
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
        parser.set_usage("%prog -u <ctf untilt> -t <ctf tilt> --override=<angle>")
        parser.add_option("-u",dest="untilt",type="string",metavar="FILE",
                help="Output ctf file from estimateCTF_CTFTILT.py for untilted images")
        parser.add_option("-t",dest="tilt",type="string",metavar="FILE",
                help="Output ctf file from estimateCTF_CTFTILT.py for tilted images")
	parser.add_option("--override",dest="override",type="int", metavar="INT",default=0,
                help="Input tilt angle to override taking angular differences between untilted and tilted micrographs. Untilted angle will be set to 0 and tilt angle will be set to angle specified.")	
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

#=============================
def checkConflicts(params):
        
	if not os.path.exists(params['untilt']):
                print "\nError: untilted ctf file '%s' does not exist\n" % params['untilt']
                sys.exit()

	if not os.path.exists(params['tilt']):
                print "\nError: tilted ctf file '%s' does not exist\n" % params['tilt']
                sys.exit()

#==============================
def align_tilts(params):

	#Find number of micrographs to analyze
	numpairs = len(open(params['untilt']).readlines())-1

	if params['debug'] is True:
		print '\nNumber of tilt pairs = %i' %(numpairs)

	#Loop over each tilt pair
	i = 1

	while i <= numpairs:

		#Get untilt micrograph name & info
		untilt = linecache.getline(params['untilt'],i+1)
	
		untiltline = untilt.split()
		untilt = untiltline[0]
		if params['override'] == 0: 
			untilt_angle = untiltline[5]
			untilt_axis = untiltline[4]
		if params['override'] != 0: 
			untilt_angle = 0
			untilt_axis = 0

		if params['debug'] is True:
			print '\nUntilted micrograph = %s' %(untilt)
			print 'tilt = %s' %(untilt_angle)
			print 'tilt axis = %s' %(untilt_axis)

		#Get tilt micrograph name & info
                tilt = linecache.getline(params['tilt'],i+1)

                tiltline = tilt.split()
                tilt = tiltline[0]
                if params['override'] == 0:
			tilt_axis = tiltline[4]
                	tilt_angle = tiltline[5]

		if params['override'] != 0:
                        tilt_axis = 86
                        tilt_angle = params['override']

                if params['debug'] is True:
                        print '\nTilted micrograph = %s' %(tilt)
                        print 'tilt = %s' %(tilt_angle)
                        print 'tilt axis = %s\n' %(tilt_axis)

		#Convert box files to .spi coordinates & bin coordinates by 4
		if os.path.exists('tmp_untilt.spi'):
			os.remove('tmp_untilt.spi')
		if os.path.exists('tmp_tilt.spi'):
                        os.remove('tmp_tilt.spi')

		boxsize = box_to_spi('%s.box' %(untilt[:-4]),'tmp_untilt.spi',4)
		boxsize = box_to_spi('%s.box' %(tilt[:-4]),'tmp_tilt.spi',4)

		#Binning micrographs by 4:
		if os.path.exists('tmp_untilt.mrc'):
                        os.remove('tmp_untilt.mrc')
                if os.path.exists('tmp_tilt.mrc'):
                        os.remove('tmp_tilt.mrc')
		if os.path.exists('outputpicks.spi'):
			os.remove('outputpicks.spi')

		cmd = 'proc2d %s tmp_untilt.mrc meanshrink=4' %(untilt)
		subprocess.Popen(cmd,shell=True).wait()

		cmd = 'proc2d %s tmp_tilt.mrc meanshrink=4' %(tilt)
                subprocess.Popen(cmd,shell=True).wait()

		#Run tilt auto picker: 

		actual_tiltangle = float(tilt_angle) - float(untilt_angle)
		if actual_tiltangle < 0:
			actual_tiltangle = actual_tiltangle*-1

		actual_tiltaxis = 90 - float(tilt_axis)

		diameter = round(int(boxsize)/1.2)/4

		cmd = 'ApTiltAutoPicker.py -1 tmp_untilt.mrc -2 tmp_tilt.mrc --p1=tmp_untilt.spi --p2=tmp_tilt.spi -t %s -o outputpicks.spi -d %s -x %s' %(str(actual_tiltangle),str(diameter),str(actual_tiltaxis))
		if params['debug'] is True:
			print cmd
		p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		out,err = p.communicate()

		#Retreive RMSD value from alignment	
		errout = err.split('rmsd')[-1]
		errout = errout.split()
		rmsd = errout[0][1:-1]
		if params['debug'] is True:
			print 'RMSD = %s' %(rmsd)
	
		#Only write output box files if RMSD < 20 Angstroms
		if float(rmsd) < 20:
			
			img1,img2 = parse_outputpicks('outputpicks.spi')
			
			spi_to_box(img1,'%s_final.box' %(untilt[:-4]),4,boxsize)
			spi_to_box(img2,'%s_final.box' %(tilt[:-4]),4,boxsize)	

		if float(rmsd) >=20: 

			print 'WARNING! RMSD = %s for tilt mates %s & %s. Not writing output box files\n' %(rmsd,untilt,tilt)
	

		#Cleanup
		cmd = 'rm tmp_tilt*'
		subprocess.Popen(cmd,shell=True).wait()

		cmd = 'rm tmp_untilt*'
                subprocess.Popen(cmd,shell=True).wait()

		os.remove('outputpicks.spi')
		
		cmd = 'rm guess-cross*'
		subprocess.Popen(cmd,shell=True).wait()

		i = i + 1

#==============================
def parse_outputpicks(picks):

	f1 = open(picks,'r')

	if os.path.exists('tmp_untilt_final.spi'):
		os.remove('tmp_untilt_final.spi')
	if os.path.exists('tmp_tilt_final.spi'):
                os.remove('tmp_tilt_final.spi')

	img1 = open('tmp_untilt_final.spi','w')
	img2 = open('tmp_tilt_final.spi','w')

	counter = 1

	#Determine line numbers for beginning & end of untilted and tilted coordinates
	for line in f1:

		l = line.split()
		if len(l) > 1: 
			if l[1] == 'LEFT':
				untilt_begins = counter + 1	

		if len(l) > 1:
                        if l[1] == 'RIGHT':
                                tilt_begins = counter + 1

		counter = counter + 1

	f1.close()

	tilt_ends = len(open(picks,'r').readlines())
	untilt_ends = tilt_begins-2
	f1.close()

	#Read lines & write into new files
	counter = 1
	f1 = open(picks,'r')

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
	return 'tmp_untilt_final.spi','tmp_tilt_final.spi'

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
        checkConflicts(params)
	align_tilts(params)
