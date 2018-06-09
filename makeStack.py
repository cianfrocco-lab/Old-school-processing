#!/usr/bin/env python

import shutil
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
        parser.set_usage("%prog --micros=<micrographs> --box=<boxfiles> -o <output stack name.img> ")
        parser.add_option("--micros",dest="micros",type="string",metavar="FILE",
                help="Path to micrographs with wildcard in quotes ('*en.mrc') (Not needed for tilt mates)")
	parser.add_option("-o",dest="stack",type="string",metavar="FILE",
                help="Output stack name (.img). If tilt mates, do not provide .img extension, output stack name will be the base name for tilted and untilted particles.")
	parser.add_option("--bin",dest="boxBin",type="int", metavar="INT",default=1,
                help="Binning factor used during boxer picking (Default=1)")
	parser.add_option("--invert", action="store_true",dest="invert",default=False,
                help="Optional: Invert contrast of micrographs")
	parser.add_option("--boxsize",dest="boxsize",type="int", metavar="INT",default=1,
                help="Optional: Box size for final stack. (Default is size used in boxer picking)")
	parser.add_option("--binstack",dest="stackbin",type="int", metavar="INT",default=1,
                help="Optional: Binning for final extracted particle stack. (Default=1)")
	parser.add_option("--phaseflip", action="store_true",dest="phaseFlip",default=False,
                help="Flag to phase flip particles")
        parser.add_option("--ctf",dest="ctf",type="string", metavar="STRING",
                help="If phase-flipping - ctf_param.txt output file from estimateCTF_CTFFIND.py if not using tilt mates")
	parser.add_option("--untilt",dest="untilt_info",type="string", metavar="STRING",
                help="If extracting tilt mates - provide CTFTILT output file for UNtilted micrographs created by estimateCTF_CTFTILT.py. Assumes extension is '01'.")
	parser.add_option("--tilt",dest="tilt_info",type="string", metavar="STRING",
                help="If extracting tilt mates - provide CTFTILT output file for TILTED micrographs created by estimateCTF_CTFTILT.py. Assumes extension is '00'.")
	parser.add_option("--noinsideonly", action="store_true",dest="noinsideonly",default=False,
                help="Flag to NOT exclude particles on edges of images (needed for tilt pairs)")
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
        if params['phaseFlip']:
		if not os.path.exists(params['ctf']):
                	print "\nError: ctf file '%s' does not exist\n" % params['ctf']
                	sys.exit()

        if not params['untilt_info']:
		if os.path.exists(params['stack']):
	                print "\nError: output stack already exists, exiting.\n"
	                sys.exit()

	if params['untilt_info']:
		if params['stack'][-4:] == '.img':
			print 'Output stack name has .img as extension. Remove extension and then rerun command.'
			sys.exit()
		if os.path.exists('%s_untilt.img' %(params['stack'])):
			print "\nError: output stack %s_untilt.img already exists. Exiting.\n" %(params['stack'])
			sys.exit()
		if os.path.exists('%s_tilt.img' %(params['stack'])):
			print "\nError: output stack %s_tilt.img already exists. Exiting.\n" %(params['stack'])
			sys.exit()
		if not os.path.exists(params['untilt_info']):
			print "\nError: Untilted CTFTILT info file %s does not exist. Exiting." %(params['untilt_info'])
			sys.exit()
		if not params['tilt_info']:
			print "\nError: No tilted micrograph information file specified. Exiting."
			sys.exit()
		if os.path.exists('%s_untilt_info.txt' %(params['stack'])):
			print "\nError: output stack %s_untilt_info.txt already exists. Exiting.\n" %(params['stack'])
			sys.exit()
		if os.path.exists('%s_tilt_info.txt' %(params['stack'])):
			print "\nError: output stack %s_tilt_info.txt already exists. Exiting.\n" %(params['stack'])
			sys.exit()

	if params['tilt_info']:
                if not os.path.exists(params['tilt_info']):
                        print "\nError: Tilted CTFTILT info file %s does not exist. Exiting." %(params['tilt_info'])
                        sys.exit()

		if not params['untilt_info']:
                        print "\nError: No untilted micrograph information file specified. Exiting."
                        sys.exit()


