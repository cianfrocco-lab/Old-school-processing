#!/usr/bin/env python 

#This script will using CTFTILT to estimate the CTF of micrographs & output tilt info.. 
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
        parser.set_usage("%prog --input=<micros> --output=<outputfile> --apix=<pixelSize> --tilt=<tilt> --mag=<magnification> --cs=<cs> --kev=<kev> --ampContrast=<amp>")
        parser.add_option("--input",dest="micros",type="string",metavar="FILE",
                help="Wild card containing absolute path to .mrc tilted micrographs ('/path/micro/*.mrc')")
	parser.add_option("--output",dest="output",type="string",metavar="FILE",
                help="Output filename")
        parser.add_option("--apix",dest="apix",type="float", metavar="FLOAT",
                help="Pixel size of micrographs")
	parser.add_option("--tilt",dest="tilt",type="int", metavar="int",
                help="Estimate of tilt angle")
	parser.add_option("--mag",dest="mag",type="int", metavar="INT",
                help="Magnification of micrographs")
	parser.add_option("--cs",dest="cs",type="float", metavar="float",
                help="Cs of microscope (mm)")
        parser.add_option("--kev",dest="kev",type="int", metavar="INT",
                help="Accelerating voltage (keV)")
	parser.add_option("--ampContrast",dest="contrast",type="float", metavar="FLOAT",
                help="Amplitude contrast (0.07 - cryo; 0.15 - neg. stain)")
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
        if not params['apix']:
                print "\nWarning: no pixel size specified\n"
		sys.exit()

	if not params['mag']:
                print "\nWarning: no magnification specified\n"
		sys.exit()
	
	if os.path.exists(params['output']):
		print "\nError: output file %s already exists. Exiting.\n" %(params['output'])
		sys.exit()
	currentPath = sys.argv[0][:-23]
	ctffind = '%s/ctftilt_mp.exe'%(currentPath)
	if os.path.exists(ctffind):
		return ctffind
	if os.path.exists('/usr/bin/ctftilt_mp.exe'):
		return ctffind
	print "\nError: ctftilt_mp.exe was not found in /usr/bin or %s\n" %(ctffind)	

#==============================
def estimateCTF(params,ctffindPath):

	#Read in all micros

	microList = sorted(glob.glob('%s'%(params['micros'])))

	outMicroList = open(params['output'],'w')
	outMicroList.write('%s,%s,%s,%s,#cs,ht,apix,ampcontrast' %(str(params['cs']),str(params['kev']),str(params['apix']),str(params['contrast'])))
	outMicroList.write('#Micro\tDF1\tDF2\tAstig\tTiltaxis\tTiltangle\n')

	for micro in microList:

		df1,df2,astig,tiltaxis,tiltang = ctffind(micro,params['apix'],params['mag'],params['cs'],params['kev'],params['contrast'],ctffindPath,params['tilt'])	
	
		outMicroList.write('%s\t%s\t%s\t%s\t%s\t%s\n' %(micro,df1,df2,astig,tiltaxis,tiltang))

	outMicroList.close()

#==============================
def ctffind(micro,apix,mag,cs,kev,contrast,ctffindPath,tiltguess):

	ctf='#!/bin/sh -x\n'
	ctf+='%s << eof\n' %(ctffindPath)
	ctf+='%s\n' %(micro)
	ctf+='%s_pow.mrc\n' %(micro[:-4])
	ctf+='%s,%s,%s,%s,%s,2	!CS[mm],HT[kV],AmpCnst,XMAG,DStep[um]\n' %(str(cs),str(kev),str(contrast),str(mag),str(params['mag']*(params['apix']/10000)))
	ctf+='128,400.0,8.0,5000.0,50000.0,1000.0,100.0,%i,10	!Box,ResMin[A],ResMax[A],dFMin[A],dFMax[A],FStep[A],dAst[A],TiltA[deg],TiltR[deg]\n' %(tiltguess)
	ctf+='eof\n'

	if os.path.exists('ctffindrun.com'):
		os.remove('ctffindrun.com')

	if os.path.exists('ctffindLog.log'):
		os.remove('ctffindLog.log')

	ctfFile = open('ctffindrun.com','w')
 	ctfFile.write(ctf)
	ctfFile.close()

	cmd = 'chmod +x ctffindrun.com'	
	subprocess.Popen(cmd,shell=True).wait()	

	cmd = './ctffindrun.com > ctffindLog.log'
	subprocess.Popen(cmd,shell=True).wait()  

	logfile = open('ctffindLog.log')

	for logLine in logfile:
        	line = logLine.split()
		if len(line) == 8:
                	if line[6] == 'Final':
				df1 = line[0]
				df2 = line[1]
				astig = line[2]
				tiltaxis = line[3]
				tiltang = line[4]

	return df1,df2,astig,tiltaxis,tiltang

#==============================
if __name__ == "__main__":

        params=setupParserOptions()
        ctffindPath = checkConflicts(params)
	estimateCTF(params,ctffindPath)
