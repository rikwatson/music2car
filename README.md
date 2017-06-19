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