#!/usr/bin/env python
#
# Python script for conveting from and to various audio formats.
# Should work recursively and handle funny names.
#
#
# Todo: Add an option to remove spaces and strange characters from
# filenames of output files (low priority).
# rearrange layout to be more readable.
#
# Version 0.4.5.3
#
# Changes:
# 0.1 Uses a system tempfile instead of a file named "tempfile", so multiple 
# instances can be running at the same time.
#
# 0.2 Redesign for cleaner code, and slightly simpler use.  Added flac and wav
# as input and output formats
#
# 0.3 Ported to windows (with downloaded exe's), and a newer version of mplayer
# that uses a different syntax.
#
# 0.3.1 Jim Hanley added support for decoding realaudio .rpm streams and rm/ra files.
#
# 0.3.2 Added a strict filter to remove genre tags that are not in a 'genre list', 
# should solve the problem of Lame (or other encoders) failing to encode due to crazy 
# genre tags.
#
# 0.3.3 Made default bitrate of output file equal to the input bitrate unless the bitrate 
# option is specified.  Skipping files that have a bitrate less than or equal to the specified 
# output bitrate, this can be bypassed with the --force option.
#
# 0.4 Added support for Metaflac tags, and the option of using a different output (destination)
# directory as requested by Joe Oldak.
#
# 0.4.1 Small bugfix for import formats read by mplayer.
#
# 0.4.2
# -added -nolirc -nojoystick and to the mplayer decoder commands to reduce the warnings.
# -Changed the creation of a tempfile when decoding with mplayer.  Unix not uses a normal tempfile,
#   while 'nt' systems use a tempfile in the local directory.  
# -There is a new --dry-run option that lists the files to be converted
# -There is also an --encoder-option option that allows passing of options to the encoder (currently lame, 
#   oggenc and flac).  This is useful for things like vbr that are hard to make universal to every encoder.
#
# 0.4.3 Minor feature added.  Added the 'tempfile' option to specify the location to be used for the pcm tempfile.
#
# 0.4.4 Refactor of the recursion logic.  This should make recursion more robust and allow directories with square
# brackets and other strange characters.  Previously this was causing problems with Glob.  Done in a multi-platform way
# but still must test in windows.
#
# 0.4.5 Added an extra check so the original input file won't be deleted if the output file does not exist.
#
# 0.4.5.1 Small bugfix for flac decoding (and small cleanup), so filenames with spaces will be handled
# (Thanks to J. Huckabay).
#
# 0.4.5.2 Improved the "--dry-run" option; it will now show the path of the input and output file.  Also switched from
# using os.system() to using subprocess.Popen() because control-c works much better among other things.  Refactored other
# try statements so control-c won't mess them up.  Added the ability to handle files with double quotes in the filename 
# (crazy, but they exist).  These can exist in *nix, but windows won't allow them - so its an easy fix.
#
# 0.4.5.3 Now replacing double quotes with single quotes for parsing of flac, mp3,
# and ogg meta tags.
#
# Chris LeBlanc, 2006
#
#
#
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU program General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the GNU
# program General Public License for more details.
#
# You should have received a copy of the GNU program General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307	USA

import sys
import os
from subprocess import *
import shutil
import glob
import StringIO
from random import randint
from string import join
from optparse import OptionParser
from tempfile import NamedTemporaryFile

# If the binaries are in the path (linux or windows).
MPLAYER = "mplayer"
OGGENC = "oggenc"
OGGDEC = "oggdec"
OGGINFO = "ogginfo"
LAME = "lame"
MP3INFO = "mp3info"
FLAC = "flac"
METAFLAC = "metaflac"
NORMALIZE = "normalize-audio"

### If the binaries are not in the path, list them here (eg windows).  Using double slashes to exclude things like \n from
### being interpreted as newlines and such
##MPLAYER = "c:\\chris\\audio_conv\\mplayer\\mplayer.exe"
##OGGENC = "c:\\chris\\audio_conv\\oggenc.exe"
##OGGDEC = "c:\\chris\\audio_conv\\oggdec.exe"
##OGGINFO = "c:\\chris\\audio_conv\\ogginfo.exe"
##LAME = "C:\\chris\\audio_conv\\lame.exe"
##MP3INFO = "C:\\chris\\audio_conv\\mp3info.exe"
##FLAC = "C:\\chris\\audio_conv\\bin\\flac.exe"
##METAFLAC = "C:\\chris\\audio_conv\\bin\\metaflac.exe"
##NORMALIZE = "C:\\chris\\audio_conv\\normalize.exe"


