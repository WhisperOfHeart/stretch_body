#!/usr/bin/env python
import pyaudio
import wave
import numpy as np
import usb.core
import struct
import time
import os
import deepspeech
from stretch_body.hello_utils import *
import stretch_body.robot as hello_robot
print_stretch_re_use()


# parameter list
# name: (id, offset, type, max, min , r/w, info)
PARAMETERS = {
    'AECFREEZEONOFF': (18, 7, 'int', 1, 0, 'rw', 'Adaptive Echo Canceler updates inhibit.', '0 = Adaptation enabled', '1 = Freeze adaptation, filter only'),
    'AECNORM': (18, 19, 'float', 16, 0.25, 'rw', 'Limit on norm of AEC filter coefficients'),
    'AECPATHCHANGE': (18, 25, 'int', 1, 0, 'ro', 'AEC Path Change Detection.', '0 = false (no path change detected)', '1 = true (path change detected)'),
    'RT60': (18, 26, 'float', 0.9, 0.25, 'ro', 'Current RT60 estimate in seconds'),
    'HPFONOFF': (18, 27, 'int', 3, 0, 'rw', 'High-pass Filter on microphone signals.', '0 = OFF', '1 = ON - 70 Hz cut-off', '2 = ON - 125 Hz cut-off', '3 = ON - 180 Hz cut-off'),
    'RT60ONOFF': (18, 28, 'int', 1, 0, 'rw', 'RT60 Estimation for AES. 0 = OFF 1 = ON'),
    'AECSILENCELEVEL': (18, 30, 'float', 1, 1e-09, 'rw', 'Threshold for signal detection in AEC [-inf .. 0] dBov (Default: -80dBov = 10log10(1x10-8))'),
    'AECSILENCEMODE': (18, 31, 'int', 1, 0, 'ro', 'AEC far-end silence detection status. ', '0 = false (signal detected) ', '1 = true (silence detected)'),
    'AGCONOFF': (19, 0, 'int', 1, 0, 'rw', 'Automatic Gain Control. ', '0 = OFF ', '1 = ON'),
    'AGCMAXGAIN': (19, 1, 'float', 1000, 1, 'rw', 'Maximum AGC gain factor. ', '[0 .. 60] dB (default 30dB = 20log10(31.6))'),
    'AGCDESIREDLEVEL': (19, 2, 'float', 0.99, 1e-08, 'rw', 'Target power level of the output signal. ', '[-inf .. 0] dBov (default: -23dBov = 10log10(0.005))'),
    'AGCGAIN': (19, 3, 'float', 1000, 1, 'rw', 'Current AGC gain factor. ', '[0 .. 60] dB (default: 0.0dB = 20log10(1.0))'),
    'AGCTIME': (19, 4, 'float', 1, 0.1, 'rw', 'Ramps-up / down time-constant in seconds.'),
    'CNIONOFF': (19, 5, 'int', 1, 0, 'rw', 'Comfort Noise Insertion.', '0 = OFF', '1 = ON'),
    'FREEZEONOFF': (19, 6, 'int', 1, 0, 'rw', 'Adaptive beamformer updates.', '0 = Adaptation enabled', '1 = Freeze adaptation, filter only'),
    'STATNOISEONOFF': (19, 8, 'int', 1, 0, 'rw', 'Stationary noise suppression.', '0 = OFF', '1 = ON'),
    'GAMMA_NS': (19, 9, 'float', 3, 0, 'rw', 'Over-subtraction factor of stationary noise. min .. max attenuation'),
    'MIN_NS': (19, 10, 'float', 1, 0, 'rw', 'Gain-floor for stationary noise suppression.', '[-inf .. 0] dB (default: -16dB = 20log10(0.15))'),
    'NONSTATNOISEONOFF': (19, 11, 'int', 1, 0, 'rw', 'Non-stationary noise suppression.', '0 = OFF', '1 = ON'),
    'GAMMA_NN': (19, 12, 'float', 3, 0, 'rw', 'Over-subtraction factor of non- stationary noise. min .. max attenuation'),
    'MIN_NN': (19, 13, 'float', 1, 0, 'rw', 'Gain-floor for non-stationary noise suppression.', '[-inf .. 0] dB (default: -10dB = 20log10(0.3))'),
    'ECHOONOFF': (19, 14, 'int', 1, 0, 'rw', 'Echo suppression.', '0 = OFF', '1 = ON'),
    'GAMMA_E': (19, 15, 'float', 3, 0, 'rw', 'Over-subtraction factor of echo (direct and early components). min .. max attenuation'),
    'GAMMA_ETAIL': (19, 16, 'float', 3, 0, 'rw', 'Over-subtraction factor of echo (tail components). min .. max attenuation'),
    'GAMMA_ENL': (19, 17, 'float', 5, 0, 'rw', 'Over-subtraction factor of non-linear echo. min .. max attenuation'),
    'NLATTENONOFF': (19, 18, 'int', 1, 0, 'rw', 'Non-Linear echo attenuation.', '0 = OFF', '1 = ON'),
    'NLAEC_MODE': (19, 20, 'int', 2, 0, 'rw', 'Non-Linear AEC training mode.', '0 = OFF', '1 = ON - phase 1', '2 = ON - phase 2'),
    'SPEECHDETECTED': (19, 22, 'int', 1, 0, 'ro', 'Speech detection status.', '0 = false (no speech detected)', '1 = true (speech detected)'),
    'FSBUPDATED': (19, 23, 'int', 1, 0, 'ro', 'FSB Update Decision.', '0 = false (FSB was not updated)', '1 = true (FSB was updated)'),
    'FSBPATHCHANGE': (19, 24, 'int', 1, 0, 'ro', 'FSB Path Change Detection.', '0 = false (no path change detected)', '1 = true (path change detected)'),
    'TRANSIENTONOFF': (19, 29, 'int', 1, 0, 'rw', 'Transient echo suppression.', '0 = OFF', '1 = ON'),
    'VOICEACTIVITY': (19, 32, 'int', 1, 0, 'ro', 'VAD voice activity status.', '0 = false (no voice activity)', '1 = true (voice activity)'),
    'STATNOISEONOFF_SR': (19, 33, 'int', 1, 0, 'rw', 'Stationary noise suppression for ASR.', '0 = OFF', '1 = ON'),
    'NONSTATNOISEONOFF_SR': (19, 34, 'int', 1, 0, 'rw', 'Non-stationary noise suppression for ASR.', '0 = OFF', '1 = ON'),
    'GAMMA_NS_SR': (19, 35, 'float', 3, 0, 'rw', 'Over-subtraction factor of stationary noise for ASR. ', '[0.0 .. 3.0] (default: 1.0)'),
    'GAMMA_NN_SR': (19, 36, 'float', 3, 0, 'rw', 'Over-subtraction factor of non-stationary noise for ASR. ', '[0.0 .. 3.0] (default: 1.1)'),
    'MIN_NS_SR': (19, 37, 'float', 1, 0, 'rw', 'Gain-floor for stationary noise suppression for ASR.', '[-inf .. 0] dB (default: -16dB = 20log10(0.15))'),
    'MIN_NN_SR': (19, 38, 'float', 1, 0, 'rw', 'Gain-floor for non-stationary noise suppression for ASR.', '[-inf .. 0] dB (default: -10dB = 20log10(0.3))'),
    'GAMMAVAD_SR': (19, 39, 'float', 1000, 0, 'rw', 'Set the threshold for voice activity detection.', '[-inf .. 60] dB (default: 3.5dB 20log10(1.5))'),
    # 'KEYWORDDETECT': (20, 0, 'int', 1, 0, 'ro', 'Keyword detected. Current value so needs polling.'),
    'DOAANGLE': (21, 0, 'int', 359, 0, 'ro', 'DOA angle. Current value. Orientation depends on build configuration.')
}


