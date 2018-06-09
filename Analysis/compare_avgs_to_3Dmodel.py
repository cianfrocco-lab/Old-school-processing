#!/usr/bin/env python 

#This script will align 2D class averagees to a 3D model
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
        parser.set_usage("%prog -i <stack.img> --num=[number of class averages] --boxsize=[boxsize of data] -v <volume>")
        parser.add_option("-i",dest="stack",type="string",metavar="FILE",
                help="Stack of 2D class averages in .img format.")
        parser.add_option("--num",dest="numParts",type="int", metavar="INT",
                help="Number of class averages")
	parser.add_option("--boxsize",dest="boxsize",type="int", metavar="INT",
                help="Boxsize of particles and 3D model")
	parser.add_option("-v",dest="vol",type="string",metavar="FILE",
                help="3D volume to be aligned to 2D averages (.mrc or .spi format)")
        parser.add_option("--angstep",dest="angstep",type="int", metavar="INT",default=10,
                help="Angular step for projecting 3D model (Default=10 degrees)")
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
        if not params['stack']:
                print "\nWarning: no stack specified\n"
        elif not os.path.exists(params['stack']):
                print "\nError: 2D average stack file '%s' does not exist\n" % params['stack']
                sys.exit()
        if params['stack'][-4:] != '.img':
        	if params['stack'][-4:] != '.hed':
                	print 'Stack extension %s is not recognized as .hed or .img file' %(params['stack'][-4:])
                        sys.exit()

	if not os.path.exists(params['vol']):
		print 'Error: input volume does not exist.'
		sys.exit()

#==============================
def getEman2Path():
        eman2path = subprocess.Popen("env | grep EMAN2", shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        if not eman2path:
		print "EMAN2 was not found, make sure EMAN2 is loaded"
		sys.exit()	

#===============================
def align_3D_model_to_avgs(vol,stack,num,boxsize,angstep):

	#Copy spider script to current working directory
	cmd='cp %s/compare_avgs_SingleModel.spi .' %(sys.argv[0][:-26])
	subprocess.Popen(cmd,shell=True).wait()
	
	#Remove tmp directory if it exists
	if os.path.isdir('tmpdirspi'):
		shutil.rmtree('tmpdirspi/')

	#Remove input temp file if it exists
	if os.path.exists('inputfilespitmp.txt'):
		os.remove('inputfilespitmp.txt')

	#Write spider inputs into temp file
	o1=open('inputfilespitmp.txt','w')
	o1.write('%s\n' %(stack[:-4]))
	o1.write('%i\n' %(num))
	o1.write('%s\n' %(vol[:-4]))
	o1.write('%i\n' %(boxsize))
	o1.write('%i\n' %(angstep))
	o1.write('tmpdirspi\n')
	o1.close()

	cmd='spider spi @compare_avgs_SingleModel < inputfilespitmp.txt'
	subprocess.Popen(cmd,shell=True).wait()

	return 'tmpdirspi/aligned_avgs_model.spi'

#==============================
if __name__ == "__main__":

        params=setupParserOptions()
        checkConflicts(params)
	getEman2Path()

	#Remove temporary files if they exist
	if os.path.exists('spivolalign.spi'):
		os.remove('spivolalign.spi')

	if os.path.exists('tmpspistack.spi'):
		os.remove('tmpspistack.spi')

	#Convert stack to spider format & 3D volume
	if params['vol'][-4:] == '.mrc':
		cmd='e2proc3d.py %s spivolalign.spi --outtype spidersingle'%(params['vol'])
		subprocess.Popen(cmd,shell=True).wait()	 

	if not os.path.exists('spivolalign.spi'):
		cmd='e2proc3d.py %s spivolalign.spi --outtype spidersingle' %(params['vol'])
                subprocess.Popen(cmd,shell=True).wait()

	cmd='e2proc2d.py %s tmpspistack.spi --outtype spi' %(params['stack'])
	subprocess.Popen(cmd,shell=True).wait()	

	outimages=align_3D_model_to_avgs('spivolalign.spi','tmpspistack.spi',params['numParts'],params['boxsize'],params['angstep'])

	#Convert output stack into new named .img stack
	cmd='e2proc2d.py %s %s_alignedWithVol_%s.img' %(outimages,params['stack'][:-4],params['vol'][:-4])
	subprocess.Popen(cmd,shell=True).wait()


	#Clean up
	cmd = 'rm -rf tmpdirspi compare_avgs_SingleModel.spi inputfilespitmp.txt spivolalign.spi tmpspistack.spi'
	subprocess.Popen(cmd,shell=True).wait()