def getCmdLineArgs():
	parser = OptionParser()

	parser.usage = """audio_conv.py -i <input> [options] --to-mp3 | --to-ogg | --to-wav | --to-flac
	
	This script is for conveting from an input audio format to an 
	intermediate wav file, then outputting to the selected output 
	format while keeping the tag info.  At first this sounds crazy, 
	why go from one lossy format to another?  This may be the only 
	option for your portable mp3 player.  It is also an easy way to 
	convert a music collection from a high quality format (eg: flac 
	or wav) to a different format (eg: mp3 or ogg vorbis).
	
	Optionally works recursively, keeps the tag information, and handles 
	filenames with strange characters such as spaces, single quotes, and 
	question marks.  It can also output the converted file to a different 
	directory, maintaining the directory structure.	Most of the other 
	wma2ogg or ogg2mp3 scripts fail on these or dont do recursion, which 
	is why this script exists.
	
	Supported input formats:
		wma
		flac
		wav
		ogg
		mp3
		rpm RealAudio streams
		rm/ra RealAudio files
	
	Supported output formats:
		wav
		flac
		mp3
		ogg
	
	
	Requires mplayer (for wma), vorbis tools, flac, lame, normalize 
	and mp3info.  Note: if there are no tags in the input file, the 
	filename will be used as the 'title' tag in the output file.
	
	Examples:
	
	This example converts the ogg vorbis file 'foo.ogg' to 'foo.mp3':
	 audio_conv.py -i foo.ogg --to-mp3
	
	This example converts all wma files to ogg vorbis files in a 
	directory (not recursive and wont delete the original files):
	 audio_conv.py -i "*.wma" --to-ogg
	
	This command passes a string to the encoder (lame in this case, 
	since mp3s are being created), which can be any sort of option 
	(variable bitrate, mode, etc).  The option here specifies that 
	variable bitrate level 6 is to be used (see encoder documentation 
	for more info):
	 audio_conv.py -i file.mp3 --to-mp3 --encoder-option "-V 6"
	
	This dry-run example lists all the files that would be processed,
	but are simply listed instead (an output format is needed, so 
	--to-mp3 is chosen though no conversion is done):
	 audio_conv.py -i "*.wma" -r --to-mp3 --dry-run
	
	This command converts all recoginized files to mp3s recursively, 
	performs normalization and deletes the original files.  If the 
	file doesn't have a recognized extension, then it is skipped.
	 audio_conv.py -i "*.*" --to-mp3 --recursive --normalize --delete
	
	Here is the same command with short options:
	 audio_conv.py -i "*.*" --to-mp3 -r -n -d
	
	This is the same command, but with a different destination directory.
	This will duplicate the directory structure present in the source 
	to subdirectories of the destination directory populating it only with 
	the converted files.
	 audio_conv.py -i "*.*" --to-mp3 -r -n -d --dest-dir /home/user/newdir
"""

	parser.add_option("-i", "--input", dest="inFile", \
		help="Specify input file, accepts wildcards in quotes.", \
		type="string", metavar="INPUT")
