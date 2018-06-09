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
		parser.set_usage("%prog --stack=<tilted stack> --tiltinfo=<ctftiltTiltFile> --selfile=<select> --autoalignfolder=<inputfolder> --output=<folder> --angle=<angle> --apix=<apix> --radius=<rad>")
		parser.add_option("--stack",dest="stack",type="string",metavar="FILE",
				help="Tilted stack in imagic format (.img)")
		parser.add_option("--untiltinfo",dest="untiltinfo",type="string",metavar="FILE",
				help="CTFTILT info file for untilted particles")
		parser.add_option("--tiltinfo",dest="tiltinfo",type="string",metavar="FILE",
				help="CTFTILT info file for tilted particles")
		parser.add_option("--selfile",dest="selfile",type="string",metavar="FILE",
				help="List of class numbers to reconstruct in EMAN format (First class average number is '0')")
		parser.add_option("--autoalignfolder",dest="inputfolder",type="string",metavar="FILE",
				help="Absolute path to folder containing the select files & APSH to use for RCT reconstruction")
		parser.add_option("--output",dest="folder",type="string", metavar="STRING",
				help="Output folder to store RCT volumes")
		parser.add_option("--angle",dest="angle",type="int", metavar="INT",
				help="Approximate tilt angle (with correct sign) for tilted particles (e.g. -55)")
		parser.add_option("--apix",dest="apix",type="float", metavar="FLOAT",
				help="Pixel size")
		parser.add_option("--lptilt",dest="lptilt",type="float", metavar="FLOAT",default=0,
                                help="Low pass filter for tilted particles (Default=None).")
		parser.add_option("--hptilt",dest="hptilt",type="float", metavar="FLOAT",default=0,
                                help="High pass filter for tilted particles (Default=None).")
		parser.add_option("--radius",dest="radius",type="int", metavar="INT",
				help="Radius (pixels) for 3D reconstruction")
		parser.add_option("--filter",dest="filter",type="int", metavar="INT",default=0,
				help="OPTIONAL: User specified low pass filter for RCT volumes during centering routine. Otherwise volumes are filtered to FSC=0.5")
		parser.add_option("--override", action="store_true",dest="override",default=False,
				help="Flag to override CTFTILT files, using ONLY specified tilt angle for RCT reconstruction")
		parser.add_option("--numparts", dest="numparts",type="int", metavar="INT",default=0,
                                help="IF using OVERRIDE: Input number of particles.")
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
	if not params['folder']:
		print "\nError: No output folder specified. Exiting.\n"
		sys.exit()
	if os.path.exists(params['folder']):
		print "\nError: Output folder %s already exists. Exiting." %(params['folder'])
		sys.exit()
	if not os.path.exists(params['stack']):
		print "\nError: Input stack %s does not exist. Exiting." %(params['stack'])
		sys.exit()
	if params['override'] is False:
		if not os.path.exists(params['untiltinfo']):
			print "\nError: Input file %s does not exist. Exiting." %(params['untiltinfo'])
			sys.exit()
		if not os.path.exists(params['tiltinfo']):
			print "\nError: Input file %s does not exist. Exiting." %(params['tiltinfo'])
			sys.exit()
	if not os.path.exists(params['selfile']):
		print "\nError: Input file %s does not exist. Exiting." %(params['selfile'])
		sys.exit()

#=============================
def getNumberOfLines(f1):

		totallines=len(open(f1,'r').readlines())
		return totallines

#==============================
def getEMANPath():
		emanpath = subprocess.Popen("env | grep EMAN2DIR", shell=True, stdout=subprocess.PIPE).stdout.read().strip()
		if emanpath:
				emanpath = emanpath.replace("EMAN2DIR=","")
		if os.path.exists(emanpath):
				return emanpath
		print "EMAN2 was not found, make sure the EMAN2 module is loaded"
		sys.exit()

