#! /usr/bin/env python

import glob
import os
import sys

#How to use: ./make_tiltpair_file_w_v_in_it.py [outputfilename].txt
#Assumes that tilted image are '00.mrc' and untilts are '01.mrc'

tiltnames=glob.glob('*00.mrc')
o1=open(sys.argv[1],'w')

maxv=10

for tilt in tiltnames:

	if tilt.split('hl')[1][1] is 'v':
		#print 'Tilt=%s' %(tilt)		
		#Rename and find untilt image with 'v' in it
		currentv=float(tilt.split('hl')[1][2:4])
		i=1
		actualuntilt=''

		while i<=maxv:
		
			nextv=currentv+i

			untiltChange = tilt.split('hl')[0]+'hl'+'_'+'v'+'%02i'%(nextv)+'_'+tilt.split('hl')[1][5:][:-6]+'01.mrc'
			if os.path.exists(untiltChange):
				actualuntilt=untiltChange
	
			i = i + 1	
	
		#print 'Untilt=%s' %(actualuntilt)
	
	if tilt.split('hl')[1][1] is not 'v':
		#print 'Tilt=%s' %(tilt)
		#print 'NOT V'

		untiltChange = tilt.split('hl')[0]+'hl'+'_'+'01'+'_'+tilt.split('hl')[1][4:][:-6]+'01.mrc'
		#print 'UntiltChange=%s' %(untiltChange)
		actualuntilt=''
		if os.path.exists(untiltChange):
			actualuntilt=untiltChange
			#print 'Untilt=%s' %(actualuntilt)

		if not os.path.exists(untiltChange):
			
			#Check for v's

			i=1
			while i<=maxv:

				untiltChange = tilt.split('hl')[0]+'hl'+'_'+'v'+'%02i'%(i)+'_'+tilt.split('hl')[1][4:][:-6]+'01.mrc'
				
				if os.path.exists(untiltChange):
					actualuntilt=untiltChange
					#print 'found it'
				i=i+1

		#if len(actualuntilt)>0:
			#print 'Untilt=%s' %(actualuntilt)
		#if len(actualuntilt)==0:
			#print 'No tilt mate'

	if len(actualuntilt)>0:
		o1.write('%s\t%s\n' %(tilt,actualuntilt))

