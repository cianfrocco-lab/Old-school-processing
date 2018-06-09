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
import shutil

#=========================
def setupParserOptions():
        parser = optparse.OptionParser()
        parser.set_usage("%prog -i <input micrograph> -t <template imagic stack> --apixMicro=[pixel size] --apixTemplate=[pixel size] --boxsize=[box] --diam=[particle diameter] --thresh=[threshold] --mirror --bin=<bin> --all='wildcard'")
        parser.add_option("--micros",dest="micros",type="string",metavar="STRING",
                help="Input file containing tilt pair names")
	parser.add_option("--binning", dest="binning", type="int",metavar="INT", default=4,
                help="Binning factor for picking (Default=4)")
	parser.add_option("--microdims", dest="microdims", type="int",metavar="INT", default=4096,
                help="Micrograph dimensions (Default=4096)")
	parser.add_option("--box", dest="box", type="int",metavar="INT",
                help="Specify output box size for particles in UNbinned micrograph.")        
	parser.add_option("--extract", action="store_true",dest="extract",default=False,
                help="Flag to extract particles into unbinned particle stacks")
	parser.add_option("--output", dest="outputbase", type="str",metavar="STRING",default='output_stack',
                help="OPTIONAL: If extracting particles, specify output base name of stacks (Default=output_stack).")
	parser.add_option("-d", action="store_true",dest="debug",default=False,
                help="debug")
        options,args = parser.parse_args()

        if len(args) > 0:
                parser.error("Unknown commandline options: " +str(args))

        if len(sys.argv) < 2:
                parser.print_help()
                sys.exit()
        params={}
        for i in parser.option_list:
                if isinstance(i.dest,str):
                        params[i.dest] = getattr(options,i.dest)
        return params

#=============================
def checkConflicts(params):
        if not os.path.exists(params['micros']):
                print "\nError: tilt pair file '%s' does not exist\n" % params['micros']
                sys.exit()
	
	if not os.path.exists('/home/xiexi2/TEMpro/Scripts/Tiltpicker_import_patched/ApTiltPicker_import.py'):
		if not os.path.exists('/labdata/allab/michaelc/tiltpicker//ApTiltPicker_import.py'):
			print "\nError: cannot find ApTiltPicker_import.py script in /usr/bin or /labdata/allab/michaelc/tiltpicker/. Exiting.\n"
			sys.exit()
		
	if not params['box']:
		print '\nError: No box size specified. Exiting.\n' 
		sys.exit()

	if os.path.exists('/home/xiexi2/TEMpro/Scripts/Tiltpicker_import_patched/ApTiltPicker_import.py'):
		aptiltpath='/home/xiexi2/TEMpro/Scripts/Tiltpicker_import_patched/ApTiltPicker_import.py'

	if os.path.exists('/labdata/allab/michaelc/tiltpicker//ApTiltPicker_import.py'):
		aptiltpath='/labdata/allab/michaelc/tiltpicker//ApTiltPicker_import.py'

	if params['extract'] is True:
		if os.path.exists('%s_tiltstack.img' %(params['outputbase'])):
			print "\nError: Output stack %s_tiltstack.img already exists. Exiting.\n" %(params['outputbase'])
			sys.exit()

		if os.path.exists('%s_untiltstack.img' %(params['outputbase'])):
			print "\nError: Output stack %s_untiltstack.img already exists. Exiting.\n" %(params['outputbase'])
			sys.exit()

	return aptiltpath
