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
        parser.add_option("-i",dest="input",type="string",metavar="FILE",
                help="Micrograph name")
        parser.add_option("-t",dest="template",type="string",metavar="FILE",
                help="Stack of particles for template (.img)")
        parser.add_option("--apixMicro",dest="apixMicro",type="float", metavar="float",
                help="Pixel size of micrograph")
	parser.add_option("--apixTemplate",dest="apixTemplate",type="float", metavar="float",
                help="Pixel size of templates")
	parser.add_option("--boxsize",dest="boxsize",type="int", metavar="int",
                help="Box size of templates")
	parser.add_option("--diam",dest="diameter",type="int", metavar="INT",
                help="Particle diameter (Angstroms)")
	parser.add_option("--thresh",dest="thresh",type="float", metavar="float",
                help="Threshold for particle selection (0 - 1)")
	parser.add_option("--mirror", action="store_true",dest="mirror",default=False,
                help="Flag to mirror input references")
	parser.add_option("--binning", dest="binning", type="int",metavar="INT", default=4,
                help="Binning factor for picking (Default=4)")
	parser.add_option("--all", dest='all',type="str",metavar="STRING", default=False,
                help="Include wildcard within quotes to loop over all micrographs with that wildcard (e.g. '*en.mrc')")
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
        if not params['all']:
		if not os.path.exists(params['input']):
                	print "\nError: micrograph file '%s' does not exist\n" % params['input']
                	sys.exit()
        if params['template'][-4:] != '.img':
        	print 'Template stack extension %s is not recognized as a .img file' %(params['template'][-4:])
                sys.exit()

#=============================
def singleMicrograph(micro,apixM,lcf,diam,boxsize,binning,allfiles):

	#Remove existing temporary files
	if os.path.exists('micro.dwn.mrc'):
		os.remove('micro.dwn.mrc')
	if os.path.exists('micro.dwn2.mrc'):
                os.remove('micro.dwn2.mrc')
	if os.path.exists('picks.ems'):
		shutil.rmtree('picks.ems')
	if os.path.exists('outlog.log'):
		os.remove('outlog.log')

	#Normalize micrograph
	cmd = 'proc2d %s micro.dwn2.mrc norm=0,1'%(micro)
	if params['debug'] is True:
                print cmd
        subprocess.Popen(cmd,shell=True).wait()
	
	#Downsize input micrograph 
	cmd = 'proc2d micro.dwn2.mrc micro.dwn.mrc meanshrink=%s' %(str(binning))
	if params['debug'] is True:
		print cmd
	subprocess.Popen(cmd,shell=True).wait()

	#Run Signature
	cmd = 'signature -c -film img -space picks -source micro.dwn.mrc -template template.dwn.mrc -pixelsize %f -partsize %i -margin 10 -lcf-thresh %f -partdist 2 -resize 4 > outlog.log' %(apixM,int(diam),lcf)
	if params['debug'] is True:
                print cmd
	subprocess.Popen(cmd,shell=True).wait()

	#Convert spider picks into .box file
	if not os.path.exists('picks.ems/particles/img.spd'):
		print 'No particle picks for %s' %(micro)

	if os.path.exists('picks.ems/particles/img.spd'):
		convertSPD_to_BOX('picks.ems/particles/img.spd',micro,boxsize,binning)
		numparts = len(open('%s.box' %(micro[:-4]),'r').readlines())
		print '\n%i particles picked in micrograph: %s\n' %(numparts,micro)
	
	#Clean up
	if os.path.exists('micro.dwn.mrc'):
                os.remove('micro.dwn.mrc')
	if os.path.exists('micro.dwn2.mrc'):
                os.remove('micro.dwn2.mrc')
        if os.path.exists('picks.ems'):
                shutil.rmtree('picks.ems')
        if os.path.exists('outlog.log'):
                os.remove('outlog.log')

#==============================
def convertSPD_to_BOX(spd,micro,box,binning):
	
	f = open(spd,'r')
	if os.path.exists('%s.box' %(micro[:-4])):
                print "\nError: output box file already exists %s.box\n" %(micro[:-4])
                if params['all'] is True:
			return 
		if params['all'] is False: 
			sys.exit()

	o1 = open('%s.box'%(micro[:-4]),'w')

	for line in f:

		l = line.split()
		if l[0] == ';':
			continue

		x=int(float(l[2]))*binning-box/2
		y=int(float(l[3]))*binning-box/2

		o1.write('%i\t%i\t%i\t%i\n' %(x,y,box,box))

	f.close()
	o1.close()
	
#==============================
def prepRefs(params):

	#Prepare signature references 

	if os.path.exists('template.dwn.mrc'):
		os.remove('template.dwn.mrc')

	if os.path.exists('template.dwn.img'):
		os.remove('template.dwn.img')

	if os.path.exists('template.dwn.hed'):  
                os.remove('template.dwn.hed')
	
	if os.path.exists('template.dwn2.img'):
                os.remove('template.dwn2.img')

        if os.path.exists('template.dwn2.hed'):
                os.remove('template.dwn2.hed')

	scalingFactor = params['apixMicro']/params['apixTemplate']
	clipping = params['boxsize']/scalingFactor

	if params['debug'] is True:
		print 'Scaling factor = %f' %(1/scalingFactor)

        cmd = 'e2proc2d.py %s template.dwn.img --clip=%.0f,%.0f --scale=%f' %(params['template'],clipping,clipping,1/scalingFactor)
        if params['debug'] is True:
                print cmd
        subprocess.Popen(cmd,shell=True).wait()
	
	if params['mirror'] is True:
		cmd = 'proc2d template.dwn.img template.dwn.img flip'
		subprocess.Popen(cmd,shell=True).wait()

	cmd = 'e2proc2d.py template.dwn.img template.dwn2.img --meanshrink=%s' %(str(params['binning']))
	if params['debug'] is True:
                print cmd
        subprocess.Popen(cmd,shell=True).wait()
	
	#Convert to .mrc stack
	cmd = 'e2proc2d.py template.dwn2.img template.dwn.mrc --twod2threed'
	if params['debug'] is True:
                print cmd
        subprocess.Popen(cmd,shell=True).wait()
	
	#Clean up
	os.remove('template.dwn.img')
	os.remove('template.dwn.hed')
	os.remove('template.dwn2.img')
        os.remove('template.dwn2.hed')

#==============================
if __name__ == "__main__":

        params=setupParserOptions()
        checkConflicts(params)
	prepRefs(params)
	if params['all'] is False:
		#Analyzing a single micrograph only: micro,templates,apix,lcf
		singleMicrograph(params['input'],params['apixMicro'],params['thresh'],params['diameter']/4,params['boxsize'],params['binning'],params['all'])

	if params['all'] is not False:

		microlist = glob.glob(params['all'])	

		for micro in microlist: 

			if os.path.exists('%s.box' %(micro[:-4])):
				continue

			singleMicrograph(micro,params['apixMicro'],params['thresh'],params['diameter']/4,params['boxsize'],params['binning'],params['all'])
	#Clean up
	os.remove('template.dwn.mrc')