# 	parser.add_option("-o", "--output", dest="outFile", \
# 		help="Specify output filename (optional).", \
# 		type="string", metavar="OUTPUT")
	parser.add_option("-b", "--bitrate", dest="bitrate", \
		help="Specify bitrate of output file.  Some encoders" + \
		"(eg Lame) will only accept certain values such as 32, " + \
		"40, 48, 56, 64, 80, 96, 112, 128, etc. The default bitrate " + \
		"of the output file is the same as the input bitrate.  This " + \
		"option will be ignored if the '--encoder-option' is used.", \
		type="int", metavar="BITRATE", default=None) #the default bitrate is set later
	parser.add_option("-f", "--force", action="store_true", \
		 dest="force", help="Force conversion of files even " + \
		 "if the input and output bitrate are the same " + \
		 "[default skips these files].")
	parser.add_option("-r", "--recursive", action="store_true", \
		 dest="recursive", help="Convert all files matching " + \
		 "the input filename in current directory and all " + \
		 "subdirectories.  If using wildcards, they must be in " + \
		 "quotes.")
	parser.add_option("--dry-run", action="store_true", \
		 dest="dryRun", help="List the path of each input file " + \
		 "and output file but do not convert anything.")
	parser.add_option("--to-ogg", action="store_true", \
		 dest="oggOutput", help="Ogg vorbis output format.")
	parser.add_option("--to-mp3", action="store_true", \
		 dest="mp3Output", help="Mp3 output format")
	parser.add_option("--to-wav", action="store_true", \
		 dest="wavOutput", help="Wav output format")
	parser.add_option("--to-flac", action="store_true", \
		 dest="flacOutput", help="Flac output format")
	parser.add_option("-n", "--normalize", action="store_true", \
		 dest="normalize", help="Normalize the volume of " + \
		 "output files.")
	parser.add_option("-d", "--delete", action="store_true", \
		 dest="delSource", help="Delete the input file after " + \
		 "conversion (use with caution!).")
	parser.add_option("--dest-dir", dest="destDir", \
		help="Specify a different output directory. This will " + \
		"duplicate the same file and directory structure seen in " + \
		"the source directory, and populate it with converted files. " + \
		"If the destination directory does not exist, it will be created. " + \
		"Works especially well with the recursive option.", \
		type="string", metavar="DESTINATION", default=None)
	parser.add_option("-t", "--tempfile", dest="tempFile", \
		help="Specify the path for a user defined tempfile. The default " + \
                "tempfile uses a system tempfile.", \
		type="string", metavar="PATH", default=None)
	parser.add_option("-e", "--encoder-option", dest="encodeOption", \
		help="Specify options to be passed to the encoder. May " + \
		"include any option supported by the encoder such as " + \
		"variable bitrate encoding. This option overrides the 'bitrate' " + \
		"option, so a custom bitrate or vbr setting should be specified " + \
		"otherwsie the encoder will use its default bitrate. Be careful not " + \
		"to specify tags that may conflict with tags taken from input file. " + \
		"String must be encapsulated by quotes.", \
		type="string", metavar="STRING", default="")
	parser.add_option("-v", "--verbose", action="store_true", \
		 dest="verbose", help="Show all standard output and error " + \
		"messages from backend programs.  Default is to hide these messages.")
	
	return parser.parse_args()

def mplayerTags(tagInfo):
	# getting tag info from mplayer (it seems only name and author are given)
	tagName = ""
	tagAuthor = ""
	inBitrate = None
	for line in tagInfo:
		fields = line.split()
		
		try:
			if fields[0] == "name:":
				tagName = join(fields[1:], " ")
			if fields[0] == "author:":
				tagAuthor = join(fields[1:], " ")
			if fields[0] == "AUDIO:":
				inBitrate = fields[-2]
				inBitrate = inBitrate.replace("(","")
		except:
			pass
	
	return tagName, tagAuthor, inBitrate


def ogginfoTags(tagInfo):
	tagName = ""
	tagAuthor = ""
	tagGenre = ""
	tagDate = ""
	tagAlbum = ""
	inBitrate = ""
	for line in tagInfo:
		# replacing equals sign with whitespace
		line = line.replace("="," ")

		# replacing double quotes with single quotes
		line = line.replace('"',"'")
		
		# splitting on whitespace
		fields = line.split()
		
		try:
			# lowercase so it can be used to parse metaflac info.
			fields[0] = fields[0].lower()
			
			if fields[0] == "title":
				tagName = join(fields[1:], " ")
			if fields[0] == "artist":
				tagAuthor = join(fields[1:], " ")
			if fields[0] == "genre":
				tagGenre = join(fields[1:], " ")
			if fields[0] == "date":
				tagDate = join(fields[1:], " ")
			if fields[0] == "album":
				tagAlbum = join(fields[1:], " ")
			if fields[0:2] == ['nominal', 'bitrate:']:
				# getting the input bitrate, will cast to an int later.
				inBitrate = fields[2]
		except:
			pass
	return tagName, tagAuthor, tagGenre, tagDate, tagAlbum, inBitrate