#==============================
def runTiltPicker(params,aptiltpath):

	#get number of lines in input file
	totlines=len(open(params['micros']).readlines())

	if params['debug'] is True:
		print "Number of tilt mates: %i\n" %(totlines)

	#Loop over all tilt pairs: 
	i=1
	while i<=totlines:
		#Get micrographs		
		untiltmicro=linecache.getline(params['micros'],i).split()[0]
		tiltmicro=linecache.getline(params['micros'],i).split()[1]

		if params['debug'] is True:
			print 'Untilted micrograph: %s\n' %(untiltmicro)
			print 'Tilted micrograph: %s\n' %(tiltmicro)

		#Check that box files exist
		if not os.path.exists('%s.box' %(untiltmicro[:-4])):
			print 'Micrograph %s does not have a box file (%s.box)' %(untiltmicro,untiltmicro[:-4])
			i=i+1
			continue

		if not os.path.exists('%s.box' %(tiltmicro[:-4])):
			print 'Micrograph %s does not have a box file (%s.box)' %(tiltmicro,tiltmicro[:-4])
			i=i+1
			continue
		
		#Check if temp files exist. If so, remove.
		untiltbox='%s_temp_bin.box' %(untiltmicro[:-4])
		tiltbox='%s_temp_bin.box' %(tiltmicro[:-4])
		if os.path.exists(untiltbox):
			os.remove(untiltbox)
		if os.path.exists(tiltbox):
			os.remove(tiltbox)
		if os.path.exists('%s_temp_bin.mrc' %(untiltmicro[:-4])):
			os.remove('%s_temp_bin.mrc' %(untiltmicro[:-4]))
		if os.path.exists('%s_temp_bin.mrc' %(tiltmicro[:-4])):
			os.remove('%s_temp_bin.mrc' %(tiltmicro[:-4]))
		if os.path.exists('%s.spi' %(tiltbox[:-4])):
			os.remove('%s.spi' %(tiltbox[:-4]))
		if os.path.exists('%s.spi' %(untiltbox[:-4])):
			os.remove('%s.spi' %(untiltbox[:-4]))
		if os.path.exists('%s_temp_aptiltout.spi' %(untiltmicro[:-4])):
			os.remove('%s_temp_aptiltout.spi' %(untiltmicro[:-4]))

		MultiFactor=1/float(params['binning'])
		if params['debug'] is True:
			print 'Scaling factor = %f' %(MultiFactor)

		if os.path.exists('%s_tiltPicked.box' %(tiltmicro[:-4])):
                	print 'Tilted micrograph %s has already been processed. Skipping these tilt mates.'%(tiltmicro)
			i = i + 1
			continue

		if os.path.exists('%s_tiltPicked.box' %(untiltmicro[:-4])):
			print 'Untilted micrograph %s has already been picked and aligned. Skipping these tilt mates.' %(untiltmicro)
                        i = i + 1
                        continue

		#Bin micrographs & box files
		boxFileManipulator('%s.box' %(untiltmicro[:-4]),MultiFactor,untiltbox)
		boxFileManipulator('%s.box' %(tiltmicro[:-4]),MultiFactor,tiltbox)
		
		cmd='e2proc2d.py %s %s_temp_bin.mrc --meanshrink=%i' %(untiltmicro,untiltmicro[:-4],params['binning'])
		if params['debug'] is True:
			print cmd
		subprocess.Popen(cmd,shell=True).wait()

		cmd='e2proc2d.py %s %s_temp_bin.mrc --meanshrink=%i' %(tiltmicro,tiltmicro[:-4],params['binning'])
		if params['debug'] is True:
			print cmd
		subprocess.Popen(cmd,shell=True).wait()

		#Convert binned box files to spider coords for apTiltPicker
		boxToSpi_twocol(untiltbox,'%s.spi' %(untiltbox[:-4]))
		boxToSpi_twocol(tiltbox,'%s.spi' %(tiltbox[:-4]))

		#Launch ApTiltPicker: 
		cmd='%s -l %s_temp_bin.mrc -r %s_temp_bin.mrc --picks1=%s.spi --picks2=%s.spi --output=%s_temp_aptiltout.spi' %(aptiltpath,untiltmicro[:-4],tiltmicro[:-4],untiltbox[:-4],tiltbox[:-4],untiltmicro[:-4])
		if params['debug'] is True:
			print cmd
		subprocess.Popen(cmd,shell=True).wait()

		if not os.path.exists('%s_temp_aptiltout.spi' %(untiltmicro[:-4])):
			print 'No particle picks for %s and %s. Continuing on to next micrograph.' %(untiltmicro,tiltmicro)
			print '%s.box' %(untiltmicro[:-4])
			shutil.move('%s.box'%(untiltmicro[:-4]),'%s_noMatch.box' %(untiltmicro[:-4]))
                        shutil.move('%s.box'%(tiltmicro[:-4]),'%s_noMatch.box' %(tiltmicro[:-4]))

			i = i + 1
			continue

		if len(open('%s_temp_aptiltout.spi'%(untiltmicro[:-4]),'r').readlines()) < 40:
			print 'There were only %i particle picks for %s and %s tiltmates, no coordinates will be written. Continuing onto next micrograph.' %((len(open('%s_temp_aptiltout.spi' %(untiltmicro[:-4]),'r').readlines())-24)/2,untiltmicro,tiltmicro)
			shutil.move('%s.box'%(untiltmicro[:-4]),'%s_noMatch.box' %(untiltmicro[:-4]))
			shutil.move('%s.box'%(tiltmicro[:-4]),'%s_noMatch.box' %(tiltmicro[:-4]))
			i = i + 1
			continue

		#Parse aptilt output spider file
		parseApTilt('%s_temp_aptiltout.spi' %(untiltmicro[:-4]),params['box'],params['binning'],'%s_tiltPicked.box' %(untiltmicro[:-4]),'%s_tiltPicked.box' %(tiltmicro[:-4]),params['microdims'],params['debug'])	

		if params['extract'] is True:
			print 'Extracting particles from %s into %s_untiltstack.img' %(untiltmicro,params['outputbase'])
	
			cmd='batchboxer input=%s dbbox=%s_tiltPicked.box newsize=%i output=%s_untiltstack.img' %(untiltmicro,untiltmicro[:-4],params['box'],params['outputbase'])
			if params['debug'] is True:
				print cmd
			subprocess.Popen(cmd,shell=True).wait()

			print 'Extracting particles from %s into %s_tiltstack.img' %(tiltmicro,params['outputbase'])
			cmd='batchboxer input=%s dbbox=%s_tiltPicked.box newsize=%i output=%s_tiltstack.img' %(tiltmicro,tiltmicro[:-4],params['box'],params['outputbase'])
			if params['debug'] is True:
				print cmd
			subprocess.Popen(cmd,shell=True).wait()

		#Clean up
		os.remove(untiltbox)
		os.remove(tiltbox)
		#os.remove('%s_temp_bin.mrc' %(tiltmicro[:-4]))
		#os.remove('%s_temp_bin.mrc' %(untiltmicro[:-4]))
		#os.remove('%s.spi' %(tiltbox[:-4]))
		#os.remove('%s.spi' %(untiltbox[:-4]))
		#if params['debug'] is False:
		#	os.remove('temp_aptiltout.spi')
		#if params['debug'] is True:
			#shutil.move('temp_aptiltout.spi','%s_temp_aptiltout.spi' %(untiltmicro[:-4]))
		i = i + 1

