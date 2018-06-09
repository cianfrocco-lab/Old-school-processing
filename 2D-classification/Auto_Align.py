#!/usr/bin/env  python

#This script will using a topology representing network ('CAN') with Imagic, SPIDER, or EMAN to perform 2D 
#reference-free alignments. 
#
#TEM|pro - mcianfrocco

import tarfile
import random
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
#import multiprocessing #Only works with python2.6

#=========================
def setupParserOptions():
        parser = optparse.OptionParser()
        parser.set_usage("%prog -i <stack> -o <output folder for results> --num=[number of particles in stack] --iter=[num. of iterations] --start=[starting class number] --final=[final class number]")
        parser.add_option("-i",dest="stack",type="string",metavar="FILE",
                help="Particle stack (.img)")
        parser.add_option("-o",dest="folder",type="string",metavar="FILE",
                help="Output folder name for iterative alignment & classification")
        parser.add_option("--num",dest="numParts",type="int", metavar="INT",
                help="Number of particles in stack")
	parser.add_option("--iter",dest="iterations",type="int", metavar="INT",
                help="Number of iterations")
	parser.add_option("--start",dest="startClassNum",type="int", metavar="INT",
                help="Starting number of classes")
	parser.add_option("--final",dest="finalClassNum",type="int", metavar="INT",
                help="Final number of classes")
	parser.add_option("--maskradius",dest="maskradius",type="int", metavar="INT",
                help="Radius for masking particles")
	parser.add_option("--imagic", action="store_true",dest="imagic",default=False,
                help="Flag to use Imagic for MRA")
        parser.add_option("--eman", action="store_true",dest="eman",default=False,
                help="Flag to use EMAN for MRA")
	parser.add_option("--spider", action="store_true",dest="spider",default=False,
                help="Flag to use SPIDER for MRA")
	parser.add_option("--radius",dest="radius",type="int", metavar="INT",
                help="SPIDER input option: radius for searching (pixels)")
	parser.add_option("--nomirrors",action="store_true",dest="mirror",default=False,
                help="SPIDER input option: flag to NOT check mirrors  (for RCT)")
	parser.add_option("--keep", action="store_true",dest="keep",default=False,
                help="Flag to keep aligned stacks from iterative alignment")
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
        if os.path.exists(params['folder']):
                print "\nError: Output folder '%s' already exists. Exiting.\n" % params['folder']
                sys.exit()

	if not os.path.exists(params['stack']):
                print "\nError: Stack '%s' does not exist. Exiting.\n" % params['stack']
                sys.exit()

	if params['stack'][-4:] == '.spi':
		print "\nError: Input stack was SPIDER format (.spi). Imagic stack is required as input (.img/hed)\n"
		sys.exit()

	if os.path.exists('/usr/bin/CAN_linux.exe'):
                return '/usr/bin/CAN_linux.exe'

	pathToScript = sys.argv[0]
	CANpathTest = '%s/CAN_linux.exe' %(pathToScript[:-14])

	if os.path.exists(CANpathTest):
		return CANpathTest
	
	if os.path.exists('CAN_linux.exe'):
		return 'CAN_linux.exe'

	print "\nError: Cannot find 'CAN_linux.exe' in current directory or /usr/bin/. Exiting'\n"
	sys.exit()

