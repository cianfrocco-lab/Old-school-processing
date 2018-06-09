# Tiltpicker_import_patched

##Original code by Neil Voss: 
TiltPicker-2.0b13: http://emg.nysbc.org/redmine/projects/software/wiki/TiltPicker 

##Installation & setup
Make sure to look at the original document, which can be found in docs/INSTALL.txt and docs/USAGE.txt

##Changes: ApTiltPicker_import.py 
A patched ApTiltPicker.py that allows users to import particle coordinates and align them using the angle and tilt axis calculated with Tilt Picker.

The command line options are identical, except now the user can specify --picks1 and --picks2, which will be files containing the center coordinates (X and Y) of particles for the untilted and tilted micrographs. Example coordinate files can be found the data folder as data/picks1_import.spi and data/picks2_import.spi. 

###New command line options: 
* *--picks1=* Coordinate file for left image
* *--picks2=* Coordinate file for right image
* *--output=* Output file into which coordinates will be saved automatically

##Example command
To see how this works, here is an example command using the original data provided by Neil:

```ApTiltPicker_import.py -1 data/rawu049b.mrc -2 data/rawu048b.mrc --picks1=data/picks1_import.spi --picks2=data/picks2_import.spi --output=data/outputpicks_import.spi``` 

**To import particles:**
* Select 5 - 6 particles in both image that are the same
* Click 'Theta' button then 'Run' to calculate tilt angle
* Click 'Optimize' and then 'Run' (click run multiple times in a row) to calculate tilt axis properly.
* Click 'Import' to insert particles
* When finished, click 'Forward' and the aligned picks will be saved automatically into the specified output file

##Using this command to loop over an entire dataset
The ApTiltPicker_import.py has been incorporated into a python script that will allow you to run it over an entire dataset that has been picked automaticaly (or manually), as long as you have .box file coordinates for each tilt mate. The following steps will show you how to loop ApTiltPicker_import.py over an entire dataset.

###1. Pick particles and save them as .box files
First, automatically or manually pick particles from .mrc micrographs. The particles need to saved as .box files with the same dimensions as the .mrc micrographs. This means that if you pick particles from a binned micrograph, you need to 'unbin' the .box file coordinates.

Also, the .box files should have an identical name as the .mrc micrographs. 

Example files:
* data/raw049b.mrc and data/raw049b.box
* data/raw048b.mrc and data/raw048b.box

###2. Create text file with tilt pairs
Using the python script *make_tilt_pair_file.py* to create a text file listing each tilt mate from your dataset.

***Input options:***
```
$ ./make_tilt_pair_file.py                                                    
Usage: make_tilt_pair_file.py -p <path/to/images> -o <output> --Uext=[untiltExtension] --Text=[tiltExtension]

Options:
  -h, --help     show this help message and exit
  -p FILE        Absolute path to the folder containing tilt-mates
  -o FILE        Output file to contain tilt mates
  --Uext=STRING  Untilted micrograph extension (e.g. '00', 'u')
  --Text=STRING  Tilted micrograph extension (e.g. '01', 't')
  --leginon      Flag if tilt mates came from leginon
  -d             debug
  ```

Example command: 
```./make_tilt_pair_file.py -p data/ -o data/rct_tiltpair.txt --Uext=049b --Text=048b```

This creates a new text: 
```$ head data/rct_tiltpair.txt 
data/rawu049b.mrc	data/rawu048b.mrc```

###3. Run ApTiltPicker_import.py over your dataset
To loop over all micrographs listed in the newly created text file, you can run the command ***runApTiltPicker_import.py***. 

***Input options:***
```
$ ./runApTiltPicker_import.py 
Usage: runApTiltPicker_import.py -i <input micrograph> -t <template imagic stack> --apixMicro=[pixel size] --apixTemplate=[pixel size] --boxsize=[box] --diam=[particle diameter] --thresh=[threshold] --mirror --bin=<bin> --all='wildcard'

Options:
  -h, --help       show this help message and exit
  --micros=STRING  Input file containing tilt pair names
  --binning=INT    Binning factor for picking (Default=4)
  --microdims=INT  Micrograph dimensions (Default=4096)
  --box=INT        Specify output box size for particles in UNbinned
                   micrograph.
  --extract        Flag to extract particles into unbinned particle stacks
  --output=STRING  OPTIONAL: If extracting particles, specify output base name
                   of stacks (Default=output_stack).
  -d               debug
  ```

Example command: 
```$ ./runApTiltPicker_import.py --micros=data/rct_tiltpair.txt --binning=2 --microdims=1600 --box=80 --extract --output=data/raw_stack```

Output box files with aligned, matched coordinates: 
* data/raw049b_tiltPicked.box
* data/raw048b_tiltPicked.box
* data/raw_stack_tiltstack.img/hed 
* data/raw_stack_untiltstack.img/hed

Where: 
* binning - the user has the option to bin the micrographs for viewing
* microdims - this option is used to in combination with the box size to remove any particles that may be outside of the micrograph 
* box - box size used to check if particles are outside of micrograph
* extract - (OPTIONAL) flag option to use batchboxer to extract particles into output stacks
* output - (OPTIONAL) basename for output stacks. The base name will have the suffix *_untiltstack.img* and *_tiltstack.img* added 