#==============================
def makeStack(params):

	microList = sorted(glob.glob(params['micros']))

	if len(microList) == 0:
		print "\nError: No micrographs in %s\n" (params['micros'])
		sys.exit()

	for micro in microList:

		#Find corresponding box file
		if os.path.exists('%s.box' %(micro[:-4])):

			if params['phaseFlip'] is True:
				print "\nPhase flipping %s.mrc\n" %(micro[:-4])
                        	microNew = phaseFlipMRC(params,'%s.mrc'%(micro[:-4]))
                	if params['phaseFlip'] is False:
                        	microNew = '%s.mrc'%(micro[:-4])

			print '\nBoxing %s using %s.box\n' %(microNew,micro[:-4])
			box = '%s.box' %(micro[:-4])

			if os.path.exists('tmp44.img'):
                                os.remove('tmp44.img')
				os.remove('tmp44.hed')

			if params['invert'] is True:
				cmd = 'e2proc2d.py %s %s_inv.mrc --mult=-1' %(micro,micro[:-4])
				subprocess.Popen(cmd,shell=True).wait()
				micro = '%s_inv.mrc' %(micro[:-4])

			if params['boxsize'] == 1:
				if params['noinsideonly'] is False:
					cmd = 'batchboxer input=%s dbbox=%s output=tmp44.img scale=%s insideonly'%(micro,box,str(params['boxBin']))
					subprocess.Popen(cmd,shell=True).wait()

				if params['noinsideonly'] is True:
                                        cmd = 'batchboxer input=%s dbbox=%s output=tmp44.img scale=%s'%(micro,box,str(params['boxBin']))
                                        subprocess.Popen(cmd,shell=True).wait()

			if params['boxsize'] > 1:
                                if params['noinsideonly'] is False:
					cmd = 'batchboxer input=%s dbbox=%s output=tmp44.img scale=%s insideonly newsize=%s insideonly'%(micro,box,str(params['boxBin']),str(params['boxsize']))
					subprocess.Popen(cmd,shell=True).wait()

				if params['noinsideonly'] is True:
					cmd = 'batchboxer input=%s dbbox=%s output=tmp44.img scale=%s insideonly newsize=%s '%(micro,box,str(params['boxBin']),str(params['boxsize']))
                                        subprocess.Popen(cmd,shell=True).wait()

			cmd='e2proc2d.py tmp44.img %s --meanshrink %i' %(params['stack'],params['stackbin'])
			if params['debug'] is True:
				print cmd
			subprocess.Popen(cmd,shell=True).wait()

			os.remove('tmp44.img')
			os.remove('tmp44.hed')
			os.remove('%s_flipped.mrc' %(micro[:-4]))