#==============================
def getimagicPath():
        imagicpath = subprocess.Popen("env | grep IMAGIC_ROOT", shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        if imagicpath:
                imagicpath = imagicpath.split('=')
		return imagicpath[1]
        print "Imagic was not found, make sure Imagic is loaded"
        sys.exit()

#===============================
def numCPUs():
	cmd = 'cat /proc/cpuinfo |grep processor |wc'
	d = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	lines = d.stdout.readlines()
	lines = re.split('\s+', lines[0])
	number_of_procs = int(lines[1])

	return number_of_procs

#==============================
def getEman2Path():
        eman2path = subprocess.Popen("env | grep EMAN2", shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        if not eman2path:
		print "EMAN2 was not found, make sure EMAN2 is loaded"
		sys.exit()

#==============================
def getSPIDERPath():
        path = subprocess.Popen("env | grep spider", shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        if not path:
                path2 = subprocess.Popen("env | grep SPIDER", shell=True, stdout=subprocess.PIPE).stdout.read().strip()
			
		if not path2:
			print "SPIDER was not found, make sure SPIDER is loaded"
                	sys.exit()

#==============================
def runAutoAlign(params,imagicPath,canPath):

	#Get absoulte CAN path
	canpath = os.path.abspath(canPath)

	#Initialize counter
	counter = 1

	#CAN parameters
	numItersCan = params['numParts']*6
	decimatingNumber = (params['startClassNum']-params['finalClassNum'])/(params['iterations']-2)

	#Create first directory
	os.mkdir('%s' %(params['folder']))
	os.mkdir('%s/auto_iteration_1' %(params['folder']))

	#Copy stack into first directory & symbolically link it to current_mra.img
	shutil.copyfile(params['stack'],'%s/auto_iteration_1/mra0.img' %(params['folder']))
	shutil.copyfile('%s.hed' %(params['stack'][:-4]),'%s/auto_iteration_1/mra0.hed' %(params['folder']))	

	#Make symbolic link
	os.symlink('auto_iteration_1/mra0.hed','%s/current_mra.hed' %(params['folder']))
	os.symlink('auto_iteration_1/mra0.img','%s/current_mra.img' %(params['folder']))
	
	#Start looping
	while counter <= params['iterations']:

		if counter > 1:
			os.mkdir('%s/auto_iteration_%1d' %(params['folder'],counter))

		#Calculate number of nodes for CAN		
		nodes1 = decimatingNumber*counter
		nodes1 = nodes1-decimatingNumber
		nodes = params['startClassNum']-nodes1 

		#Run CAN
		cmd = '%s %s/current_mra %s/auto_iteration_%1d/classsums%1d %s 0.01 0.0005 25 %s > log.log' %(canPath,params['folder'],params['folder'],counter,counter,str(numItersCan),str(nodes))
		subprocess.Popen(cmd,shell=True).wait()	

		#Prepare references
		if params['imagic'] is True:
			pretreat('%s/auto_iteration_%1d/classsums%1d' %(params['folder'],counter,counter),imagicPath)
		if params['imagic'] is False:
			
			if params['debug'] is True:
				print 'Finished CAN - aligning references\n'
	
			#Use eman2 to align references (taken from appion topologyAlignment.py):
 			emancmd = "e2stacksort.py %s/auto_iteration_%1d/classsums%1d.img %s/auto_iteration_%1d/classsums%1d_prep.hdf --simalign=rotate_translate --center --useali --iterative" %(params['folder'],counter,counter,params['folder'],counter,counter)
			if params['debug'] is True:
				print emancmd 
			subprocess.Popen(emancmd,shell=True).wait()

			#Align avgs together
			#cmd = 'classalign2 %s/auto_iteration_%1d/classsums%1d.img 10 keep=100 saveali'%(params['folder'],counter,counter)
			#if params['debug'] is True:
			#	print cmd
			#subprocess.Popen(cmd,shell=True).wait()
			
			#sys.exit()
			#shutil.move('%s/auto_iteration_%1d/aclasssums%1d.img'%(params['folder'],counter,counter),'%s/auto_iteration_%1d/classsums%1d_prep.img'%(params['folder'],counter,counter))
			#shutil.move('%s/auto_iteration_%1d/aclasssums%1d.hed'%(params['folder'],counter,counter),'%s/auto_iteration_%1d/classsums%1d_prep.hed'%(params['folder'],counter,counter))			

			#Convert .hdf outputs into .img
			cmd = 'e2proc2d.py %s/auto_iteration_%1d/classsums%1d_prep.hdf %s/auto_iteration_%1d/classsums%1d_prep.img' %(params['folder'],counter,counter,params['folder'],counter,counter)
			if params['debug'] is True:
				print cmd
			subprocess.Popen(cmd,shell=True).wait()

			#Normalize class averages
			cmd = 'e2proc2d.py %s/auto_iteration_%1d/classsums%1d_prep.img %s/auto_iteration_%1d/classsums%1d_prep_norm.img --process=normalize.edgemean' %(params['folder'],counter,counter,params['folder'],counter,counter)
			subprocess.Popen(cmd,shell=True).wait()

		#Run MRA
		if params['imagic'] is True:
			mra('%s/current_mra' %(params['folder']),'%s/auto_iteration_%1d/mra%1d' %(params['folder'],counter,counter),'%s/auto_iteration_%1d/classsums%1d_center_prep_mask_norm' %(params['folder'],counter,counter),params['stack'][:-4],imagicPath)
		if params['eman'] is True:
			mra_eman('%s/auto_iteration_%1d/classsums%1d_prep_norm.img' %(params['folder'],counter,counter),'%s/current_mra.img'%(params['folder']),'%s/auto_iteration_%1d' %(params['folder'],counter),'%s/auto_iteration_%1d/mra%1d.img' %(params['folder'],counter,counter))		
		if params['spider'] is True:
			mra_spider('%s/auto_iteration_%1d/classsums%1d_prep_norm.img' %(params['folder'],counter,counter),'%s/current_mra.img'%(params['folder']),'%s/auto_iteration_%1d' %(params['folder'],counter),'%s/auto_iteration_%1d/mra%1d.img' %(params['folder'],counter,counter),nodes,params['numParts'],counter,'%s/auto_iteration_%1d/mra%1d_apsh.spi' %(params['folder'],counter-1,counter-1))

			shutil.move('%s/current_mra_apsh.spi' %(params['folder']),'%s/auto_iteration_%1d/mra%1d_apsh.spi' %(params['folder'],counter,counter))
			cmd = 'e2proc2d.py %s/current_mra_aligned.spi %s/auto_iteration_%1d/mra%1d.img' %(params['folder'],params['folder'],counter,counter)
			if params['debug'] is True:
				print cmd
			subprocess.Popen(cmd,shell=True).wait()
		#Finish iteration - remove symbolic linked current_mra & replace it with new MRA output

		#Mask references using spider
		if params['imagic'] is False:
			cmd = 'e2proc2d.py %s/auto_iteration_%1d/mra%1d.img %s/auto_iteration_%1d/mra%1d.spi --outtype=spi' %(params['folder'],counter,counter,params['folder'],counter,counter)
			subprocess.Popen(cmd,shell=True).wait()

			maskParticles('%s/auto_iteration_%1d/mra%1d.spi'%(params['folder'],counter,counter),params['numParts'],params['maskradius'])

			cmd = 'e2proc2d.py %s/auto_iteration_%1d/mra%1d_prep.spi %s/auto_iteration_%1d/mra%1d_prep.img' %(params['folder'],counter,counter,params['folder'],counter,counter)
			subprocess.Popen(cmd,shell=True).wait()
			os.remove('%s/auto_iteration_%1d/mra%1d_prep.spi'%(params['folder'],counter,counter))
			os.remove('%s/auto_iteration_%1d/mra%1d.spi'%(params['folder'],counter,counter))
		
		#Mask references using imagic
		if params['imagic'] is True:
			maskParticlesImagic('%s/auto_iteration_%1d/mra%1d.img' %(params['folder'],counter,counter),imagicPath)

		os.remove('%s/current_mra.hed'%(params['folder']))
		os.remove('%s/current_mra.img'%(params['folder']))
		if params['spider'] is True:
			os.remove('%s/current_mra.spi'%(params['folder']))
			os.remove('%s/current_mra_aligned.spi'%(params['folder']))	
		os.symlink('auto_iteration_%1d/mra%1d_prep.hed'%(counter,counter),'%s/current_mra.hed' %(params['folder']))
        	os.symlink('auto_iteration_%1d/mra%1d_prep.img'%(counter,counter),'%s/current_mra.img' %(params['folder']))	

		counter = counter + 1

#=====================
def maskParticlesImagic(stack,imagicPath):

	img='%s/incore/incprep.e <<EOF\n' %(imagicPath)
	img+='%s\n' %(stack[:-4])
	img+='%s_prep\n' %(stack[:-4])
	img+='0.015\n'
	img+='0.005\n'
	img+='0.8\n'
	img+='0.8,0.1\n'
	img+='NO\n'
	img+='EOF\n'
	runImagic(img)

#=====================
def maskParticles(stack,numParts,radius):

	spi='do lb1 [part]=1,%f\n' %(numParts)
	spi+='MA\n'
        spi+='%s@{********[part]}\n' %(stack[:-4])
        spi+='%s_prep@{********[part]}\n' %(stack[:-4])
        spi+='%f,0\n'%(radius)
        spi+='G\n'
        spi+='E\n'
        spi+='0\n'
        spi+='*\n'
        spi+='2\n'
	spi+='lb1\n'
	runSpider(spi)

#=====================
def mra_spider(refs,stack,folder,output,numRefs,numParts,iteration,previous):

	#Convert particle stack to spider stack
	cmd = 'e2proc2d.py %s %s.spi --outtype=spi' %(stack,stack[:-4])
	subprocess.Popen(cmd,shell=True).wait()

	#Convert references to spider stack
	cmd = 'e2proc2d.py %s %s.spi --outtype=spi' %(refs,refs[:-4])
	subprocess.Popen(cmd,shell=True).wait()

	if params['mirror'] is True:
		checkmirror = 'N'

	if params['mirror'] is False:
		checkmirror = 'Y'

	#Run AP SH
	apsh='AP SH\n'
	apsh+='%s@*****\n' %(refs[:-4])
	apsh+='1-%s\n' %(str(numRefs))
	apsh+='10,1\n' 
	apsh+='2,%s,1,1\n' %(str(params['radius']))
	apsh+='*\n'
	apsh+='%s@*********\n' %(stack[:-4])
	apsh+='1-%s\n' %(str(numParts))
	#if iteration == 1:
	apsh+='*\n'
	#if iteration > 1:
	#apsh+='%s\n' %(previous[:-4])
	apsh+='0,0\n'
	#if params['mirror'] is True:
	#	if iteration > 1:
	#		apsh+='180,0\n'
	#	if iteration == 1:
	#		apsh+='0,0\n'
	#if params['mirror'] is False:
        #      if iteration > 1:
        #               apsh+='360,0\n'
        #      if iteration == 1:
       	#	       apsh+='0,0\n'
	apsh+='%s,N\n' %(checkmirror)
	apsh+='%s_apsh\n' %(stack[:-4])
	runSpider(apsh)

	#if params['mirror'] is True:

	#	rot='RT SQ\n' 
	#	rot+='%s@********\n' %(stack[:-4])
	#	rot+='1-%s\n' %(str(numParts))
     	#	rot+='6,0,7,8\n' 
	#	rot+='%s_apsh\n' %(stack[:-4])
	#	rot+='%s_aligned@*******\n' %(stack[:-4])
	#	runSpider(rot)

	#if params['mirror'] is False:

	rot='do lb1 [part]=1,%s\n' %(str(numParts))
	rot+='UD IC [part] [one] [two] [three] [four] [five] [rot] [sx] [sy] [nine] [ten] [eleven] [twelve] [thirteen] [fourteen] [mirror]\n'
	rot+='%s_apsh\n' %(stack[:-4])
	rot+='IF([mirror].EQ.-1) THEN\n'
	rot+='MR\n'
	rot+='%s@{******[part]}\n' %(stack[:-4])
	rot+='_1\n' 
	rot+='Y\n'
	rot+='ENDIF\n'
	rot+='IF([mirror].EQ.1) THEN\n'
        rot+='CP\n'
        rot+='%s@{******[part]}\n' %(stack[:-4])
        rot+='_1\n'
        rot+='ENDIF\n'
	rot+='RT SQ\n'
	rot+='_1\n'
	rot+='%s_aligned@{*********[part]}\n' %(stack[:-4])
	rot+='[rot],1\n'
	rot+='[sx],[sy]\n'
 	rot+='lb1\n'
	runSpider(rot)

#=============================
def runSpider(lines):
       spifile = "currentSpiderScript.spi"
       if os.path.isfile(spifile):
               os.remove(spifile)
       nprocs = numCPUs()
       spi=open(spifile,'w')
       spi.write("MD\n")
       spi.write("TR OFF\n")
       spi.write("MD\n")
       spi.write("VB OFF\n")
       spi.write("MD\n")
       spi.write("SET MP\n")
       spi.write("(%s)\n" %(str(nprocs)))
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


#=====================
def mra_eman(refs,stack,folder,output):
        # set up cls files
        cmd = "proc2d %s cls mraprep" %(refs)
	subprocess.Popen(cmd,shell=True).wait()

        # run EMAN projection matching
        emancmd = "classesbymra %s %s split imask=-1 logit=1 sep=1 phase" %(stack,refs)
	
	nprocs = numCPUs()

	if nprocs > 1:
        	executeRunpar(emancmd,nprocs)
        else:
        	executeEmanCmd(emancmd, verbose=True)

        # create stack of aligned particles
        # first get list of cls files
        clslist=glob.glob('cls*.lst')
        clslist.sort()
        emantar = tarfile.open("%s/cls.eman.tar"%(folder),"w")
        clsarray = [[]for i in range(params['numParts'])]
	for cls in clslist:
		f = open(cls)
                lines = f.readlines()
                f.close()
                for l in range(1,len(lines)):
                	d=lines[l].strip().split()
                       	if len(d) < 4:
                        	continue
                        part = int(d[0])
                        stack = d[1]
                        cc = float(d[2][:-1])
                        (rot,x,y,mirror) = d[3].split(',')
                        clsarray[part]=[part,stack,cc,float(rot),float(x),float(y),int(mirror)]
                # for tarring cls files
        	emantar.add(cls)
	emantar.close()        

	# remove eman cls####.lst files
        for cls in clslist:
        	os.remove(cls)
	os.remove('classesbymra.log')
        # create a new cls file with all particles
        f = open("cls_all.lst","w")
        f.write("#LST\n")
        for p in clsarray:
        	f.write("%i\t%s\t%.2f,  %.6f,%.3f,%.3f,%i\n" % (p[0],p[1],p[2],p[3],p[4],p[5],p[6]))
        f.close()

        # create aligned particles
        alignParticlesInLST("cls_all.lst",output)

	shutil.move("cls_all.lst","%s"%(folder))

#=====================
def alignParticlesInLST(lstfile,outstack):
        import EMAN
        ### create a stack of particles aligned according to an LST file
        images=EMAN.readImages(lstfile,-1,-1,0)
        for i in images:
                i.edgeNormalize()
                i.rotateAndTranslate()
                if i.isFlipped():
                        i.hFlip()
                i.writeImage(outstack,-1)
	
#=======================
def executeEmanCmd(emancmd, verbose=False, showcmd=True, logfile=None, fail=False):
        """
        executes an EMAN command in a controlled fashion
        """
        waited = False
        t0 = time.time()
        try:
                if logfile is not None:
                        logf = open(logfile, 'a')
                        emanproc = subprocess.Popen(emancmd, shell=True,
                                stdout=logf, stderr=logf)
                elif verbose is False:
                        devnull = open('/dev/null', 'w')
                        emanproc = subprocess.Popen(emancmd, shell=True,
                                stdout=devnull, stderr=devnull)
                else:
                        emanproc = subprocess.Popen(emancmd, shell=True)
                if verbose is True:
                        #emanproc.wait()
                        out, err = emanproc.communicate()
                        if out is not None and err is not None:
                                print "EMAN error", out, err
                else:
                        out, err = emanproc.communicate()
                        ### continuous check
                        waittime = 2.0
                        while emanproc.poll() is None:
                                if waittime > 10:
                                	waited = True
                                        sys.stderr.write(".")
                                waittime *= 1.1
                                time.sleep(waittime)
        except:
                print ("could not run eman command: "+emancmd)
                raise
        tdiff = time.time() - t0
        proc_code = emanproc.returncode
        if proc_code != 0:
                if proc_code == -11:
                        if fail is True:
                                print ("EMAN failed with Segmentation Fault")
                        else:
                		print ("EMAN failed with Segmentation Fault")
		else:
                        if fail is True:
                        	print ("EMAN failed with Segmentation Fault")
			else:
				print ("EMAN failed with Segmentation Fault") 
#=====================
def executeRunpar(cmd,np):
        ### distribute eman function to run on several processors
        ### and run through "runpar"
        rfile="tmp.%08i"%random.randint(0,99999999)
        f=open(rfile,'w')
        for i in range(np):
                f.write(cmd+" frac=%i/%i\n" % (i,np))
        f.close()
        emancmd = "runpar proc=%i,%i file=%s" % (np,np,rfile)
        executeEmanCmd(emancmd, verbose=True)
        os.remove(rfile)
	
#==========================
def pretreat(stackfile,imagicPath):

	imgcmd='%s/align/alimass.e <<EOF\n'%(imagicPath)
	imgcmd+='%s\n' %(stackfile)
	imgcmd+='%s_center\n' %(stackfile)
	imgcmd+='TOTSUM\n'
	imgcmd+='CCF\n'
	imgcmd+='0.2\n'
	imgcmd+='3\n'
	imgcmd+='EOF\n'
	imgcmd+='%s/align/alirefs.e <<EOF\n' %(imagicPath)
	imgcmd+='ALL\n'
	imgcmd+='CCF\n'
	imgcmd+='%s_center\n'%(stackfile)
	imgcmd+='NO\n'
	imgcmd+='0.9\n'
	imgcmd+='%s_center_prep\n' %(stackfile)
	imgcmd+='-999.\n' 
	imgcmd+='.1\n'
	imgcmd+='-180,180\n'
	imgcmd+='NO\n'
	imgcmd+='EOF\n'
	imgcmd+='%s/stand/arithm.e <<EOF\n' %(imagicPath)
	imgcmd+='%s_center_prep\n' %(stackfile)
	imgcmd+='%s_center_prep_mask\n' %(stackfile)
	imgcmd+='SOFT\n' 
	imgcmd+='0.7\n'
	imgcmd+='0.1\n'
	imgcmd+='EOF\n'
	imgcmd+='%s/stand/pretreat.e <<EOF\n' %(imagicPath)
	imgcmd+='%s_center_prep_mask\n' %(stackfile)
	imgcmd+='%s_center_prep_mask_norm\n' %(stackfile)
	imgcmd+='NORMVARIANACE\n'
	imgcmd+='WHO\n'
	imgcmd+='10.0\n'
	imgcmd+='EOF\n'
	runImagic(imgcmd)

#====================
def mra(input,output,refs,orig,imagicPath):
	
	NSLOTS=numCPUs()

	imgcmd='mpirun -np %s -x DYLD_LIBRARY_PATH -x IMAGIC_BATCH %s/align/mralign.e_mpi <<EOF\n' %(str(NSLOTS),imagicPath)
	imgcmd+='FRESH\n'
	imgcmd+='ALL\n'
	imgcmd+='ROTATION_FIRST\n'
	imgcmd+='CCF\n'
	imgcmd+='%s\n' %(input)
	imgcmd+='%s\n' %(output)
	imgcmd+='%s\n' %(orig)
	imgcmd+='%s\n' %(refs)
	imgcmd+='NO\n'
	imgcmd+='NO\n'
	imgcmd+='0.2\n'
	imgcmd+='0.05\n'
	imgcmd+='-180,180\n'
	imgcmd+='-180,180\n'
	imgcmd+='0.0,0.7\n'
	imgcmd+='5\n'
	imgcmd+='NO\n'
	imgcmd+='EOF\n'
	runImagic(imgcmd)

#=====================
def runImagic(lines):
	imgfile = "currentImagicScript.csh"
       	if os.path.isfile(imgfile):
      		os.remove(imgfile)
       	imagic=open(imgfile,'w')
       	imagic.write("#!/bin/csh\n")
       	imagic.write("setenv IMAGIC_BATCH 1\n")
       	imagic.write(lines)
       	imagic.close()
	imagiccmd = "chmod +x currentImagicScript.csh"
	subprocess.Popen(imagiccmd,shell=True).wait()
       	imagiccmd = "./currentImagicScript.csh"
	subprocess.Popen(imagiccmd,shell=True).wait()
       	# clean up
       	os.remove(imgfile)
       	if os.path.isfile("Imagic_finished"):
		os.remove("Imagic_finished")

#=======================
def cleanup(params):

	mraFiles = glob.glob("%s/auto_iteration_*/mra*.img" %(params['folder']))
	mraFiles2 = glob.glob("%s/auto_iteration_*/mra*.hed" %(params['folder']))
	for files in mraFiles:
		os.remove(files)
	for files2 in mraFiles2:
		os.remove(files2)
	os.remove('%s/current_mra.img' %(params['folder']))
	os.remove('%s/current_mra.hed' %(params['folder']))

#==============================
if __name__ == "__main__":

        params=setupParserOptions()
        canPath = checkConflicts(params)
	if params['imagic'] is True:
		imagicPath=getimagicPath()
		runAutoAlign(params,imagicPath,canPath)
	if params['eman'] is True:
		getEman2Path()
		runAutoAlign(params,canPath,canPath)
	if params['spider'] is True:
		if not params['radius']:
			print "\n"
			print "Error: No radius specified, exiting."
			print "\n"
			sys.exit()
		getEman2Path()
		getSPIDERPath()
		runAutoAlign(params,canPath,canPath)
	if params['imagic'] is False:
		if params['eman'] is False:
			if params['spider'] is False:
				print '\n'
				print 'Error: No MRA program package specified. Please indicate --imagic, --eman, or --spider.\n'
				print '\n'
				sys.exit()
	cleanup(params)