#=============================
def writeSpiderEulerAngles(apshfile,untiltinfo,tiltinfo,out,angle,debug,iternum,inputfolder,numflag,override,numparts):

	if override is False:
		if getNumberOfLines(untiltinfo) != getNumberOfLines(tiltinfo):
			print '%s has a different number of lines than %s. Exiting.' %(untiltinfo,tiltinfo)
			sys.exit()

	#Write euler angles
	o1=open(out,'w')
	line=1

	if override is True:
		tot=numparts
	if override is False:
		tot=getNumberOfLines(untiltinfo)
	
	while line<= tot:

		if debug is True:
			print 'Working on particle %i'%line

		#Need to get cumulative rotation during spider alignment, NOT just the last rotation angle.
		cumulMRAangle=getCumulRotSPIDER(iternum,line,inputfolder,debug,numflag) 
		untiltline=linecache.getline(untiltinfo,line)
		tiltline=linecache.getline(tiltinfo,line)

		if debug is True:
			print 'untilt line = %s' %(untiltline)
			print 'tilt line = %s' %(tiltline)
			print 'cumul ROT = %f' %(cumulMRAangle)

		if override is False:
			ctftiltRotUntilt=float(untiltline.split()[3])
			ctftiltAngUntilt=float(untiltline.split()[4])
			ctftiltRotTilt=float(tiltline.split()[3])
			ctftiltAngTilt=float(tiltline.split()[4])

		if override is True:
			ctftiltRotUntilt=88
                        ctftiltAngUntilt=0
                        ctftiltRotTilt=88
                        ctftiltAngTilt=angle

		#Calc euler angles; flip sign of tilt angle for tilted micrograph if the sign is wrong (sometimes ctftilt messes up absolute tilt angle)
		#IF you are changing the sign of tilt angle, you need to change the rotation angle of the micrograph

		if ctftiltAngTilt > 0:
			if angle < 0:
				ctftiltAngTilt = ctftiltAngTilt*-1
				ctftiltRotTilt = ctftiltRotTilt + 180

		if ctftiltAngTilt < 0:
			if angle > 0:
				ctftiltAngTilt = ctftiltAngTilt*-1
				ctftiltRotTilt = ctftiltRotTilt - 180

		PHI= ctftiltRotUntilt - 90 - cumulMRAangle #Gets in plane rotation angle & adds this rotation to the ctftiltRotTilt
		if PHI < 0:
			PHI = PHI+360
		THETA = ctftiltAngTilt        #Only using tilt angle of tilted micrograph.
		PSI = 90 - ctftiltRotTilt
		o1.write('%i\t3\t%s\t%s\t%s\n' %(line,str(PSI),str(THETA),str(PHI)))

		line = line + 1
	o1.close()

#==============================
def getCumulRotSPIDER(iternum,line,inputfolder,debug,numflag):

	counter=1
	cumulMRA=0
	while counter < iternum:
	
		#Get line from APSH file - particle is counter + 2 to avoided commented lines
		if debug is True:
			print counter
			print iternum
			print '%s%i/mra%i_apsh.spi' %(inputfolder[:-numflag],counter,counter)
			print linecache.getline('%s%i/mra%i_apsh.spi' %(inputfolder[:-numflag],counter,counter),line+2)

		rot=linecache.getline('%s%i/mra%i_apsh.spi' %(inputfolder[:-numflag],counter,counter),line+2).split()[13]
		if debug is True:
			print 'Iter %i' %(counter)
			print rot	

		cumulMRA=float(rot)+cumulMRA

		if cumulMRA>360:
			cumulMRA=cumulMRA-360
			
		if debug is True:
			print cumulMRA	

		counter=counter+1
	
	return cumulMRA

#=============================
def recontruct_volume_and_refine(eulers,stack,numClasses,workingdir,debug,apix,radius,rotShift,lowpass,selfile,basename,autoalignfolder):

	#Loop over all classes in select file
	counter=1

	while counter<=numClasses:

		#Get class number from select file & then add 1 to it to correct from EMAN to SPIDER numbering conventions
		selclass=float(linecache.getline(selfile,counter))+1

		#Create folder witih output files for class
		os.makedirs('%s/selectFiles/sel%04d' %(workingdir,selclass))

		o1=open('%s/selectFiles/sel%04d/resolution' %(workingdir,selclass),'a')

		reconstruct(stack,'%s%04d.spi' %(basename,selclass),eulers,'%s/selectFiles/sel%04d' %(workingdir,selclass))
		fsc=calcFSC_filter('%s/selectFiles/sel%04d/vol001' %(workingdir,selclass),'%s/selectFiles/sel%04d/vol1001' %(workingdir,selclass),'%s/selectFiles/sel%04d/vol2001' %(workingdir,selclass),apix/lowpass)

		o1.write('%s\t%s\n' %('vol001_fq.spi',str(apix/float(fsc))))

		volcounter=1
		itermax=5

		while volcounter<=itermax:
			if volcounter==1:
				refine3D('%s%04d' %(basename,selclass),eulers,'%s/selectFiles/sel%04d/vol%03d_fq' %(workingdir,selclass,volcounter),'%s/selectFiles/sel%04d/vol%03d' %(workingdir,selclass,volcounter+1),radius,'blank',stack,apix)

				fsc=calcFSC_filter('%s/selectFiles/sel%04d/vol%03d' %(workingdir,selclass,volcounter+1),'%s/selectFiles/sel%04d/vol1%03d' %(workingdir,selclass,volcounter+1),'%s/selectFiles/sel%04d/vol2%03d' %(workingdir,selclass,volcounter+1),apix/lowpass)

			if volcounter>1:
				refine3D('%s%04d' %(basename,selclass),eulers,'%s/selectFiles/sel%04d/vol%03d_fq' %(workingdir,selclass,volcounter),'%s/selectFiles/sel%04d/vol%03d' %(workingdir,selclass,volcounter+1),radius,rotShift,stack,apix)

				fsc=calcFSC_filter('%s/selectFiles/sel%04d/vol%03d' %(workingdir,selclass,volcounter+1),'%s/selectFiles/sel%04d/vol1%03d' %(workingdir,selclass,volcounter+1),'%s/selectFiles/sel%04d/vol2%03d' %(workingdir,selclass,volcounter+1),apix/lowpass)

			o1.write('vol%03d_fq.spi\t%s\n' %(volcounter+1,str(apix/float(fsc))))

			volcounter=volcounter+1

		counter = counter +1