#==============================
def makeStack_tilt(params):

	#WRite out micrographs that don't have tilt mates into file only when debugging
	if params['debug'] is True:
		if os.path.exists('tmp_pairs.txt'):
			os.remove('tmp_pairs.txt')

	o1=open('tmp_pairs.txt','w')

	#Loop over micrographs within the untilted list:
	totlines=len(open(params['tilt_info'],'r').readlines())
	counter=2 #skip first line b/c it has ctftilt info in it.

	untilt_out=open('%s_untilt_info.txt' %(params['stack']),'a')
	tilt_out=open('%s_tilt_info.txt' %(params['stack']),'a')

	while counter <= totlines:

		tilt_microName = linecache.getline(params['tilt_info'],counter).split()[0].split('/')[-1]
		tilt_ang = linecache.getline(params['tilt_info'],counter).split()[5]
		tilt_axis = linecache.getline(params['tilt_info'],counter).split()[4]
		tilt_df1 = linecache.getline(params['tilt_info'],counter).split()[1]
		tilt_df2 = linecache.getline(params['tilt_info'],counter).split()[2]
		tilt_astig =linecache.getline(params['tilt_info'],counter).split()[3]

		if params['debug'] is True:
			print 'tilt_microName=%s' %(tilt_microName)
		path_to_micros = '/'.join(linecache.getline(params['tilt_info'],counter).split()[0].split('/')[:-1])
		if params['debug'] is True:
			print 'path_to_micros=%s' %(path_to_micros)

		#Find corresponding tilted .mrc file file
		if os.path.exists(tilt_microName):

			untilt_fullname,actualname=findTiltMate(tilt_microName,path_to_micros,params['debug'])

			if params['debug'] is True:
				print 'Tilt: %s  --> Untilt: %s\n' %(tilt_microName,untilt_fullname)

			if untilt_fullname is 'blank':
				print 'No untilted micro tilt name for %s' %(tilt_microName)
				if params['debug'] is True:
					o1.write('Tilt=%s\tUntilt=%s\n' %(tilt_microName,actualname))
				counter=counter+1
				continue

			untilt_microName=untilt_fullname.split('/')[-1]

			#Go get ctf info for untilted micrograph:
			untilt_df1,untilt_df2,untilt_astig,untilt_ang,untilt_axis=goGetCTF(untilt_microName,params['untilt_info'])

			if params['phaseFlip'] is True:
				print "\nPhase flipping untilted micrograph %s" %(untilt_microName)
                        	#untilt_microNew = '%s/%s' %(path_to_micros,untilt_microName)
				untilt_microNew = phaseFlipMRC_tilt(untilt_fullname,untilt_df1,untilt_df2,untilt_astig,params)

                	if params['phaseFlip'] is False:
                        	untilt_microNew = '%s/%s' %(path_to_micros,untilt_microName)

			tilt_microNew='%s/%s' %(path_to_micros,tilt_microName)

			#Check if box file exists:
			untilt_box='%s/%s_tiltPicked.box' %(path_to_micros,untilt_microName[:-4])
			tilt_box='%s_tiltPicked.box' %(tilt_microNew[:-4])
			if params['debug'] is True:
				print 'untilt_box=%s' %(untilt_box)
				print 'tilt_box=%s' %(tilt_box)

			if os.path.exists(untilt_box):
				if os.path.exists(tilt_box):
					#Check that they each have the same number of particles
					tot_untilt=len(open(untilt_box,'r').readlines())
					tot_tilt=len(open(tilt_box,'r').readlines())

					if tot_untilt != tot_tilt:
						print '%s does not have the same number of particles as %s. Skipping' %(untilt_box,tilt_box)
						counter=counter+1
						continue

					print '\nBoxing %s using %s\n' %(untilt_microName,untilt_box)
					print '\nBoxing %s using %s\n' %(tilt_microName,tilt_box)

					if params['boxsize'] == 1:
						if params['noinsideonly'] is False:
							cmd = 'batchboxer input=%s dbbox=%s output=%s_untilt.img scale=%s insideonly'%(untilt_microNew,untilt_box,params['stack'],str(params['boxBin']))
							subprocess.Popen(cmd,shell=True).wait()
							cmd = 'batchboxer input=%s dbbox=%s output=%s_tilt.img scale=%s insideonly'%(tilt_microNew,tilt_box,params['stack'],str(params['boxBin']))
							subprocess.Popen(cmd,shell=True).wait()

						if params['noinsideonly'] is True:
				                        cmd = 'batchboxer input=%s dbbox=%s output=%s_untilt.img scale=%s '%(untilt_microNew,untilt_box,params['stack'],str(params['boxBin']))
							subprocess.Popen(cmd,shell=True).wait()
							cmd = 'batchboxer input=%s dbbox=%s output=%s_tilt.img scale=%s '%(tilt_microNew,tilt_box,params['stack'],str(params['boxBin']))
							subprocess.Popen(cmd,shell=True).wait()

					if params['boxsize'] > 1:
				                if params['noinsideonly'] is False:
							cmd = 'batchboxer input=%s dbbox=%s output=%s_untilt.img scale=%s insideonly newsize=%s'%(untilt_microNew,untilt_box,params['stack'],str(params['boxBin']),str(params['boxsize']))
							subprocess.Popen(cmd,shell=True).wait()
							cmd = 'batchboxer input=%s dbbox=%s output=%s_tilt.img scale=%s insideonly newsize=%s'%(tilt_microNew,tilt_box,params['stack'],str(params['boxBin']),str(params['boxsize']))
							subprocess.Popen(cmd,shell=True).wait()


						if params['noinsideonly'] is True:
							cmd = 'batchboxer input=%s dbbox=%s output=%s_untilt.img scale=%s  newsize=%s'%(untilt_microNew,untilt_box,params['stack'],str(params['boxBin']),str(params['boxsize']))
							subprocess.Popen(cmd,shell=True).wait()
							cmd = 'batchboxer input=%s dbbox=%s output=%s_tilt.img scale=%s  newsize=%s'%(tilt_microNew,tilt_box,params['stack'],str(params['boxBin']),str(params['boxsize']))
							subprocess.Popen(cmd,shell=True).wait()

					#Write tilt info into files now.
					write_counter=1
					while write_counter <= tot_untilt:
						untilt_out.write('%s\t%s\t%s\t%s\t%s\n' %(untilt_df1,untilt_df2,untilt_astig,untilt_axis,untilt_ang))
						tilt_out.write('%s\t%s\t%s\t%s\t%s\n' %(tilt_df1,tilt_df2,tilt_astig,tilt_axis,tilt_ang))
						write_counter=write_counter+1
		counter=counter+1
