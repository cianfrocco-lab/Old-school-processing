#!/usr/bin/env python

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
        parser.set_usage("%prog -p <path/to/images> -o <output> --Uext=[untiltExtension] --Text=[tiltExtension]")
        parser.add_option("-p",dest="path",type="string",metavar="FILE",
                help="Absolute path to the folder containing tilt-mates")
	parser.add_option("-o",dest="output",type="string",metavar="FILE",
                help="Output file to contain tilt mates")
	parser.add_option("--Uext",dest="Uext",type="string", metavar="STRING",
                help="Untilted micrograph extension (e.g. '00', 'u')")
	parser.add_option("--Text",dest="Text",type="string", metavar="STRING",
                help="Tilted micrograph extension (e.g. '01', 't')")
        parser.add_option("--leginon",action="store_true",dest="leginon",default=False,
		help="Flag if tilt mates came from leginon")
	parser.add_option("-d", action="store_true",dest="debug",default=False,
                help="debug")
        options,args = parser.parse_args()

        if len(args) > 1:
                parser.error("Unknown commandline options: " +str(args))

        if len(sys.argv) < 4:
                parser.print_help()
                sys.exit()
        params={}
        for i in parser.option_list:
                if isinstance(i.dest,str):
                        params[i.dest] = getattr(options,i.dest)
        return params
#=============================
def checkConflicts(params):
        if not params['path']:
                print "\nWarning: no path specified\n"
        elif not os.path.exists(params['path']):
                print "\nError: path '%s' does not exist\n" % params['path']
                sys.exit()
	if os.path.exists(params['output']):
		print "\nError: output file %s already exists. Exiting\n" %(params['output'])
		sys.exit()
	if not params['Text']:
                print "\nWarning: no tilted micrograph extension specified\n"
                sys.exit()
	if not params['Uext']:
                print "\nWarning: no untilted micrograph extension specified\n"
                sys.exit()

#==================
def start(param):
	
	o1 = open(params['output'],'w')	#output file

	first=1
	#Number of untilted micrographs:
	numUntilt = len(glob.glob('%s/*%s.mrc' %(param['path'],param['Uext'])))
	if param['debug'] is True:
		print 'Number of untilted micrographs = %i' %(numUntilt)
	#Number of tilted micrographs: 
	numTilt = len(glob.glob('%s/*%s.mrc' %(param['path'],param['Text'])))
        if param['debug'] is True:
                print 'Number of tilted micrographs = %i' %(numTilt)
	if numTilt != numUntilt: 
		print 'Warning: Number of untilted and tilted micrographs are unequal. Check output file to confirm they are correctly matched!'
	totalMicros = numTilt + numUntilt
	
	tiltedList = glob.glob('%s/*%s.mrc' %(param['path'],param['Text']))
	
	for tilt in sorted(tiltedList):

		tiltOrig = tilt
	
		if params['leginon'] is True:
                        #parse this type of filename: 14jul09b_00009hl_00_00008en_00.mrc 
                        tiltsplit=tilt.split('hl')
                        if params['debug'] is True:
                                print tiltsplit
                        
			untiltMiddleChange = '_'+param['Uext'][-2:]+'_'+tiltsplit[1][4:]
	
                        tilt=tiltsplit[0]+'hl'+untiltMiddleChange

			if params['debug'] is True:
				print tilt

		#Retrieve untilted micrograph pair filename	
		tiltNoExt = tilt.split('%s'%(param['Text']+'.'))
		if params['debug'] is True:
			print tiltNoExt
		
		numPartsTilt = len(tiltNoExt)
		i = 0
		untilt = ''
		while i < numPartsTilt-1:
			if i == 0:
				untilt = untilt+tiltNoExt[i]	
				i = i + 1
				continue
			untilt = untilt+tiltNoExt[i]
			if params['debug'] is True:
				print untilt
			i = i + 1
	
		#Check that tilt mates exist
		if os.path.exists('%s' %(untilt+'%s.mrc'%(param['Uext']))) is False:
			if params['debug'] is True:
				print '%s' %(untilt+'%s.mrc'%(param['Uext']))
			print 'No tilt mate for %s' %(tilt)
			continue		

		o1.write('%s\t%s\n' %(untilt+'%s.mrc'%(param['Uext']),tiltOrig))


#==============================
if __name__ == "__main__":

        params=setupParserOptions()
        checkConflicts(params)
        start(params)

