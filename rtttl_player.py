from micropython import const
import pwmio

try:
    from typing import Optional, Union, Tuple, List
except ImportError:
    pass

try:
    from time import monotonic_ns

    monotonic_ns()  # Test monotonic_ns in 6.x
    def monotonic_ms():
        """
        Return monotonic time in milliseconds.
        """
        return monotonic_ns() // NANOS_PER_MS
except (ImportError, NotImplementedError):
    import time

    def monotonic_ms():
        """
        Implementation of monotonic_ms for platforms without time.monotonic_ns
        """
        return int(time.monotonic() * MS_PER_SECOND)

NANOS_PER_MS = const(1000000)
MS_PER_SECOND = const(1000)

# Copy of the notes and note parsing code from Adafruit RTTTL code
# https://github.com/adafruit/Adafruit_CircuitPython_RTTTL
PIANO = {
    "4c": 261.626,
    "4c#": 277.183,
    "4d": 293.665,
    "4d#": 311.127,
    "4e": 329.628,
    "4f": 349.228,
    "4f#": 369.994,
    "4g": 391.995,
    "4g#": 415.305,
    "4a": 440,
    "4a#": 466.164,
    "4b": 493.883,
    "5c": 523.251,
    "5c#": 554.365,
    "5d": 587.330,
    "5d#": 622.254,
    "5e": 659.255,
    "5f": 698.456,
    "5f#": 739.989,
    "5g": 783.991,
    "5g#": 830.609,
    "5a": 880,
    "5a#": 932.328,
    "5b": 987.767,
    "6c": 1046.50,
    "6c#": 1108.73,
    "6d": 1174.66,
    "6d#": 1244.51,
    "6e": 1318.51,
    "6f": 1396.91,
    "6f#": 1479.98,
    "6g": 1567.98,
    "6g#": 1661.22,
    "6a": 1760,
    "6a#": 1864.66,
    "6b": 1975.53,
    "7c": 2093,
    "7c#": 2217.46,
}

def _parse_note(note: str, duration: int = 2, octave: int = 6) -> Tuple[str, float]:
    note = note.strip()
    piano_note = None
    note_duration = duration
    if note[0].isdigit() and note[1].isdigit():
        note_duration = int(note[:2])
        piano_note = note[2]
    elif note[0].isdigit():
        note_duration = int(note[0])
        piano_note = note[1]
    else:
        piano_note = note[0]
    if "." in note:
        note_duration *= 1.5
    if "#" in note:
        piano_note += "#"
    note_octave = str(octave)
    if note[-1].isdigit():
        note_octave = note[-1]
    piano_note = note_octave + piano_note
    return piano_note, note_duration


class RTTTLSong:
    def __init__(self, rtttl, octave=None, duration=None, tempo=None, loops=0):
        self.octave = octave
        self.duration = duration
        self.tempo = tempo
        self.name, defaults, self.tune = rtttl.lower().split(':')
        for default in defaults.split(','):
            if default[0] == 'd' and not self.duration:
                self.duration = int(default[2:])
            elif default[0] == 'o' and not self.octave:
                self.octave = default[2:]
            elif default[0] == 'b' and not tempo:
                self.tempo = int(default[2:])
        if not self.octave:
            self.octave = 6
        if not self.duration:
            self.duration = 4
        if not self.tempo:
            self.tempo = 63

        self._loops = loops
        self._loop_count = 0

        self._notes = []
        self._notes_index = 0
        notes = self.tune.split(',')
        for note in notes:
            piano_note, note_duration = _parse_note(note, self.duration, self.octave)
            if piano_note in PIANO:
                note_frequency = int(PIANO[piano_note])
            else:
                note_frequency = None
            self._notes.append((note_frequency, note_duration))

    def next_note(self):
        note = self._notes[self._notes_index]
        self._notes_index += 1

        if self.complete:
            self._loop_count += 1
            if self._loops == -1 or self._loop_count <= self._loops:
                self.reset()

        return note

    @property
    def complete(self):
        return self._notes_index >= len(self._notes)

    def reset(self):
        self._notes_index = 0


class RTTTLPlayer:
    TONE_ON = 0
    TONE_OFF = 1

    TONE_GAP = 20

    def __init__(self, pin):
        self._paused = False
        self._complete = False
        self._next_update_time = monotonic_ms()
        self._next_update_state = self.TONE_ON
        self._also_notify = []
        self._song = None

        self._base_tone = pwmio.PWMOut(pin, duty_cycle=0, variable_frequency=True)

    def load(self, song):
        self.reset()
        self._song = song

    def on_complete(self):
        self._complete = True
        for callback in self._also_notify:
            callback(self)

    def add_complete_receiver(self, callback):
        self._also_notify.append(callback)

    def play(self):
        if self._paused or self._complete or self._song is None:
            return False

        now = monotonic_ms()
        if now < self._next_update_time:
            return False

        if self._song.complete:
            # We reached the end of a cycle
            self._base_tone.duty_cycle = 0
            self.on_complete()
            return False

        if self._next_update_state == self.TONE_ON:
            # Play the 'on' part of a note
            note_frequency, note_duration = self._song.next_note()
            if note_frequency is not None:
                self._base_tone.frequency = note_frequency
                self._base_tone.duty_cycle = 2 ** 15

            self._next_update_time = now + int(4 / note_duration * 60 * 1000 / self._song.tempo)
            self._next_update_state = self.TONE_OFF
        else:
            # Play the 'off' part of a note
            self._base_tone.duty_cycle = 0
            self._next_update_time = now + self.TONE_GAP
            self._next_update_state = self.TONE_ON

        return True

    def stop(self):
        self._complete = True

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def reset(self):
        self._complete = False
        self._paused = False
        if self._song is not None:
            self._song.reset()

# import board
# rtttl_song = RTTTLSong(find('Smurfs'))
# rtttl_player = RTTTLPlayer(board.D3)
# rtttl_player.load(rtttl_song)
# while True:
#     rtttl_player.play()