# skipping files that have the same or less input bitrate as the desired output (and the same in/output format).
def badBitrate(file, inBitrate, options, inFileExtension, outFileExtension):
	if outFileExtension == inFileExtension:
		if options.force:
			# forcing by making it look like the bitrates are not identical
			return False
		elif int(float(inBitrate)) == options.bitrate:
			print("skipping %s, input and output bitrate are identical. Use -f to force conversion." % file)
			return True
		elif int(float(inBitrate)) < options.bitrate:
			print("skipping %s, input bitrate less than output. Use -f to force conversion." % file)
			return True
		else:
			return False
	# if in/out file extensions are different, don't skip transcoding.
	else:
		return False

# duplicating old recursive directory structure in new destination directory.  Tricky!  TODO: test in windows
# the use of absolute paths may mess up the windows version of mplayer...
def destinationDir(file, destDir, dryRun):
	# some variable needed for creating the destination directory structure.
	
	fileBasename = os.path.basename(file) # basename of file, no leading directories.
	fileAbs = os.path.abspath(file) # absolute, not relative
	topDirAbs = os.path.abspath(topDir) # the 'top' directory, the subdris from here will be duplicated in the new dir.
	destDirAbs = os.path.abspath(destDir) # absolute path of the destination directory
	strippedPath = fileAbs.replace(topDirAbs, "")[1:] # stripping the 'top' directory from the path of the file to process.
	newFileDir = os.path.dirname(strippedPath) # the directory of the stripped file, relative to the top directory (NOT absolute).  Needs to be created if it doesn't exist!
	newFileDirAbs = os.path.join(destDirAbs, newFileDir) # absolute path of the new directory including new subdirs.
	newFilePath = os.path.join(newFileDirAbs, fileBasename) # joining the new path and basename
	
	# making a copy of the directory structure, because it will be modified.
	newFileDirCopy = newFileDir
	dirList = []
	while newFileDirCopy:
		deepDir = newFileDirCopy
		dirList.append(deepDir)
		# modifying newFileDirCopy by stripping off the deepest subdir.
		newFileDirCopy = os.path.split(newFileDirCopy)[0]

	# no need to make new directories for a dry run.
	if not dryRun:
		# creating the dest-dir if it doesn't exist (not really necessary, but what the heck).  May remove this later (?).
		if not os.path.isdir(destDirAbs):
			os.mkdir(destDirAbs)
		
		# reversing the list so I make parent directories (if needed) before subdirectories
		dirList.reverse()
		for directory in dirList:
			fullDirPath = os.path.join(destDirAbs, directory)
			if not os.path.isdir(fullDirPath):
				print "The following output driectory doesn't exist, creating:", fullDirPath
				os.mkdir(fullDirPath)
	
	return newFilePath

def runPopen(popenString, verbose):
	popenOuput = None
	if verbose:
		# letting standard output go to terminal for verbosity
		popenOutput = Popen(popenString, shell=True).communicate()[0]
	else:
		# capturing standard output from command instead
		popenOutput = Popen(popenString, shell=True, stdout=PIPE, stderr=PIPE).communicate()[0]
	
	popenInfo = StringIO.StringIO(popenOutput)
# 	print popenOutput
# 	for i in popenInfo:
# 		print i
	
	return popenInfo
	

def gracefulExit():
	# exiting program gracefully instead of messing up try statements and continuing on to process other files.
	# may want to delete the tempfile here.
	sys.exit()
	

