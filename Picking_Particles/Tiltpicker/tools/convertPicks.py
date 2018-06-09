#!/usr/bin/env python

import sys
from apSpider import operations

if __name__ == "__main__":
	infile = sys.argv[1]
	outfile = sys.argv[2]
	f = open(infile, "r")
	g = open(outfile, "w")
	num = 1
	for line in f:
		sline = line.strip()
		if sline[0] == ";":
			g.write(" "+sline+"\n")
			continue
		spidict = operations.spiderInLine(sline)
		nline = operations.spiderOutLine(num, spidict['floatlist'][1:3])
		g.write(nline)
		num+=1

