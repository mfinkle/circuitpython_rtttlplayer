from micropython import const
import pwmio

import adafruit_rtttl

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
            piano_note, note_duration = adafruit_rtttl._parse_note(note, self.duration, self.octave)
            if piano_note in adafruit_rtttl.PIANO:
                note_frequency = int(adafruit_rtttl.PIANO[piano_note])
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
