#!/usr/bin/env python

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
        parser.set_usage("%prog -v <volume> --thresh=<threshold> --dilate=<dilate>")
        parser.add_option("-v",dest="vol",type="string",metavar="FILE",
                help="Volume to be threshold-masked (.mrc or .spi)")
        parser.add_option("--thresh",dest="thresh",type="float", metavar="float",
                help="Value to threshold the map density to create mask. (Retrieved from Chimera's volume viewer histogram value when viewing struture)")
        parser.add_option("--dilate",dest="dilate",type="int", metavar="INT",default=4,
                help="Amount (in pixels) to expand the thresholded structure to create a shape mask. (Default=4)")
        parser.add_option("--savemask",action='store_true',dest="savemask",default=False,
                help="Flag to save mask generated during threshold & masking of input volume.")
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
    if params['vol'][-4:] != '.mrc':
                if params['vol'][-4:] != '.spi':
                	print 'Stack extension %s is not recognized as .spi .mrc file' %(params['vol'][-4:])
                        sys.exit()

    if os.path.exists('%s_thresh_masked%s' %(params['vol'][:-4],params['vol'][-4:])):
		print '\n Output file %s_thresh_masked%s already exists. Exiting.' %(params['vol'][:-4],params['vol'][-4:])
		sys.exit()

    if params['savemask'] is True:
        if os.path.exists('%s_thresh%s'%(params['vol'][:-4],params['vol'][-4:])):
            print '\nOutput file %s_thresh%s already exists. Exiting.'%(params['vol'][:-4],params['vol'][-4:])
            sys.exit()

#==============================
def spider_thresh_mask(vol,thresh,dilate,savemask):

    if savemask is True:
        if os.path.exists('threshmasktmp.spi'):
            os.remove('threshmasktmp.spi')

	spi='TH M\n'
	spi+='%s\n' %(vol[:-4])
	spi+='_1\n'
	spi+='B\n'
	spi+='%f\n' %(thresh)
	spi+='DI\n'
	spi+='_1\n'
	spi+='_2\n'
	spi+='B\n'
	spi+='%i\n'%(dilate)
	spi+='1\n'
	spi+='FQ\n'
	spi+='_2\n'
	spi+='_3\n'
	spi+='3\n'
	spi+='0.2\n'
	spi+='MU\n'
	spi+='%s\n' %(vol[:-4])
	spi+='_3\n'
	spi+='%s_masked\n' %(vol[:-4])
	spi+='*\n'
    if savemask is True:
        spi+='CP\n'
        spi+='_3\n'
        spi+='threshmasktmp\n'
        threshmask='threshmasktmp.spi'
    if savemask is False:
        threshmask='blank'
    runSpider(spi)

    return '%s_masked.spi' %(vol[:-4]),threshmask


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
       spi.write("0\n")
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

	#Remove tmp files
	if os.path.exists('tmp3D1.spi'):
		os.remove('tmp3D1.spi')

	#convert if .mrc
	if params['vol'][-4:] == '.mrc':
		cmd='e2proc3d.py %s tmp3D1.spi --outtype spidersingle' %(params['vol'])
		subprocess.Popen(cmd,shell=True).wait()

	if not os.path.exists('tmp3D1.spi'):
		cmd='e2proc3d.py %s tmp3D1.spi --outtype spidersingle' %(params['vol'])
                subprocess.Popen(cmd,shell=True).wait()

	#Threshold and mask
	masked,threshmask=spider_thresh_mask('tmp3D1.spi',params['thresh'],params['dilate'],params['savemask'])

	#Output intput type
	if params['vol'][-4:] == '.mrc':
		cmd='e2proc3d.py %s %s_thresh_masked%s' %(masked,params['vol'][:-4],params['vol'][-4:])
		subprocess.Popen(cmd,shell=True).wait()

        if params['savemask'] is True:
            if threshmask != 'blank':
                cmd='e2proc3d.py %s %s_thresh%s' %(threshmask,params['vol'][:-4],params['vol'][-4:])
                subprocess.Popen(cmd,shell=True).wait()

	if params['vol'][-4:] == '.spi':
		cmd='cp %s %s_thresh_masked%s' %(masked,params['vol'][:-4],params['vol'][-4:])
		subprocess.Popen(cmd,shell=True).wait()
        if params['savemask'] is True:
            if threshmask != 'blank':
                cmd='cp %s %s_thresh%s' %(threshmask,params['vol'][:-4],params['vol'][-4:])
                subprocess.Popen(cmd,shell=True).wait()

	#Clean up
	os.remove(masked)
	os.remove('tmp3D1.spi')