#=============================
def findTiltMate(tilt,path,debug):
	maxv=10
	if tilt.split('hl')[1][1] is 'v':
		if debug is True:
			print 'Tilt=%s' %(tilt)
		#Rename and find untilt image with 'v' in it
		currentv=float(tilt.split('hl')[1][2:4])
		if debug is True:
			print currentv
		i=1
		actualuntilt=''

		while i<=maxv:

			nextv=currentv+i

			untiltChange = path+'/'+tilt.split('hl')[0]+'hl'+'_'+'v'+'%02i'%(nextv)+'_'+tilt.split('hl')[1][5:][:-6]+'01.mrc'
			if debug is True:
				print untiltChange
			if os.path.exists(untiltChange):
				actualuntilt=untiltChange

			i = i + 1
		if debug is True:
			print 'Untilt=%s' %(actualuntilt)

	if tilt.split('hl')[1][1] is not 'v':
		if debug is True:
			print 'Tilt=%s' %(tilt)
			print 'NOT V'

		untiltChange = path+'/'+tilt.split('hl')[0]+'hl'+'_'+'01'+'_'+tilt.split('hl')[1][4:][:-6]+'01.mrc'
		if debug is True:
			print 'UntiltChange=%s' %(untiltChange)
		actualuntilt=''
		if os.path.exists(untiltChange):
			actualuntilt=untiltChange
			if debug is True:
				print 'Untilt=%s' %(actualuntilt)

		if not os.path.exists(untiltChange):

			#Check for v's

			i=1
			while i<=maxv:

				untiltChange = path+'/'+tilt.split('hl')[0]+'hl'+'_'+'v'+'%02i'%(i)+'_'+tilt.split('hl')[1][4:][:-6]+'01.mrc'

				if os.path.exists(untiltChange):
					actualuntilt=untiltChange
				i=i+1

	if len(actualuntilt)>0:
		return actualuntilt,actualuntilt
	if len(actualuntilt)==0:
		return 'blank',actualuntilt

#=============================
def goGetCTF(micro,info_file):

	f1=open(info_file,'r')

	for line in f1:

		q_micro=line.split()[0].split('/')[-1]
		if q_micro == micro:
			df1=line.split()[1]
			df2=line.split()[2]
			astig=line.split()[3]
			axis=line.split()[4]
			angle=line.split()[5]

	f1.close()

	return df1,df2,astig,axis,angle

#=============================
def phaseFlipMRC(params,micro):

	#Convert to spider
	if os.path.exists('%s.spi' %(micro[:-4])):
		os.remove('%s.spi' %(micro[:-4]))
	cmd = 'e2proc2d.py %s %s.spi --outtype=spidersingle' %(micro,micro[:-4])
	subprocess.Popen(cmd,shell=True).wait()

	#Read in parameters: 6.2,120,2.15,0.15 #cs,ht,apix,ampcontrast

	paramline = linecache.getline(params['ctf'],1)
	lineparam = paramline.split(',')
	cs = lineparam[0]
	kev = lineparam[1]
	apix = lineparam[2]
	contrast = lineparam[3]

	#Get defocus
	df1,df2,astig = getCTFparam(params['ctf'],micro)

	if params['debug'] is True:
		print df1
		print df2
		print astig
		print micro

	df = (float(df1)+float(df2))/2

	#Write spider phase flip script
	ctfFile = createCTFfile(4096,df,apix,kev,cs,contrast)

	#Phase flip micrograph
	flippedMicro = phaseFlipMicro('%s.spi'%(micro[:-4]),ctfFile)

	#Convert back to mrc
	cmd = 'e2proc2d.py %s %s.mrc' %(flippedMicro,flippedMicro[:-4])
	subprocess.Popen(cmd,shell=True).wait()

	os.remove(flippedMicro)
	os.remove('%s.spi' %(micro[:-4]))

	return '%s.mrc' %(flippedMicro[:-4])