class Tuning:
    TIMEOUT = 100000

    def __init__(self, dev):
        self.dev = dev

    def write(self, name, value):
        try:
            data = PARAMETERS[name]
        except KeyError:
            return

        if data[5] == 'ro':
            raise ValueError('{} is read-only'.format(name))

        id = data[0]

        # 4 bytes offset, 4 bytes value, 4 bytes type
        if data[2] == 'int':
            payload = struct.pack(b'iii', data[1], int(value), 1)
        else:
            payload = struct.pack(b'ifi', data[1], float(value), 0)

        self.dev.ctrl_transfer(
            usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
            0, 0, id, payload, self.TIMEOUT)

    def read(self, name):
        try:
            data = PARAMETERS[name]
        except KeyError:
            return

        id = data[0]

        cmd = 0x80 | data[1]
        if data[2] == 'int':
            cmd |= 0x40

        length = 8

        response = self.dev.ctrl_transfer(
            usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
            0, cmd, id, length, self.TIMEOUT)

        response = struct.unpack(b'ii', response.tostring())

        if data[2] == 'int':
            result = response[0]
        else:
            result = response[0] * (2.**response[1])

        return result

    def set_vad_threshold(self, db):
        self.write('GAMMAVAD_SR', db)

    def is_voice(self):
        return self.read('VOICEACTIVITY')

    @property
    def direction(self):
        return self.read('DOAANGLE')

    @property
    def version(self):
        return self.dev.ctrl_transfer(
            usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
            0, 0x80, 0, 1, self.TIMEOUT)[0]

    def close(self):
        """
        close the interface
        """
        usb.util.dispose_resources(self.dev)


