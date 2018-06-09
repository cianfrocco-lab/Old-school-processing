#!/usr/bin/env python 

#This script will remove particles from a stack based upon a user-provided list and the output from Auto Align
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
        parser.set_usage("%prog -i <stack.img> -o <output folder name> --num=[number of particles in stack]")
        parser.add_option("--autoalignfolder",dest="folder",type="string",metavar="FOLDER",
                help="Input output folder from Auto_Align.py that contains the auto_iteration_? folders.")
        parser.add_option("--stack",dest="stack",type="string",metavar="FILE",
                help="Input particle stack (.img) from which the averages were calculated, and from which particles will be removed")
        parser.add_option("--badlist",dest="badlist",type="string",metavar="FILE",
                help="Text file containing list of 'bad' class averages, where they are numbered according to the convention where particle #1 is '0', etc.")
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
        if params['stack'][-4:] != '.img':
        	if params['stack'][-4:] != '.hed':
                	print 'Stack extension %s is not recognized as a .hed or .img file' %(params['stack'][-4:])
                        sys.exit()

        if not os.path.exists('%s/auto_iteration_1/' %(params['folder'])):
                print "\nError: Auto_Align.py output folder does not exist. Exiting.\n"
                sys.exit()

	if not os.path.exists(params['badlist']):
		print "\nError: Bad list %s does not exist. Exiting" %(params['badlist'])
		sys.exit()

#==============================
if __name__ == "__main__":

        params=setupParserOptions()
        checkConflicts(params)

	#Create EMAN numbered text file 
	##Get number of select files:
	numClass=len(glob.glob('%s/auto_iteration_1/classsums1_class_*'%(params['folder'])))
	classcounter=1
	if params['debug'] is True:
		print 'Number of classes: %i' %(numClass)

	#Remove tmp file if it already exists
	if os.path.exists('tmpemanfile33.txt'):
		os.remove('tmpemanfile33.txt')

	goodlistout=open('tmpemanfile33.txt','w')
	
	while classcounter<=numClass:

		#Check if this class is in the bad list
		openbad=open(params['badlist'],'r')
		flag=0
		for line in openbad:
			checkclass=float(line.split()[0])
			if checkclass == (classcounter-1):
				flag=1
		openbad.close()

		#Write particles in select file if not in bad list
		if flag == 0:
			opensel=open('%s/auto_iteration_1/classsums1_class_%04i.spi'%(params['folder'],classcounter),'r')
			for line in opensel:
				particle=int(line.split()[2])-1
				goodlistout.write('%i\n' %(particle))		
			opensel.close()
		classcounter=classcounter+1
	goodlistout.close()

	#Make stack of ONLY the particles NOT in the list
	cmd='e2proc2d.py %s %s_select.img --list=tmpemanfile33.txt' %(params['stack'],params['stack'][:-4])
	subprocess.Popen(cmd,shell=True).wait()	
	
	#Clean up - remove list
	os.remove('tmpemanfile33.txt')

