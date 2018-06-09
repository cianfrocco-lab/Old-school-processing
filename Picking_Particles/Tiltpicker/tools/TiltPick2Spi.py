#!/usr/bin/python -O

import sys
import os
#import shutil

def getSyntax(name):
  syntax = 'Syntax: \n'
  syntax += '   python %s /inpath/prefix file_extension /outpath/ \n\n' % name
  syntax += 'Example: \n'
  syntax += '   python %s /path/to/cords/pik spi /new/cord/path/ \n\n' % name
  syntax += '       will cut /path/to/cords/pik****.spi to: \n'
  syntax += '       /new/cord/path/dct****.spi = particle coordinates of tilted micro \n'
  syntax += '       /new/cord/path/dcu****.spi = particle coordinates of untilted micro \n'
  syntax += '       /new/cord/path/dct****.spi = angles between tilted and untilted micro \n\n'
  syntax += 'Instructions: \n'
  syntax += '   1) if data was manually collected then last four characters correspond with tilted micrograph \n'
  syntax += '   2) if from Leginon then assumes _0 is tilted and _1 is untilted \n'
  syntax += '       and output filenames are given odd numbers starting from 0001 \n\n'
  syntax += 'Version: 2009.10.06 Ed Brignole \n'

  return syntax

def lowerCase(name):

  return name.lower()
  
def break_pikfile_into_docs(fname):
  infile = open(fname, "r")
  filenum = os.path.splitext( os.path.basename(fname) )[0][-4:]
  mode = None
  blines = []
  ulines = []
  tlines = []
  for line in infile:
    if line[0] == ';':  #add space if first line starts with a ;
      line = ' ' + line
    if mode == None:    #mode None is reading header into bfile
      if "; parameters" in lowerCase(line):
        mode = "PARAM"
        print ' ...found angles'
        blines.append( line )
    elif mode == "PARAM":  #mode Param is reading parameters
      if "; left image" in lowerCase(line): 
        if ( filenum or "en_00.dwn.mrc" ) in line:
          mode = "TIMAGE"
          print ' ...found tilted coordinates for left image'
          tlines.append( line )
        else:
          mode = "UIMAGE"
          print ' ...found untilted coordinates for left image'
          ulines.append( line )
      else:
        blines.append( line )
    elif mode == "TIMAGE":  #mode Image is reading coordinates
      if "; right image" in lowerCase(line): 
        if ( filenum or "en_00.dwn.mrc" ) in line:
          print 'ERROR: Found tilted coordinates for right image too!'
          sys.exit(1)
        else:
          mode = "UIMAGE"
          print ' ...found untilted coordinates for right image'
          ulines.append( line )
      else:
        tlines.append( line )
    elif mode == "UIMAGE":  #mode Image is reading coordinates
      if "; right image" in lowerCase(line): 
        if ( filenum or "en_00.dwn.mrc" ) in line:
          mode = "TIMAGE"
          print ' ...found tilted coordinates for right image'
          tlines.append( line )
        else:
          print 'ERROR: Found untilted coordinates for right image too!'
          sys.exit(1)
      else:
        ulines.append( line )
    else:
      print 'ERROR: Could not figure out where to put line'
      sys.exit(1)
  if ("IMAGE" not in mode):
    print "ERROR: Did not correctly parse file"
    sys.exit(1)        
  infile.close()

  return blines, tlines, ulines

if __name__ == "__main__":
  if len(sys.argv[1:]) != 3 or '-h' in sys.argv[1:]:
    syntax = getSyntax(sys.argv[0])
    print syntax
    sys.exit(0)
  pathprefix = sys.argv[1]
  ext = sys.argv[2]
  outpath = sys.argv[3]
  
  coordpath, prefix = os.path.split(pathprefix) # ('/this/is/my', 'path.ext')
  print "Searching for TiltPicked coordinate files in %s/ with filename extension .%s" % (coordpath, ext)
  if outpath[-1] != '/':
    outpath += '/'
  print "Output Path is %s" % outpath
  #list all filenames in coordinate directory
  filelist = os.listdir(coordpath)
  count=0
  for filename in filelist:
    froot, fext = os.path.splitext(filename)  # ('/this/is/my/path', '.ext')
    #does filename have correct prefix and extension
    if (fext[1:] == ext) and (froot[:len(prefix)] == prefix):
      print "\nCutting %s" % filename
      infname = coordpath + "/" + filename
      blines, tlines, ulines = break_pikfile_into_docs(infname)
      count += 1                  #increment number of input coordfiles
      # Check for filenames according to Leginon or manual micrographs
      if "en" in froot[-5:-1]:            #then image is from leginon
        num1 = count * 2 - 1             # tilted micro number
        num2 = num1 + 1                  # untilted micro number
        bname = outpath + "dcb" + "%04d" %num1 + ".spi"
        tname = outpath + "dct" + "%04d" %num1 + ".spi"
        uname = outpath + "dcu" + "%04d" %num1 + ".spi"
      else:                    #then image is scanned micrograph
        filenum = froot[-4:]   #assume last four characters are micronumber
        bname = outpath + "dcb" + filenum + ".spi"
        tname = outpath + "dct" + filenum + ".spi"
        uname = outpath + "dcu" + filenum + ".spi"
      #write angle parameters file
      bfile = open(bname, "w")
      bfile.writelines(blines)
      bfile.close()
      #write tilted coordinate file
      tfile = open(tname, "w")
      tfile.writelines(tlines)
      tfile.close()
      #write untilted coordinate file
      ufile = open(uname, "w")
      ufile.writelines(ulines)
      ufile.close()

  print "\nFound and processed %s coordinate files. Saved in %s" % (count, outpath)