if __name__ == "__main__":
	# getting the command line options from the parser
	(options,args)= getCmdLineArgs()
	
	if not options.inFile:
		print("Error: you must supply an input file (--input).  \nType 'audio_conv.py -h' for help")
		sys.exit()
	
	topDir, wildCard = os.path.split(options.inFile)
	absTopDir = os.path.abspath(topDir)
	baseName = os.path.splitext(wildCard)[0]
	wildCardExt = os.path.splitext(wildCard)[1]
	if len(topDir) == 0:
		topDir = "."
	

	# The file(s) to process if not doing the recursive thing.  Glob handles wildcards
	# but you have to use quotes in *nix.
	filesToProcess = []
	for possibleFile in glob.glob(options.inFile):
		if os.path.isfile(possibleFile):
			filesToProcess.append(possibleFile)
		elif not os.path.isdir(possibleFile):
			print possibleFile, "not a regular file, skipping."
	
	# handling the recursive case, still using glob for wildcards.  Glob handles some paths poorly, so 
	# chaning to those dirs and using glob to expand contents of each dir.
	workingDir = os.getcwd()
	os.chdir(absTopDir)
	if options.recursive:
		# walking the present working dir, since we've changed to that dir.
		for directories, subdirs, files in os.walk("."):
			for subdir in subdirs:
				subDirPath = os.path.join(directories, subdir)
				
				# changing directory to the dirPath, because glob will fail on
				# directories with square brackets in the path.
				os.chdir(subDirPath)
				
				for file in glob.glob(wildCard):
					#only want real files and links	
					if os.path.isfile(file):
						# 'file' is just the filename, joining with the path and appending to list
						# of files to process.
						absFilePath = os.path.join(topDir, directories, subdir, file)
						
						# cleansing the path with normpath to make it easier for mplayer and such.
						absFilePath = os.path.normpath(absFilePath)
						
						filesToProcess.append(absFilePath)
				
				# changing back to the parent directory of recursion for looping in other dirs.
				os.chdir(absTopDir)
				
	# returning to the original directory
	os.chdir(workingDir)


	# Using os.system line calls for all the heavy lifting
	for file in filesToProcess:
		# unix specific way of being able to read files with double quotes.
		# Fine since double quotes are not allowed in windows.
		file = file.replace('"', '\\"')
		
		# user defined tempfile location for the pcm file.
		# mplayer decoding uses a special tempfile for windows.
		if options.tempFile:
			tempFile = options.tempFile
		else:
			tempFile = NamedTemporaryFile().name
	
		# leave the taginfo file as a system tempfile
		tagInfo = NamedTemporaryFile().name
	
	

		# metadata tags and input bitrate value
		tagName = ""
		tagAuthor = ""
		tagGenre = ""
		tagDate = ""
		tagAlbum = ""
		inBitrate = ""
		
		# need to know output extension to see if conversion can be skipped with badBitrate().
		if options.oggOutput:
			outFileExtension = ".ogg"
		elif options.mp3Output:
			outFileExtension = ".mp3"
		elif options.wavOutput:
			outFileExtension = ".wav"
		elif options.flacOutput:
			outFileExtension = ".flac"
		else:
			print "Error: Audio output format not chosen, please select one."
			break	
		
		# using the file extension to determine what format it is (there could be a better way,
		# something like the unix command 'file')
		# converting all to lower case for simplicity
		fileCaseless = file.lower()
		inFileExtension = os.path.splitext(fileCaseless)[1]
		
		# Dry run, not doing conversion.  Just listing files to be precessed
		if options.dryRun:
			if file == filesToProcess[0]:
				print "Dry run file(s) to process, and new output file(s):"
		
		# converting everything to a wav file, and getting the tag data
		elif inFileExtension == ".mp3":
			print "decoding:" + file
			
			# using mp3info because it gives a lot of nice options for formatting of tag output.
			# formatting so I can use ogginfoTags to parse the info.  Using popen to subprocess.Popen to drive command line
			popenString = ('%s %s "%s"' % (MP3INFO, '-x -r m -p "title=%t \\nartist=%a \\ngenre=%g \\ndate=%y \\nalbum=%l\\n \\nNominal bitrate: %r\\n"', file))
			# tagInfo captures stdout and stderr from mp3info, stores as a string.
			tagInfo = runPopen(popenString, verbose=False)
			
			# using ogginfoTags to parse the tag info.  Maybe I should rename it.
			tagName, tagAuthor, tagGenre, tagDate, tagAlbum, inBitrate = ogginfoTags(tagInfo)
			
			if badBitrate(file, inBitrate, options, inFileExtension, outFileExtension):
				continue
			
			# decoding mp3 with lame
			decodeString = ('%s --decode "%s" "%s"' % (LAME, file, tempFile))
			runPopen(decodeString, options.verbose)
			
		elif inFileExtension in (".wma", ".rm", ".ra"):
			print "decoding:" + file
			
			# converting from wma to wav
			# the 'pcm -aofile <filename>' options has changed to '-ao pcm:file=<filename>'
			# which doesn't like dos filenames! (c:\bla\...) so I'm changing the tempfile path to
			# point to the working directory.  Also letting user set a tempfile location with a CLI option.
			if (os.name == 'nt' and not options.tempFile):
				tempFile = os.path.basename(tempFile)
			
			# newer syntax for newer version of mplayer (1.0pre7-3.4.2) and dos/win compatible:
			popenString = ('%s -quiet -nolirc -nojoystick -ao pcm:file="%s" -vo null -vc dummy "%s"' % (MPLAYER, tempFile, file))
			