#=============================
def calcFSC_filter(vol,evenvol,oddvol,lowpass):
	#print 'CalcFSC lowpass=%s' %(str(lowpass))
	if float(lowpass) == 1:
		#print 'Lowpass is equal to 1'
		#Calculate FSC curve using SPIDER
		spi='RF 3\n'
		spi+='%s\n' %(evenvol)
		spi+='%s\n' %(oddvol)
		spi+='(1.0)\n'
		spi+='(0.5,1.5)\n'
		spi+='C\n'
		spi+='(90.0)\n'
		spi+='(3.0)\n'
		spi+='%s_dres\n' %(vol)
		runSpider(spi)

		res=findFSC_eq_to_pt5('%s_dres.spi' %(vol))

	if float(lowpass) < 1:
		#print 'Low pass < 1'
		res=lowpass

	#Filter volume
	spi='FQ\n'
	spi+='%s\n' %(vol)
	spi+='%s_fq\n' %(vol)
	spi+='(7)\n'
	spi+='(%s),(%s)\n' %(float(res)-0.01,float(res)+0.01)
	runSpider(spi)

	return res

#===============================
def findFSC_eq_to_pt5(dres):

	resolution=0
	f1 = open(dres,'r')

	for line in f1:

		if line[1] == ';':
			continue
		#print line
		freq=line.split()[2]
		fsc=line.split()[4]
		if float(fsc) < 0.5:
			if resolution == 0:
				resolution=freq
				#print 'found freq ==> %f' %(float(freq))
	return resolution