def get_respeaker_device_id():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    num_devices = info.get('deviceCount')

    device_id = -1
    for i in range(num_devices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            if "ReSpeaker" in p.get_device_info_by_host_api_device_index(0, i).get('name'):
                device_id = i

    return device_id


RESPEAKER_RATE = 16000
RESPEAKER_CHANNELS = 6 # must flash 6_channels_firmware.bin first
RESPEAKER_WIDTH = 2
RESPEAKER_INDEX = get_respeaker_device_id()
CHUNK = 1024

small_move_m=.01
small_rotate_rad=deg_to_rad(1.0)
small_lift_move_m=.01
small_arm_move_m=.010

robot=hello_robot.Robot()


def record_audio(seconds=3):
    p = pyaudio.PyAudio()
    stream = p.open(rate=RESPEAKER_RATE,
                    format=p.get_format_from_width(RESPEAKER_WIDTH),
                    channels=RESPEAKER_CHANNELS,
                    input=True,
                    input_device_index=RESPEAKER_INDEX)

    frames = []
    for i in range(0, int(RESPEAKER_RATE / CHUNK * seconds)):
        data = stream.read(CHUNK)
        a = np.fromstring(data,dtype=np.int16)[0::6] # extracts fused channel 0
        frames.append(a.tostring())

    stream.stop_stream()
    stream.close()
    p.terminate()

    return frames


def save_wav(frames, fname="output.wav"):
    p = pyaudio.PyAudio()
    wf = wave.open(fname, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(p.get_sample_size(p.get_format_from_width(RESPEAKER_WIDTH)))
    wf.setframerate(RESPEAKER_RATE)
    wf.writeframes(b''.join(frames))
    wf.close()


def play_audio(frames):
    p = pyaudio.PyAudio()
    stream = p.open(rate=RESPEAKER_RATE,
                    format=p.get_format_from_width(RESPEAKER_WIDTH),
                    channels=1,
                    output=True)

    for f in frames:
        stream.write(f, CHUNK)

    stream.stop_stream()
    stream.close()
    p.terminate()

    return frames

def menu():
    print '--------------'
    print 'Mobile Base'
    print 'say "base forward" / "back" / "left" / "right"'
    print
    print 'Arm'
    print 'say "arm up" / "down" / "in" / "out"'
    print
    print 'Head'
    print 'say "ahead" / "back" / "tool" / "wheels"'
    print
    print 'System'
    print 'CTRL + C : quit'
    print '--------------'

def move_robot(cmd):
    valid = False

    # mobile base commands
    if cmd == "base forward" or "forward" in cmd:
        robot.base.translate_by(small_move_m)
        valid = True
    if cmd == "base back" or "back" in cmd:
        robot.base.translate_by(-1*small_move_m)
        valid = True
    if cmd == "base left" or "left" in cmd:
        robot.base.rotate_by(small_rotate_rad)
        valid = True
    if cmd == "base right" or "right" in cmd:
        robot.base.rotate_by(-1*small_rotate_rad)
        valid = True

    # lift commands
    if cmd == "arm up" or "up" in cmd:
        robot.lift.move_by(small_lift_move_m)
        valid = True
    if cmd == "arm down" or "down" in cmd:
        robot.lift.move_by(-1*small_lift_move_m)
        valid = True

    # arm commands
    if cmd == "arm in" or "in" in cmd:
        robot.arm.move_by(-1*small_arm_move_m)
        valid = True
    if cmd == "arm out" or "out" in cmd:
        robot.arm.move_by(small_arm_move_m)
        valid = True

    # head commands
    if cmd == "ahead":
        robot.head.pose('ahead')
        valid = True
    if cmd == "back":
        robot.head.pose('back')
        valid = True
    if cmd == "tool":
        robot.head.pose('tool')
        valid = True
    if cmd == "wheels":
        robot.head.pose('wheels')
        valid = True

    robot.push_command()

    if not valid:
        print "Unable to interpret: " + cmd
    else:
        print "Understood: " + cmd

if __name__ == "__main__":
    data_path = os.environ['HELLO_FLEET_PATH']
    if not os.path.isdir(os.path.join(data_path, "models/deepspeech-0.6.1-models/")):
        print "Missing DeepSpeech model in stretch_user/"

    BEAM_WIDTH = 500
    LM_ALPHA = 0.75
    LM_BETA = 1.85
    model_path = os.path.join(data_path, "models/deepspeech-0.6.1-models/output_graph.tflite")
    lm_path = os.path.join(data_path, "models/deepspeech-0.6.1-models/lm.binary")
    trie_path = os.path.join(data_path, "models/deepspeech-0.6.1-models/trie")
    model = deepspeech.Model(model_path, BEAM_WIDTH)
    model.enableDecoderWithLM(lm_path, trie_path, LM_ALPHA, LM_BETA)
    dev = usb.core.find(idVendor=0x2886, idProduct=0x0018)
    robot.startup()

    printed_wait_statement = False
    if dev:
        respeaker = Tuning(dev)
        while True:
            try:
                if not printed_wait_statement and respeaker.is_voice() == 0:
                    menu()
                    print "\n* waiting for audio..."
                    printed_wait_statement = True
                else:
                    if respeaker.is_voice() == 1:
                        print "* recording 2 seconds"
                        frames = record_audio(seconds=2)
                        print "* done"
                        time.sleep(1)
                        print "* analyzing"
                        stream_context = model.createStream()
                        # for i in range(12):
                        #     model.feedAudioContent(stream_context, np.frombuffer(frames[len(frames) - 1], np.int16))
                        for f in frames:
                            if f is not None:
                                model.feedAudioContent(stream_context, np.frombuffer(f, np.int16))
                        text = model.finishStream(stream_context)
                        move_robot(text)
                        print "* done"
                        time.sleep(1)
                        printed_wait_statement = False
                    time.sleep(0.01)
            except (ThreadServiceExit,KeyboardInterrupt, SystemExit):
                robot.stop()
                break