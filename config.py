# -*- coding: utf-8 -*-

import sys, os
sys.path.insert(0, '/home/pi/berryconda3/envs/py36/lib/python3.6/site-packages')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'midi-0.2.3-py3.7.egg'))


# For 'sys.path.insert'
NULL = None

# For networks
APP_IP = '0.0.0.0' # for server frontend
SERVER_IP = '192.168.8.7' # for server backend
PI_IP = '192.168.8.8' # for raspberry pi
MC_IP = PI_IP #'169.254.133.0' # for mcpi
PORT = '2022' # for server frontend

# For net_channel
CH_PORT = '20220'
PASSWD = 'OWGBJ2022_MC'
NETCH_DEBUG = True

# For OLED
OLED_W = 128
OLED_H = 64
FONT_DIR = '/home/pi/Fonts/'
OLED_FONT = 'simfang.ttf' # If no font available, set this to None
OLED_FSIZE = 16

# For jianlu
ATHLETE_NAME = 'RyanWei'

# For TCS3200
TCS_PINS = {
'led':18,
'out':17,
's0':23,
's1':24,
's2':27,
's3':22,
}
BUTTON_PIN = 4

# For car
DETECT_INT = 0.3
MAX_SPEED = 10
PWM_PERITER = 50
CAR_PIN = (None,
	6, 13, 19, 26, 12, 16, 20, 21 # From IN1 to IN8
)
MINECART_NAME = 'entity.MinecartRideable.name'
CAR_ENDP = (0, 160)
CAR_SL = 80

# For music
MIDI_DIR = './midi_src'
PIANO_POS = (42, 1, 226)
BUZ_PINS = (10, 9, 11, 5, 25, 8, 7)
SAME_NOTE = True # Whether buzzer and mc share the same note.

if isinstance(FONT_DIR, str) and FONT_DIR[-1] != '/':
	FONT_DIR += '/'