#==============================
def refine3D(workingdir,eulers,inputvol,outputvol,radius,rotShift,stack,apix):

	numParts=getNumberOfLines('%s.spi'% (workingdir))
	shiftThresh=round(radius*0.3)

	spi='PJ 3Q\n'
	spi+='%s\n' %(inputvol)
	spi+='%s\n' %(str(radius))
	spi+='%s\n' %(workingdir)
	spi+='%s\n' %(eulers[:-4])
	spi+='%s_proj@******\n' %(inputvol)
	spi+='SD IC NEW\n'
	spi+='incore_shifts\n'
	spi+='2,%s\n' %(str(numParts))
	spi+='do lb1 [part]=1,%s\n' %(str(numParts))
	spi+='UD IC [part] [sel]\n'
	spi+='%s\n' %(workingdir)
	if rotShift != 'blank':
		#spi+='UD IC [part] [sx] [sy]\n'
		#spi+='%s_rotShift\n' %(inputvol[:-3])
		#spi+='SH\n'
		#spi+='%s@{*******[sel]}\n' %(stack[:-4])
		#spi+='_5\n'
		#spi+='-[sx],-[sy]\n'
		spi+='CP\n'
                spi+='%s@{*******[sel]}\n' %(stack[:-4])
                spi+='_5\n'
	if rotShift == 'blank':
		spi+='CP\n'
		spi+='%s@{*******[sel]}\n' %(stack[:-4])
		spi+='_5\n'
	spi+='CC N\n'
	spi+='_5\n'
	spi+='%s_proj@{******[sel]}\n' %(inputvol)
	spi+='_3\n'
	spi+='PK [xi] [yi]\n'
	spi+='_3\n'
	spi+='(1,0)\n'
	#if rotShift != 'blank':
	#	spi+='[newx]=[sx]+[xi]\n'
	#	spi+='[newy]=[sy]+[yi]\n'
	#	spi+='IF([newx].GT.%i) THEN\n'%(shiftThresh)
	#	spi+='[newx]=[xi]\n'
	#	spi+='[newy]=[yi]\n'
	#	spi+='ENDIF\n'
	#	spi+='IF([newx].LT.-%i) THEN\n'%(shiftThresh)
	#	spi+='[newx]=[xi]\n'
	#	spi+='[newy]=[yi]\n'
	#	spi+='ENDIF\n'
	#	spi+='IF([newy].GT.%i) THEN\n'%(shiftThresh)
	#	spi+='[newy]=[yi]\n'
	#	spi+='[newx]=[xi]\n'
	#	spi+='ENDIF\n'
	#	spi+='IF([newy].LT.-%i) THEN\n'%(shiftThresh)
	#	spi+='[newy]=[yi]\n'
	#	spi+='[newx]=[xi]\n'	
	#	spi+='ENDIF\n'
	#if rotShift == 'blank':
	spi+='[newx]=[xi]\n'
	spi+='[newy]=[yi]\n'
	spi+='IF([newx].GT.%i) THEN\n'%(shiftThresh)
	spi+='[newx]=0\n'
	spi+='[newy]=0\n'
	spi+='ENDIF\n'
	spi+='IF([newx].LT.-%i) THEN\n'%(shiftThresh)
	spi+='[newx]=0\n'
	spi+='[newy]=0\n'
	spi+='ENDIF\n'
	spi+='IF([newy].GT.%i) THEN\n'%(shiftThresh)
	spi+='[newy]=0\n'
	spi+='[newx]=0\n'
	spi+='ENDIF\n'
	spi+='IF([newy].LT.-%i) THEN\n'%(shiftThresh)
	spi+='[newy]=0\n'
	spi+='[newx]=0\n'
	spi+='ENDIF\n'
	spi+='SH\n'
	#if rotShift != 'blank':
	#	spi+='%s_parts_shifted@{*******[sel]}\n' %(inputvol[:-3])
		#spi+='%s_parts_shifted@{*******[sel]}\n' %(outputvol)
	#if rotShift == 'blank':
	spi+='%s@{*******[sel]}\n' %(stack[:-4])
	spi+='%s_parts_shifted@{*******[sel]}\n' %(outputvol)
	spi+='-[newx],-[newy]\n'
	spi+='SD IC [part] [newx] [newy]\n'
	spi+='incore_shifts\n'
	spi+='lb1\n'
	spi+='SD IC COPY\n'
	spi+='incore_shifts\n'
	spi+='%s_rotShift\n' %(outputvol)
	spi+='BP 32F\n'
	spi+='%s_parts_shifted@*******\n' %(outputvol)
	spi+='%s\n' %(workingdir)
	spi+='%s\n' %(eulers[:-4])
	spi+='*\n'
	spi+='%s\n' %(outputvol)
	spi+='%s/vol1%s\n'%(outputvol[:(len(outputvol))-6],outputvol[(len(outputvol))-3:])
	spi+='%s/vol2%s\n'%(outputvol[:(len(outputvol))-6],outputvol[(len(outputvol))-3:])
	runSpider(spi)

#==============================
def reconstruct(stack,select,eulers,folder):

	spi='BP 32F\n'
	spi+='%s@*********\n' %(stack[:-4])
	spi+='%s\n' %(select[:-4])
	spi+='%s\n' %(eulers[:-4])
	spi+='*\n'
	spi+='%s/vol001\n' %(folder)
	spi+='%s/vol1001\n' %(folder)
	spi+='%s/vol2001\n' %(folder)
	runSpider(spi)