# 			# older syntax, for mplayer 1.0pre5-3.3.4 and similar
# 			popenString = ('%s -quiet -nolirc -nojoystick -ao pcm -aofile "%s" -vo null -vc dummy "%s"' % (MPLAYER, tempFile, file))

			tagInfo = runPopen(popenString, verbose=False)
			
			if options.verbose:
				for line in tagInfo:
					line = line.replace("\n", "")
					print line

			# getting tag info from the info file created by mplayer in the last step.
			tagName, tagAuthor, inBitrate = mplayerTags(tagInfo)
			
			if badBitrate(file, inBitrate, options, inFileExtension, outFileExtension):
				continue

		elif inFileExtension == ".rpm":
			readFile = open(file)
			readLines = readFile.readlines()
			for stream in readLines :
				print "decoding stream:" + stream
				
				# only process non blank lines
				if len(stream) == 0:
					continue
				
#				os.system( '%s -cache 1280 -dumpstream -dumpfile essselection.ra %s' \
#					% (MPLAYER, stream))

				# syntax for newer mplayer, see above section for .wma files for older syntax
        			if (os.name == 'nt' and not options.tempFile):
        				tempFile = os.path.basename(tempFile)



				# new mplayer syntax (not tested yet! get appropriate file to test)
				popenString = ('%s -cache 1280 -quiet -nolirc -nojoystick -ao pcm:file="%s" -vo null -vc dummy "%s"' % (MPLAYER, tempFile, stream))
				## old mplayer syntax
				#popenString = ('%s -cache 1280 -quiet -nolirc -nojoystick -ao pcm -aofile="%s" -vo null -vc dummy "%s"' % (MPLAYER, tempFile, stream))
				
				tagInfo = runPopen(popenString, verbose=False)
				
				if options.verbose:
					for line in tagInfo:
						line = line.replace("\n", "")
						print line
					
				tagName, tagAuthor, inBitrate = mplayerTags(tagInfo)

			if badBitrate(file, inBitrate, options, inFileExtension, outFileExtension):
				continue
			
		elif inFileExtension == ".ogg":
			print "decoding:" + file

			# getting tag info
			popenTagString = ('%s "%s"' % (OGGINFO, file))
			tagInfo = runPopen(popenTagString, verbose=False)
			
			tagName, tagAuthor, tagGenre, tagDate, tagAlbum, inBitrate = ogginfoTags(tagInfo)
			
			if badBitrate(file, inBitrate, options, inFileExtension, outFileExtension):
				continue
			
			# converting ogg to wav
			popenString = ('%s "%s" -o "%s"' % (OGGDEC, file, tempFile))
			encodeInfo = runPopen(popenString, options.verbose)

		elif inFileExtension == ".flac":
			print "decoding:" + file
			
			# decoding from flac to wav
			popenString = ('%s -f --decode "%s" -o "%s"' % (FLAC, file, tempFile))
			encodeInfo = runPopen(popenString, options.verbose)
			
			
			try:
				# using metaflac to extract the tags from the flac file
				popenTagString = ('%s --show-tag=TITLE --show-tag=ARTIST --show-tag=ALBUM --show-tag=DATE --show-tag=GENRE "%s"' \
																% (METAFLAC, file))
				# verbose is false because we want to capture the standard output instead of letting it go to the terminal.
				# metaflac is quick, so it can be run again if the verbose option is given.
				tagInfo = runPopen(popenTagString, verbose=False)
				
				# we can use ogginfoTags to parse the tag info file since its almost the same format.
				tagName, tagAuthor, tagGenre, tagDate, tagAlbum, inBitrate = ogginfoTags(tagInfo)
				
			# this except statement is for handling control-c from command line.  Otherwise if control-c is hit, 
			# the other except will be run.  This allows the program to exit normally.
			except (KeyboardInterrupt, SystemExit):
        			gracefulExit()
			except:
				print "No tags in flac file"
			
		elif inFileExtension == ".wav":
			# if its already a wave, leave it as is.
			tempFile = file
		else:
			print "Error processing file: " + file
			print "input format not recognized, please check file extension."
			continue
		
		
		# checking the genre tag to make sure its acceptable for Lame and other encoders (got listing from id3v2)
		# should probably have dictionary in a different file, but its nice to have everything in one script.
		
		# Testing the genre tag.  Ignoring the 'genre as number' case.  Not trying to handle crazy cases.
		# Genre list generated by id3v2 program with -L option ('Bebob' looks like a typo but 'Bebop' wont work with Lame).
		genreList = ('Blues', 'Classic Rock', 'Country', 'Dance', 'Disco', 'Funk', 'Grunge', 'Hip-Hop', \
			'Jazz', 'Metal', 'New Age', 'Oldies', 'Other', 'Pop', 'R&B', 'Rap', 'Reggae', 'Rock', 'Techno', \
			'Industrial', 'Alternative', 'Ska', 'Death Metal', 'Pranks', 'Soundtrack', 'Euro-Techno', \
			'Ambient', 'Trip-Hop', 'Vocal', 'Jazz+Funk', 'Fusion', 'Trance', 'Classical', 'Instrumental', \
			'Acid', 'House', 'Game', 'Sound Clip', 'Gospel', 'Noise', 'Alt. Rock', 'Bass', 'Soul', 'Punk', \
			'Space', 'Meditative', 'Instrum. Pop', 'Instrum. Rock', 'Ethnic', 'Gothic', 'Darkwave', \
			'Techno-Indust.', 'Electronic', 'Pop-Folk', 'Eurodance', 'Dream', 'Southern Rock', 'Comedy', \
			'Cult', 'Gangsta', 'Top 40', 'Christian Rap', 'Pop/Funk', 'Jungle', 'Native American', \
			'Cabaret', 'New Wave', 'Psychadelic', 'Rave', 'Showtunes', 'Trailer', 'Lo-Fi', 'Tribal', \
			'Acid Punk', 'Acid Jazz', 'Polka', 'Retro', 'Musical', 'Rock & Roll', 'Hard Rock', 'Folk', \
			'Folk/Rock', 'National Folk', 'Swing', 'Fusion', 'Bebob', 'Latin', 'Revival', 'Celtic', \
			'Bluegrass', 'Avantgarde', 'Gothic Rock', 'Progress. Rock', 'Psychadel. Rock', 'Symphonic Rock', \
			'Slow Rock', 'Big Band', 'Chorus', 'Easy Listening', 'Acoustic', 'Humour', 'Speech', 'Chanson', \
			'Opera', 'Chamber Music', 'Sonata', 'Symphony', 'Booty Bass', 'Primus', 'Porn Groove', 'Satire', \
			'Slow Jam', 'Club', 'Tango', 'Samba', 'Folklore', 'Ballad', 'Power Ballad', 'Rhythmic Soul', \
			'Freestyle', 'Duet', 'Punk Rock', 'Drum Solo', 'A Capella', 'Euro-House', 'Dance Hall', 'Goa', \
			'Drum & Bass', 'Club-House', 'Hardcore', 'Terror', 'Indie', 'BritPop', 'Negerpunk', 'Polsk Punk', \
			'Beat', 'Christian Gangsta Rap', 'Heavy Metal', 'Black Metal', 'Crossover', 'Contemporary Christian', \
			'Christian Rock', 'Merengue', 'Salsa', 'Thrash Metal', 'Anime', 'Jpop', 'Synthpop')
		
		# skipping these steps if its a dry run
		if not options.dryRun:
			# discarding anything not in the list of genres.
			if tagGenre not in genreList:
				tagGenre = ""
			
			# If there is no title tag, set it to the filename (without extension).  Otherwise the file will show nothing in XMMS.
			# Must test this, crazy filenames might cause problems with some encoders.
			if not tagName:
				print "No title tag, setting the title of song to the filename"
				filePathless = os.path.split(file)[1]
				fileBaseName = os.path.splitext(filePathless)[0]
				
				tagName = fileBaseName
			
			# setting the bitrate of the output file the same as the input file unless
			# a bitrate is specified as an option.  Bitrate not used for wav or flac.
			if not options.bitrate and not (options.wavOutput or options.flacOutput):
				try:
					# nasty syntax but handles casting of the string 128.0000 to an int (example).
					options.bitrate = int(float(inBitrate))
					
				except (KeyboardInterrupt, SystemExit):
					gracefulExit()
				
				except:
					print "cannot determine bitrate of input, setting output to 128 kbps."
					options.bitrate = 128
			if options.encodeOption:
				options.bitrate = None
				print "Custom encoder options specified, ignoring bitrate option if specified."
			
			
			# optional normalization of the wav file
			if options.normalize:
				print "normalizing intermediate wav file"
				normalizeString = ('%s "%s"' % (NORMALIZE, tempFile))
				normalizeInfo = runPopen(normalizeString, options.verbose)
				
			
		# setting the output filename by replacing the extension with the new one determined by the 
		# output format option.
		if options.destDir:
			# using the destinationDir function to handle making new directories and the new path names.
			# dont want to make new directories if its only a dry run.
			newOutFilePath = destinationDir(file, options.destDir, options.dryRun)
				
			outFile = os.path.splitext(newOutFilePath)[0] + outFileExtension
		else:
			outFile = os.path.splitext(file)[0] + outFileExtension
		
		
		# dry run, output info to terminal
		bitrateStr = ""
		if options.dryRun:
			print "Input File:", file, "\nOutput File:", outFile
		
		# writing to an ogg file	
		elif options.oggOutput:
			print "encoding:", outFile
			if options.bitrate:
				bitrateStr = "-b " + str(options.bitrate)
