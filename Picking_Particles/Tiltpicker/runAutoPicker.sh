#!/bin/sh

./ApTiltAutoPicker.py \
  -1 data/rawu049b.jpg -2 data/rawu048b.jpg \
  --p1=data/picks1.spi --p2=data/picks2.spi \
  -o data/rawu0picks-new.spi \
  -t 49.9 -d 80.0 -x -77.48
