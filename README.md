# music2car

Script(s) to copy & convert selected audio files to a USB for in-car playback

The rational is that you have a significant number of audio files stored in a lossless (=large files) format and you want to copy selected tracks onto a USB stick for playback on an in-car stereo. Whilst copying the audio files, you also need to convert them to MP3 format because the chances are, your car can't plat FLAC or ALAC - an even if it did they would be too large.

So, the problem splits itself nicely into two.

 1. Select the tracks we want to copy
 2. Convert the selected tracks from lossless to lossy.

As we're on a Mac, we can use the Finder's Tag'ing facility to tag all the albums, tracks, artists we want to copy.

The stratergy is that we use tags to signify the root of the track(s) we want. So if we want all the `Roger Waters` albums we just tag his name. If we just want a single album, we just tag that single folder and if we just want a single track (Hello one-hit-wonder) then we just that individual file.

## Prerequisits

```bash
brew install tag, ffmpeg
```

## Usage

```bash
tag --find '*' /Volumes/Media/Music
```

This lists all the files and folders in the music folder which match the tag specified (in our case we match all of them via the wildcard).

### xargs

Use `-0` with `xargs -0`

```bash
tag -0 --find 'TODO' . | xargs -0
```

# XLD

The following all work

```bash
./xld -f mp3 -o Tony\ Anderson\ -\ All\ Is\ Not\ Lost.mp3 Tony\ Anderson\ -\ All\ Is\ Not\ Lost.m4a
./xld -f mp3 -o "03. The Last Refugee.mp3" "03. The Last Refugee.flac"
./xld -f mp3 08\ -\ Travelin\ On.m4a 08\ -\ Travelin\ On.mp3
```

## converter.sh

From [Bliss](https://www.blisshq.com/music-library-management-blog/2017/08/29/converting-music-libraries-macos/)

Usage:

```
converter.sh /path/to/source /path/to/destination aac
```


```bash
#!/bin/bash

ROOT_SOURCE_DIR=$1
ROOT_DEST_DIR=$2
TARGET_FORMAT=$3

# ensure the destination directory structure exists
mkdir -p $ROOT_DEST_DIR

# loop through all files in the source directory
find "${ROOT_SOURCE_DIR}" -type f \( -name "*" \) -print0 | while read -d $'\0' FULL_SOURCE_PATH; do

  # break the source file path down
  DIR=$(dirname "$FULL_SOURCE_PATH")
  FILENAME=$(basename "$FULL_SOURCE_PATH")
  EXTENSION="${FILENAME##*.}"
  FILENAME="${FILENAME%.*}"

  # calculate the destination file path 
  DEST_DIR=${DIR#${ROOT_SOURCE_DIR}}
  FULL_DEST_DIR=${ROOT_DEST_DIR}${DEST_DIR}

  # skip this file if the destination file already exists
  if ls "${FULL_DEST_DIR}/${FILENAME}"* 1> /dev/null 2>&1; then
    echo "skipping ${FILENAME}"
  else
    mkdir -p "${FULL_DEST_DIR}"
    echo "converting ${FILENAME} to ${FULL_DEST_DIR}"

    # Send the file to XLD for conversion. 
    # If conversion fails, we'll copy it over instead
    if ! xld -o "${FULL_DEST_DIR}" "${FULL_SOURCE_PATH}" -f $3; then
      echo "XLD could not convert ${FULL_SOURCE_PATH} - Coyping instead"
      cp "${FULL_SOURCE_PATH}" "${FULL_DEST_DIR}"
    fi
  fi

done
```

# Cover Art

Embed `Folder.jpg` as album cover into example.mp3 with `mutagen`:

```python
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error

audio = MP3('example.mp3', ID3=ID3)

# add ID3 tag if it doesn't exist
try:
    audio.add_tags()
except error:
    pass

audio.tags.add(
    APIC(
        encoding=3, # 3 is for utf-8
        mime='image/jpeg', # image/jpeg or image/png
        type=3, # 3 is for the cover image
        desc=u'Cover',
        data=open('Folder.jpg').read()
    )
)
audio.save()
```



 * http://khenriks.github.io/mp3fs/
 * https://ubuntuforums.org/showthread.php?t=1096665


```python
#!/usr/bin/env python

import os
import os.path
import sys

LAME_QUALITY = CBR 320

def escape_quotes(path):
    return path.replace('"', r'\"')


# Gets the tag of a flac file
def get_flac_tag(flac_file, tag):
    flac_file = os.path.abspath(flac_file)

    # Make sure the path exists and that the file exists
    if not os.path.exists(flac_file) or not os.path.isfile(flac_file):
        return ''

    flac_file = escape_quotes(flac_file)

    f = os.popen('metaflac --show-tag=%s "%s"' % (tag.upper(), flac_file))
    meta_out = f.read()
    f.close()

    try:
        return meta_out[meta_out.find('=') + 1:].strip()
    except:
        return ''


def encode_mp3(flac_file):
    mp3_file, ext = os.path.splitext(flac_file)
    wave_file = escape_quotes(mp3_file + '.wav')
    mp3_file = escape_quotes(mp3_file + '.mp3')
    flac_file = flac_file

    # Converts to wave
    os.system('flac -d -f "%s"' % escape_quotes(flac_file))

    year = get_flac_tag(flac_file, 'DATE')
    if year: year = year[:5]
    title = escape_quotes(get_flac_tag(flac_file, 'TITLE'))
    artist = escape_quotes(get_flac_tag(flac_file, 'ARTIST'))
    album = escape_quotes(get_flac_tag(flac_file, 'ALBUM'))
    track_number = int('0' + get_flac_tag(flac_file, 'TRACKNUMBER'))
    # Missing out GENRE because genre is stored a index in mp3 but as a string in flac

    command = 'lame -b 320 -V %d --tt "%s" --ta "%s" --tl "%s" --ty %s --tn %d "%s" "%s"' \
                % (LAME_QUALITY, title, artist, album, year, track_number, wave_file, mp3_file)

    # Converts wave to mp3 then deletes wave
    os.system(command)
    os.system('rm "%s"' % wave_file)


def main(argv):
    for i in argv:
        flac_file = i

        if not os.path.exists(flac_file) or not os.path.isfile(flac_file):
            print '%s is not found.' % (flac_file)
            sys.exit(1)

        encode_mp3(flac_file)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'usage: %s <flacfile(s)>' % (sys.argv[0])
        sys.exit(1)

    main(sys.argv[1:])
```


oops, sorry, I changed it from "2" (I had it set for vbr 2), but apparently it has to be an integer. So use 

LAME_QUALITY = 2
The "-b 320' part in red is what counts and should give you cbr 320 (just checked it)