# 			# converting from wav to ogg with some tag info included
			encodeString = ('%s -t "%s" -a "%s" -G "%s" -d "%s" -l "%s" %s %s "%s" -o "%s"' % \
					(OGGENC, tagName, tagAuthor, tagGenre, tagDate, tagAlbum, bitrateStr, options.encodeOption, tempFile, outFile))
			
			runPopen(encodeString, options.verbose)
					
		elif options.mp3Output:
			print "encoding:", outFile
			if options.bitrate:
				bitrateStr = "-b " + str(options.bitrate)
			# converting wav to mp3
			encodeString = ('%s --tt "%s" --ta "%s" --tg "%s" --ty "%s" --tl "%s" -h %s %s "%s" -o "%s"' % \
				(LAME, tagName, tagAuthor, tagGenre, tagDate, tagAlbum, bitrateStr, options.encodeOption, tempFile, outFile))
			
			runPopen(encodeString, options.verbose)
				
				
		elif options.wavOutput:
			print "outputting:", outFile
			# just copying the tempfile (wav) to the output filename - easy.
			shutil.copyfile(tempFile, outFile)
			
		elif options.flacOutput:
			print "encoding:", outFile
			# writing out from wav to flac format.
			encodeString = ('%s -f "%s" %s -o "%s"' % (FLAC, tempFile, options.encodeOption, outFile))
			
			runPopen(encodeString, options.verbose)
			
			## Updating tags with metaflac
			flacTagString = ('%s --set-tag=TITLE="%s" --set-tag=ARTIST="%s" --set-tag=ALBUM="%s" --set-tag=DATE="%s" --set-tag=GENRE="%s" "%s"' \
				% (METAFLAC, tagName, tagAuthor, tagAlbum, tagDate, tagGenre, outFile))
			
			runPopen(flacTagString, options.verbose)

		else:
                        print "No output format chosen, output file not written.  Please select output format."

		# dangerous option here, deleting the input file after conversion
		# Todo: only run these two cleanup items if no exceptions have been raised.
		if options.delSource:
			# if the output file doesn't exist, something went wrong and we should not delete the source
			# even if --delete is specified.
			if not os.path.isfile(outFile):
				print "Output file does not exist, input file will not be deleted."
				continue
			
			# if the new output filename is the same as the original input, dont delete original
			# because it has already been overwritten by the new one.
			if file == outFile:
				continue
		
			# removing the input file
			try:
				os.remove(file)
				
			# exiting normally if control-c is hit instead of deleting file!
			except (KeyboardInterrupt, SystemExit):
        			gracefulExit()
			
			except:
				print "could not remove input file:", file
		
		# manually removing tempfiles just to make sure the disk doesn't get cluttered

		try:
			# only trying to remove the tempfile if it exists.  This will make the dry run output clearer.
			if os.path.isfile(tempFile):
				os.remove(tempFile)
			
		except (KeyboardInterrupt, SystemExit):
			gracefulExit()
		
		except:
			print "error: could not remove tempfile"
		
		print "----"