#===========================
def runSpider(lines):
	   spifile = "currentSpiderScript.spi"
	   if os.path.isfile(spifile):
			   os.remove(spifile)
	   spi=open(spifile,'w')
	   spi.write("MD\n")
	   spi.write("TR OFF\n")
	   spi.write("MD\n")
	   spi.write("VB OFF\n")
	   spi.write("MD\n")
	   spi.write("SET MP\n")
	   spi.write("(8)\n")
	   spi.write("\n")
	   spi.write(lines)

	   spi.write("\nEN D\n")
	   spi.close()
	   spicmd = "spider spi @currentSpiderScript"
	   spiout = subprocess.Popen(spicmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stderr.read()
	   output = spiout.strip().split()
	   if "ERROR" in output:
			   print "Spider Error, check 'currentSpiderScript.spi'\n"
			   sys.exit()
	   # clean up
	   os.remove(spifile)
	   if os.path.isfile("LOG.spi"):
			   os.remove("LOG.spi")
	   resultf = glob.glob("results.spi.*")
	   if resultf:
			   for f in resultf:
					   os.remove(f)

#==============================
def getAPSHFile(outputfolder):

	lists=glob.glob('%s/*apsh.spi'%(outputfolder))
	if len(lists)>1:
		print 'Error: more than one file containing the string apsh.spi in %s folder. Exiting'(outputfolder)
		sys.exit()
	if len(lists) == 0:
		print 'Error: there are no files containing the string apsh.spi in %s folder. Exiting'(outputfolder)
		sys.exit()
	for o1 in lists:
		apshfile=o1
	return apshfile

#==============================
if __name__ == "__main__":

	#Imagic directory
	getEMANPath()
	params=setupParserOptions()
	checkConflicts(params)

	#Create output directory
	os.mkdir(params['folder'])

	#Get path to apsh file
	apshfile=getAPSHFile(params['inputfolder'])

	#Get basename of select files
	basename=glob.glob('%s/*_class*.spi' %(params['inputfolder']))[0][:-8]
	
	if params['debug'] is True:
		print '\nFound APSH file: %s\n' %(apshfile)

	#Get number of volumes to reconstruct
	numClasses=getNumberOfLines(params['selfile'])

	if params['debug'] is True:
		print '\nReconstructing %i classes\n' %(numClasses)

	iternum=params['inputfolder'].split('_')[-1]
	numflag=len(params['inputfolder'].split('_')[-1])

	if iternum[-1:] == '/':
		iternum=iternum[:-1]

	iternum=int(iternum)

	#Write spider euler angle file
	writeSpiderEulerAngles(apshfile,params['untiltinfo'],params['tiltinfo'],'%s/euler_angles.spi' %(params['folder']),params['angle'],params['debug'],iternum,params['inputfolder'],numflag,params['override'],params['numparts'])

	#Create a new spider stack with the 'untilted' and 'tilted' particles in alternative positions for the reconstruction
	#if params['cont'] is False:
	
	if params['lptilt']>0 or params['hptilt']>0:

		if os.path.exists('tilt_tmp_stack.img'):
			os.remove('tilt_tmp_stack.img')
	
		if os.path.exists('tilt_tmp_stack.hed'):
                        os.remove('tilt_tmp_stack.hed')
	
		if params['lptilt']==0:
			lpcutoff=0
		if params['lptilt']>0:
			lpcutoff=params['apix']/params['lptilt']

		if params['hptilt']==0:
                        hpcutoff=2000
                if params['hptilt']>0:
                        hpcutoff=params['apix']/params['hptilt']

		cmd='e2proc2d.py %s tilt_tmp_stack.img --process=filter.lowpass.gauss:cutoff_freq=%s --process=filter.highpass.gauss:cutoff_freq=%s' %(params['stack'],lpcutoff,hpcutoff)
		if params['debug'] is True:
			print cmd
		subprocess.Popen(cmd,shell=True).wait()

		cmd='e2proc2d.py tilt_tmp_stack.img %s/tiltMateStack.spi --outtype spi' %(params['folder'])
        	if params['debug'] is True:
                	print cmd
        	subprocess.Popen(cmd,shell=True).wait()

		os.remove('tilt_tmp_stack.hed')
		os.remove('tilt_tmp_stack.img')

	if params['lptilt'] == 0 and params['hptilt']==0:
		cmd = 'e2proc2d.py %s %s/tiltMateStack.spi --outtype spi' %(params['stack'],params['folder'])
		if params['debug'] is True:
			print cmd
		subprocess.Popen(cmd,shell=True).wait()

	#Reconstruct and refine 3D volumes
	if params['filter'] == 0:
		lowpass=params['apix']
	if params['filter'] > 0:
		lowpass=params['filter']

	if params['debug'] is True:
		print 'basename=%s' %basename

	recontruct_volume_and_refine('%s/euler_angles.spi' %(params['folder']),'%s/tiltMateStack.spi' %(params['folder']),numClasses,params['folder'],params['debug'],params['apix'],params['radius'],'%s/rot_shifts' %(params['folder']),lowpass,params['selfile'],basename,params['inputfolder'])