#===============================
def parseApTilt(aptilt,box,binning,untiltout,tiltout,microdims,debug):

	f=aptilt
	f1 = open(aptilt,'r')
	tot = len(f1.readlines())
	f1.close()

	if debug is True:
		print 'There are %i lines in this file' %(tot)

	#Get number of lines in header
	i =1
	while i <= tot:
		testline=linecache.getline(f,i)
		if len(testline.split()) > 2:
			if debug is True:
				print testline.split()
			if testline.split()[1] == 'LEFT':
				if debug is True:
					print '----------------> %s' %(testline.split()[1])
				leftmicrostarts=i
                        if testline.split()[1] == 'RIGHT':
                                if debug is True:
					print '----------------> %s' %(testline.split()[1])
				rightmicrostarts=i
		i = i + 1

	numParts=linecache.getline(f,rightmicrostarts-1).split()[0]
	if debug is True:
		print 'Number of particles: %s' %(numParts)

	leftmicro=linecache.getline(f,leftmicrostarts).split()[4]
	if debug is True:
		print 'Left: %s' %(leftmicro)
	rightmicro=linecache.getline(f,rightmicrostarts).split()[4]
	if debug is True:
		print 'Right: %s' %(rightmicro)

	i=1

	o1=open(untiltout,'w')
	o2=open(tiltout,'w')

	while i<=float(numParts):

		part=i+leftmicrostarts

		if debug is True:
			print 'Working on particle %i' %(part)
			print linecache.getline(f,part)

		leftx=int(round(float(linecache.getline(f,part).split()[5])))*binning
		lefty=int(round(float(linecache.getline(f,part).split()[6])))*binning

		if leftx-(box)/2-2 <= 0 or lefty-(box)/2-1 <= 0:
			print 'Particle %i in %s is outside of the boundaries (<0): %i,%i' %(i,leftmicro,leftx-(box)/2-1,lefty-(box)/2-1)
			i = i + 1
			continue

		if leftx+(box)/2+2 >= microdims or lefty+(box)/2+1 >= microdims:
			print 'Particle %i in %s is outside of the boundaries (>%i): %i,%i' %(i,leftmicro,microdims,leftx+(box)/2+1,lefty+(box)/2+1)
			i = i + 1
			continue

		part2=i+rightmicrostarts
		if debug is True:
			print 'Working on particle %i' %(part2)
			print linecache.getline(f,part2)

		rightx=int(round(float(linecache.getline(f,part2).split()[5])))*binning
		righty=int(round(float(linecache.getline(f,part2).split()[6])))*binning

		if debug is True:
			print linecache.getline(f,part2)
			print rightx
			print righty
			print rightx-(box)/2
			print righty-(box)/2
		if rightx-(box)/2-2 <= 0 or righty-(box)/2-1 < 0:
	       		print 'Particle %i in %s is outside of the boundaries (<0): %i,%i' %(i,rightmicro,rightx-(box)/2-1,righty-(box)/2-1)
	        	i = i + 1
			continue

		if rightx+(box)/2+2 >= microdims or righty+(box)/2+1 >= microdims:
	        	print 'Particle %i in %s is outside of the boundaries (>%i): %i,%i' %(i,rightmicro,microdims,rightx+(box)/2+1,righty+(box)/2+1)
	        	i = i + 1
			continue

		o1.write('%i\t%i\t%i\t%i\n' %((leftx-(box/2),lefty-(box/2),box,box)))
		o2.write('%i\t%i\t%i\t%i\n' %((rightx-(box/2),righty-(box/2),box,box)))
		i = i + 1