#=============================
def phaseFlipMRC_tilt(micro,df1,df2,astig,params):

	#Convert to spider
	if os.path.exists('%s.spi' %(micro[:-4])):
		os.remove('%s.spi' %(micro[:-4]))
	cmd = 'e2proc2d.py %s %s.spi --outtype=spidersingle' %(micro,micro[:-4])
	subprocess.Popen(cmd,shell=True).wait()

	#Read in parameters: 6.2,120,2.15,0.15 #cs,ht,apix,ampcontrast

	paramline = linecache.getline(params['ctf'],1)
	lineparam = paramline.split(',')
	cs = lineparam[0]
	kev = lineparam[1]
	apix = lineparam[2]
	contrast = lineparam[3]

	#Get defocus
	#df1,df2,astig = getCTFparam(params['ctf'],micro)

	df = (float(df1)+float(df2))/2

	#Write spider phase flip script
	ctfFile = createCTFfile(4096,df,apix,kev,cs,contrast)

	#Phase flip micrograph
	flippedMicro = phaseFlipMicro('%s.spi'%(micro[:-4]),ctfFile)

	#Convert back to mrc
	cmd = 'e2proc2d.py %s %s.mrc' %(flippedMicro,flippedMicro[:-4])
	subprocess.Popen(cmd,shell=True).wait()

	return '%s.mrc' %(flippedMicro[:-4])
#===========================
def phaseFlipMicro(micro,ctfFile):

	spi='FT\n'
	spi+='%s\n' %(micro[:-4])
	spi+='_1\n'
	spi+='MU\n'
	spi+='_1\n'
	spi+='%s\n' %(ctfFile[:-4])
	spi+='_2\n'
	spi+='*\n'
	spi+='FT\n'
	spi+='_2\n'
	spi+='%s_flipped\n'%(micro[:-4])
	runSpider(spi)

	flipped = os.path.abspath('%s_flipped.spi' %(micro[:-4]))

	return flipped

#============================
def getCTFparam(ctf,micro):

	ctflines = open(ctf,'r')

	for ctfline in ctflines:
		l2=ctfline.split()
		l = l2[0].split('/')[-1]
		if l == micro.split('/')[-1]:
			df1 = l2[1]
			df2 = l2[2]
			astig = l2[3]
	ctflines.close()

	return df1,df2,astig

#=============================
def createCTFfile(box,df,apix,kev,cs,contrast):

	if os.path.exists('ctf_tmp.spi'):
		os.remove('ctf_tmp.spi')

	spi=';____________ENTER__PARAMETERS__________________\n'
	spi+='X50=%f\n'%(float(cs))
	spi+='X51=%f\n'%((float(kev)*0.0336)/120)
	spi+='X52=%f\n'%(box)
	spi+='X53=%f\n' %(1/(2*float(apix)))
	spi+='X54=0.0047\n'
        spi+='X55=100\n'
	spi+='X58=%f\n' %(float(contrast))
	spi+='X59=0.15\n'
	spi+='X60=-1 ;-1 to keep the same contrast as input stack\n'
	spi+=';_______________________________________________\n'
	spi+='MD\n'
	spi+='SET MP\n'
	spi+='4\n'
        spi+='TF CT\n'
	spi+='ctf_tmp\n'
	spi+='X50             ; CS[mm]\n'
        spi+='X23,X51         ; defocus, lambda\n'
        spi+='X52             ; dimensions of output array (box size)\n'
        spi+='X53             ; max spatial freq\n'
        spi+='X54,X55         ; source size, defocus spread\n'
        spi+='0,0	      ; astigmatism correction\n'
        spi+='X58,x59         ; amp contrast\n'
        spi+='X60             ; sign\n'
	runSpider(spi)
	return 'ctf_tmp.spi'

#=============================
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
       spi.write("(0)\n")
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
if __name__ == "__main__":

        params=setupParserOptions()
        checkConflicts(params)
	if not params['untilt_info']:
		makeStack(params)
		#Normalize output stack
		cmd = 'e2proc2d.py %s %s_norm.img --process=normalize.edgemean' %(params['stack'],params['stack'][:-4])
		subprocess.Popen(cmd,shell=True).wait()
		os.remove('%s' %(params['stack']))
		os.remove('%s.hed' %(params['stack'][:-4]))

	if params['untilt_info']:
		makeStack_tilt(params)
		cmd = 'e2proc2d.py %s_tilt.img %s_tilt_norm.img --process=normalize.edgemean' %(params['stack'],params['stack'])
		subprocess.Popen(cmd,shell=True).wait()
		cmd = 'e2proc2d.py %s_untilt.img %s_untilt_norm.img --process=normalize.edgemean' %(params['stack'],params['stack'])
		subprocess.Popen(cmd,shell=True).wait()
		os.remove('%s_untilt.img' %(params['stack']))
		os.remove('%s_untilt.hed' %(params['stack']))
		os.remove('%s_tilt.img' %(params['stack']))
		os.remove('%s_tilt.hed' %(params['stack']))

	#Clean up
	flip = glob.glob('*flipped.*')

	for fli in flip:
		os.remove(fli)
