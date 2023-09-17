## Introduction
Adafruit's RTTTL library supports parsing and playing RTTTL ringtones. Playback is synchronus, so the program is blocked while playing the RTTTL song. CircuitPython RTTTLPlayer supports timing slicing, so the program can support other tasks while playing a song.

## Dependencies
This code depends on:

* [Adafruit CircuitPython](https://github.com/adafruit/circuitpython)

Please make sure all dependencies are available on the CircuitPython filesystem.

## Usage Example
```
import board

from rtttl_player import RTTTLSong, RTTTLPlayer
import rtttl_songs

rtttl_song = RTTTLSong(rtttl_songs.find('Smurfs'))
rtttl_player = RTTTLPlayer(board.D3)
rtttl_player.load(rtttl_song)
while True:
    rtttl_player.play()
```

## What's Included
**rtttl_player.py**

* `RTTTLSong`:
* `RTTTLPlayer`:

**rtttl_songs.py**

* `SONGS`: List of RTTTL songs collected from various places. Use this as an idea for building your own library of songs.
* `find`: Helper method used to find an RTTTL song by name from the `SONGS` list.