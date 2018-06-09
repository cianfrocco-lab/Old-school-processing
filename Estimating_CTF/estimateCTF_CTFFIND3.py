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
        parser.set_usage("%prog --input=<micros> --apix=<pixelSize> --mag=<magnification> --cs=<cs>")
        parser.add_option("--input",dest="micros",type="string",metavar="FILE",
                help="Wild card containing absolute path to .mrc micrographs ('/path/micro/*.mrc')")
        parser.add_option("--apix",dest="apix",type="float", metavar="FLOAT",
                help="Pixel size of micrographs")
	parser.add_option("--mag",dest="mag",type="int", metavar="INT",
                help="Magnification of micrographs")
	parser.add_option("--cs",dest="cs",type="float", metavar="float",
                help="Cs of microscope (mm)")
        parser.add_option("--kev",dest="kev",type="int", metavar="INT",
                help="Accelerating voltage (keV)")
	parser.add_option("--ampContrast",dest="contrast",type="float", metavar="FLOAT",
                help="Amplitude contrast (0.07 - cryo; 0.15 - neg. stain)")
	parser.add_option("--relionoutput", action="store_true",dest="relion",default=False,
                help="Flag to save CTFFIND output log files compatible with Relion for particle extraction")
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
	
	if os.path.exists('ctf_param.txt'):
		print "\nError: output file ctf_param.txt already exists. Exiting.\n"
		sys.exit()

	currentPath = sys.argv[0][:-24]
	ctffind = '%s/ctffind3_mp.exe'%(currentPath)
	if os.path.exists(ctffind):
		return ctffind
	if os.path.exists('/usr/bin/ctffind3_mp.exe'):
		return ctffind
	print "\nError: ctffind3_mp.exe was not found in /usr/bin or %s\n" %(ctffind)	

	if params['relion'] is True:
		if os.path.exists('all_micrographs.star'):
			print 'Error: all_micrographs.star file already exits. Exiting.'
			sys.exit()

#==============================
def estimateCTF(params,ctffindPath):

	#Read in all micros

	microList = sorted(glob.glob('%s'%(params['micros'])))

	outMicroList = open('ctf_param.txt','w')
	outMicroList.write('%s,%s,%s,%s,#cs,ht,apix,ampcontrast' %(str(params['cs']),str(params['kev']),str(params['apix']),str(params['contrast'])))
	outMicroList.write('#Micro\tDF1\tDF2\tAstig\tConfidence\n')

	for micro in microList:

		df1,df2,astig,confidence= ctffind(micro,params['apix'],params['mag'],params['cs'],params['kev'],params['contrast'],ctffindPath)	
	
		outMicroList.write('%s\t%s\t%s\t%s\t%s\n' %(micro,df1,df2,astig,confidence))

		if params['relion'] is True:
			writeRelionOutMicro(micro,df1,df2,astig,confidence,params['contrast'],params['cs'],params['kev'],params['mag'],(params['mag']*(params['apix']/10000)))

	outMicroList.close()

#==============================
def ctffind(micro,apix,mag,cs,kev,contrast,ctffindPath):

	shell=subprocess.Popen("echo $SHELL", shell=True, stdout=subprocess.PIPE).stdout.read()
	shell=shell.split('/')[-1][:-1]
	
	ctf='#!/bin/%s -x\n' %(shell)
	ctf+='%s << eof\n' %(ctffindPath)
	ctf+='%s\n' %(micro)
	ctf+='%s.ctf\n' %(micro[:-4])
	ctf+='%s,%s,%s,%s,%s	!CS[mm],HT[kV],AmpCnst,XMAG,DStep[um]\n' %(str(cs),str(kev),str(contrast),str(mag),str(params['mag']*(params['apix']/10000)))
	ctf+='128,400.0,8.0,5000.0,50000.0,1000.0,100.0	!Box,ResMin[A],ResMax[A],dFMin[A],dFMax[A],FStep[A],dAst[A]\n'
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
		if len(line) == 6:
                	if line[4] == 'Final':
				df1 = line[0]
				df2 = line[1]
				astig = line[2]
				confidence=line[3]
	return df1,df2,astig,confidence