#===============================
def boxToSpi_twocol(box,out):

	o1=open(out,'w')
	b1=open(box,'r')

	boxsize=int(linecache.getline(box,1).split()[2])

	for line in b1: 
		o1.write('%i\t%i\n' %(int(line.split()[0])+(boxsize/2),int(line.split()[1])+(boxsize/2)))
	
	o1.close()
	b1.close()

#===============================
def boxFileManipulator(box,factor,outfile):

	b1=open(box,'r')
	o1=open(outfile,'w')

	for line in b1:
		o1.write('%i\t%i\t%i\t%i\n' %(int(int(line.split()[0])*factor),int(int(line.split()[1])*factor),int(int(line.split()[2])*factor),int(int(line.split()[3])*factor)))
		
	o1.close()
	b1.close()

#========================
def getEMANPath():
        ### get the eman2 directory        
        emanpath = subprocess.Popen("env | grep EMAN2DIR", shell=True, stdout=subprocess.PIPE).stdout.read().strip()        

        if emanpath:
                emanpath = emanpath.replace("EMAN2DIR=","")
        if os.path.exists(emanpath):
                return emanpath
        print "EMAN2 was not found, make sure eman2 is in your path"
        sys.exit()

#==============================
if __name__ == "__main__":

        params=setupParserOptions()
        aptiltpath=checkConflicts(params)
	getEMANPath()
	runTiltPicker(params,aptiltpath)

