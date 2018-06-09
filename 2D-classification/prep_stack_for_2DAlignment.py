#!/usr/bin/env python 

#This script will filter an imagic stack and can apply a circular mask. 
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
        parser.set_usage("%prog -i <stack.img> --num=<number of particles in stack> --apix=<pixel size> --lp=<low pass> --hp=<high pass> --mask=<radius>")
        parser.add_option("-i",dest="stack",type="string",metavar="FILE",
                help="Particle stack in .img format")
        parser.add_option("--num",dest="numParts",type="int", metavar="INT",
                help="Number of particles in stack")
        parser.add_option("--apix",dest="apix",type="float", metavar="FLOAT",
                help="Pixel size")
	parser.add_option("--lp",dest="lp",default=0,type="int", metavar="INT",
                help="Low pass filter (Angstroms)")
	parser.add_option("--hp",dest="hp",default=5000,type="int", metavar="INT",
                help="High pass filter (Angstroms)")
	parser.add_option("--mask",dest="radius",type="int", metavar="INT",
                help="Soft mask radius (pixels)")
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
        if not os.path.exists(params['stack']):
                print "\nError: stack file '%s' does not exist\n" % params['stack']
                sys.exit()

        if os.path.exists('%s_prep.img' %(params['stack'][:-4])):
                print "\nError: output stack %s_prep.img already exists, exiting.\n" %(params['stack'][:-4])
                sys.exit()

#==============================
def filterStack(params):

	#Conver stack to spider format
	cmd = 'e2proc2d.py %s %s.spi --outtype=spi' %(params['stack'],params['stack'][:-4])
	if params['debug'] is True:
		print cmd
	subprocess.Popen(cmd,shell=True).wait()

	if not params['radius']:
		maskRadius = 0

	if params['radius']:
		maskRadius = params['radius']
	
	filter(params['stack'],params['apix'],params['lp'],params['hp'],params['numParts'],maskRadius)
	
	cmd = 'e2proc2d.py %s_prep.spi %s_prep.img' %(params['stack'][:-4],params['stack'][:-4])
	subprocess.Popen(cmd,shell=True).wait()

	os.remove('%s_prep.spi' %(params['stack'][:-4]))
	os.remove('%s.spi' %(params['stack'][:-4]))
#=============================
def filter(stack,apix,lp,hp,numParts,mask):

	lpPass=(apix/lp)-0.025
	lpStop=(apix/lp)+0.025
	
	if hp > 0:
		hpStop=(apix/hp)-0.0015
		hpPass=(apix/hp)+0.0015

	if hp == 0:
		hpStop=0
		hpPass=0.00002

	spi='do lb1 [part]=1,%f\n' %(numParts)
	spi+='FQ\n'
	spi+='%s@{*********[part]}\n' %(stack[:-4])
	spi+='_1\n'
	spi+='7\n'
	spi+='%f,%f\n' %(lpPass,lpStop)
	spi+='\n'
	spi+='FQ\n'
	spi+='_1\n'
	spi+='_2\n'
	spi+='8\n'
	spi+='%f,%f\n' %(hpStop,hpPass)
	if mask > 0:
		spi+='MA\n'
		spi+='_2\n'
		spi+='_3\n'
		spi+='%f,0\n' %(mask)
		spi+='G\n'
		spi+='E\n'
		spi+='0\n'
		spi+='*\n'
		spi+='2\n'
		spi+='DE\n'
		spi+='_2\n'
		spi+='CP\n'
		spi+='_3\n'
		spi+='_2\n'
	spi+='CP\n'
	spi+='_2\n'
	spi+='%s_prep@{********[part]}\n' %(stack[:-4])
	spi+='lb1\n'
	runSpider(spi)
	
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
       spi.write("(4)\n")
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
	filterStack(params)