#==============================
def writeRelionOutMicro(micro,df1,df2,astig,confidence,ampcontrast,cs,kev,mag,detector):

	ctflog = micro[:-4]+'_ctffind3.log'		
	microname = 'Micrographs/%s' %(micro)
	crosscorr = confidence
		
	#Check if new ctf log file exists
	if os.path.exists(ctflog):
		print '%s already exists. Exiting.' %(ctflog)
		return

	#Open new ctf log file
	ctf='\n'
	ctf+=' CTF DETERMINATION, V3.5 (9-Mar-2013)\n'
	ctf+=' Distributed under the GNU General Public License (GPL)\n'
	ctf+='\n'
	ctf+=' Parallel processing: NCPUS =         4\n'
	ctf+='\n'
	ctf+=' Input image file name\n'
	ctf+='%s\n' %(microname) 
	ctf+='\n'
	ctf+='\n'
	ctf+=' Output diagnostic file name\n'
	ctf+='%s.ctf\n'%(microname[:-4])
	ctf+='\n'
        ctf+='\n'
	ctf+=' CS[mm], HT[kV], AmpCnst, XMAG, DStep[um]\n'
	ctf+='  %.1f    %.1f    %.2f   %.1f    %.3f\n' %(cs,kev,ampcontrast,mag,detector)
	ctf+='\n'
	ctf+='\n'
	ctf+='      DFMID1      DFMID2      ANGAST          CC\n'
	ctf+='\n'
	ctf+='    %.2f\t%.2f\t%.2f\t%.5f\tFinal Values\n' %(float(df1),float(df2),float(astig),float(crosscorr)) 
 
	outctf = open(ctflog,'w')
	outctf.write(ctf)
	outctf.close()

#================================
def writeRelionHeader():

        relion='\n'
        relion+='data_\n'
        relion+='\n'
        relion+='loop_\n'
        relion+='_rlnMicrographName #1\n'
        relion+='_rlnDefocusU #2\n'
        relion+='_rlnDefocusV #3\n'
        relion+='_rlnDefocusAngle #4\n'
        relion+='_rlnVoltage #5\n'
        relion+='_rlnSphericalAberration #6\n'
        relion+='_rlnAmplitudeContrast #7\n'
        relion+='_rlnMagnification #8\n'
        relion+='_rlnDetectorPixelSize #9\n'
        relion+='_rlnCtfFigureOfMerit #10\n'

        return relion

#================================
def convertToRelionSTAR(ctfparam,microstar,params):

        relionOut = writeRelionHeader()

        out = open(microstar,'w')

        ctf = open(ctfparam,'r')

        for line in ctf:
                l = line.split()

                if l[-2] == 'Astig':
                        continue

                #Prepare micrograph name
                micro = l[0].split('/')[-1]
                microname = 'Micrographs/%s' %(micro)

                #Get defocus information
                df1 = float(l[1])
                df2 = float(l[2])
                astig = float(l[3])
		crosscor=float(l[4])
                ampcontrast = params['contrast']

                relionOut+='%s  %.6f  %.6f  %.6f  %.6f  %.6f  %.6f  %.6g  %.6f  %.6f\n' %(microname,df1,df2,astig,params['kev'],params['cs'],params['contrast'],params['mag'],params['mag']*(params['apix']/10000),crosscor)

        out.write(relionOut)

#==============================
if __name__ == "__main__":

        params=setupParserOptions()
        ctffindPath = checkConflicts(params)
	estimateCTF(params,ctffindPath)
	if params['relion'] is True:
		convertToRelionSTAR('ctf_param.txt','all_micrographs.star',params)

	#Clean up
	os.remove('ctffindLog.log')
	os.remove('ctffindrun.com')
