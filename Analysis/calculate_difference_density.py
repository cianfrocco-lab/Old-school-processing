#!/usr/bin/env python 

#This script will calculate a difference density between two 2D images or two 3D models
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
import shutil

#=========================
def setupParserOptions():
        parser = optparse.OptionParser()
        parser.set_usage("%prog --input1=[input] --input2=[input] --type=2D/3D")
        parser.add_option("--input1",dest="input1",type="string",metavar="FILE",
                help="Image/Volume from which input2 will be subtracted. (2D or 3D input, .spi or .mrc format)")
        parser.add_option("--input2",dest="input2",type="string",metavar="FILE",
                help="Image/Volume that wil be subtracted from input1 econd input will be subtracted. (2D or 3D input, .spi or .mrc format)")
	parser.add_option("--type",dest="type",type="string",metavar="TYPE",
                help="Input type: 2D or 3D.")
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
        
	if not os.path.exists(params['input1']):
		print 'Input1 file %s does not exist. Exiting.\n' %(params['input1'])
		sys.exit()

	if not os.path.exists(params['input2']):
                print 'Input2 file %s does not exist. Exiting.\n' %(params['input2'])
                sys.exit()

        if params['input1'][-4:] != '.mrc':
                if params['input1'][-4:] != '.spi':
			print 'Input1 extension %s is not recognized as .spi .mrc' %(params['input1'][-4:])
                        sys.exit()
	if params['input2'][-4:] != '.mrc':
                if params['input2'][-4:] != '.spi':
                        print 'Input2 extension %s is not recognized as .spi .mrc' %(params['input2'][-4:])
                        sys.exit()

	if params['input1'][-4:] != params['input2'][-4:]:
		print 'Input1 (%s) and Input2 (%s) are not the same file type: %s vs. %s. Exiting.\n' %(params['input1'],params['input2'],params['input1'][-4:],params['input2'][-4:])
		sys.exit() 

        if os.path.exists('%s_minus_%s%s' %(params['input1'][:-4],params['input2'][:-4],params['input1'][-4:])):
                print "\nError: output difference density %s_minus_%s%s already exists. Exiting.\n" %(params['input1'][:-4],params['input2'][:-4],params['input1'][-4:])
                sys.exit()

	if params['type'] != '2D':
		if params['type'] != '3D':
			print "\nError: unknown image type %s provided. Not 2D or 3D. Exiting.\n"%(params['type'])
			sys.exit()

#==============================
def getEman2Path():
        eman2path = subprocess.Popen("env | grep EMAN2", shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        if not eman2path:
		print "EMAN2 was not found, make sure EMAN2 is loaded"
		sys.exit()
#=============================
def calculate_spider_difference(in1,in2,out):

	spi='FS  [max],[min],[avg],[std]\n' 
	spi+='in1\n' 
	spi+='AR\n'
	spi+='in1\n'
	spi+='in1_norm\n'
	spi+='(P1-[avg])/[std]\n'
	spi+='FS  [max],[min],[avg],[std]\n'
        spi+='in2\n'
        spi+='AR\n'
        spi+='in2\n'
        spi+='in2_norm\n'
        spi+='(P1-[avg])/[std]\n'
	spi+='SU\n'
	spi+='in1_norm\n'
	spi+='in2_norm\n'
	spi+='dif_out\n'
	spi+='*\n'
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

#=============================
def getBoxSize(inputfile):
	if os.path.exists('%s_tmpoutboxsize.spi'%(inputfile)):
		os.remove('%s_tmpoutboxsize.spi'%(inputfile))

	spi='SD IC NEW\n'
	spi+='incore\n'
	spi+='1,1\n'
	spi+='[one]=1\n'
	spi+='FI H [boxsize]\n'
	spi+='%s\n'%(inputfile)
	spi+='NX\n'
	spi+='[boxsize]\n'
	spi+='SD IC [one] [boxsize]\n'
	spi+='incore\n'
	spi+='SD IC COPY\n'
	spi+='incore\n'
	spi+='%s_tmpoutboxsize\n' %(inputfile)
	spi+='SD ICE\n'
	spi+='incore\n'
	runSpider(spi)

	boxsize=float(linecache.getline('%s_tmpoutboxsize.spi'%(inputfile),2).split()[2])
	os.remove('%s_tmpoutboxsize.spi'%(inputfile))
	return boxsize
#==============================
if __name__ == "__main__":

        params=setupParserOptions()
        checkConflicts(params)
	getEman2Path()
	#Check inputs: remove temporary working files
	if os.path.exists('in1.spi'):
                        os.remove('in1.spi')
	if os.path.exists('in2.spi'):
                        os.remove('in2.spi')
	if os.path.exists('in1_norm.spi'):
                        os.remove('in1_norm.spi')
        if os.path.exists('in2_norm.spi'):
                        os.remove('in2_norm.spi')
	if os.path.exists('dif_out.spi'):
                        os.remove('dif_out.spi')

	#Convert inputs
	if params['type'] == '2D':
		emanvar='e2proc2d.py'
	if params['type'] == '3D':
		emanvar='e2proc3d.py'
	if params['input1'][-4:] is '.mrc':
		cmd='%s %s in1.spi --outtype spidersingle'%(emanvar,params['input1'])
		subprocess.Popen(cmd,shell=True).wait()	
	if not os.path.exists('in1.spi'):
		cmd='%s %s in1.spi --outtype spidersingle'%(emanvar,params['input1'])
                subprocess.Popen(cmd,shell=True).wait()
	if params['input2'][-4:] is '.mrc':
                cmd='%s %s in2.spi --outtype spidersingle'%(emanvar,params['input2'])
                subprocess.Popen(cmd,shell=True).wait()
        if not os.path.exists('in2.spi'):
                cmd='%s %s in2.spi --outtype spidersingle' %(emanvar,params['input2'])
                subprocess.Popen(cmd,shell=True).wait()	

	#Calculate difference density using spider
	if getBoxSize('in1') != getBoxSize('in2'):
		print 'Input1 (%s) and Input (%s) have different box sizes. Exiting\n' %(params['input1'],params['input2'])
		os.remove('in1.spi')
		os.remove('in2.spi')
		sys.exit()

	calculate_spider_difference('in1.spi','in2.spi','dif_out.spi')

	#Output same type as input type
	if params['input1'][-4:] == '.mrc':
		cmd='%s dif_out.spi %s_minus_%s%s' %(emanvar,params['input1'][:-4],params['input2'][:-4],params['input1'][-4:])
		subprocess.Popen(cmd,shell=True).wait()

	if params['input1'][-4:] == '.spi':	
		shutil.move('dif_out.spi','%s_minus_%s%s' %(params['input1'][:-4],params['input2'][:-4],params['input1'][-4:]))

	#Clean up temporary files
	if params['debug'] is False:
		os.remove('in1.spi')
		os.remove('in2.spi')
		os.remove('in1_norm.spi')
                os.remove('in2_norm.spi')
		if os.path.exists('dif_out.spi'):
			os.remove('dif_out.spi')
