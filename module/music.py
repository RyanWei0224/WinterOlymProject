# -*- coding: utf-8 -*-

from init import NULL
from config import MC_IP, MIDI_DIR, PIANO_POS, BUZ_PINS, SAME_NOTE

import time
import os
from multiprocessing import Process, SimpleQueue as MPQueue

from mcpi.minecraft import Minecraft
import RPi.GPIO as GPIO

from lib.oled import OLED
from lib.music_lib import MCAPI as MCPiano, MIDINotes, MultiBuzzer as Buzzers
# LocalAPI


def oled_lyric(q):
	oled = OLED()
	try:
		while True:
			s = q.get()
			if s is None:
				break
			if isinstance(s, tuple):
				font = s[0]
				_ = oled.set_font(font)
			else:
				_ = oled.print(s)
	except KeyboardInterrupt:
		pass
	except Exception as e:
		print('[oled_lyric] Exception: "{}" of type {}'.format(e, type(e)))
	oled.clear()

def load_midi(buz):
	midis = dict()
	try:
		ls = os.listdir(MIDI_DIR)
	except OSError:
		print("[load_midi] Warning: Cannot list MIDI_DIR. No midi detected.")
		ls = ()

	for file in ls:
		if not file.endswith('.mid'):
			continue
		full_fname = os.path.join(MIDI_DIR, file)
		if not os.path.isfile(full_fname):
			continue
		notes = MIDINotes(full_fname, SAME_NOTE)
		if not notes.valid:
			continue
		try:
			note_list, num_ch = notes.full_events(buz.proc_buz)
			font = notes.lyric_font
			midi_len = notes.length
		except Exception:
			continue
		print("[load_midi] INFO: Successfully loads '{}' ({} channels)".format(file, num_ch))
		midis[file[:-4]] = (note_list, font, midi_len)
		if len(midis) > 5:
			break
	return midis

def init(mc):
	mc = MCPiano(mc, *PIANO_POS)
	buz = Buzzers(BUZ_PINS)
	print("[music] Loading midi...")
	midis = load_midi(buz)
	print("[music] Successfully loads {} midis.".format(len(midis)))
	oled_q = MPQueue()
	oled_proc = Process(target = oled_lyric, args = (oled_q,))
	oled_proc.start()
	return mc, buz, midis, oled_proc, oled_q

def main(mc, buz, midis, oled_proc, oled_q):
	try:
		ls = list(midis.keys())
		for i, name in enumerate(ls):
			print('{}\t{}'.format(i, name))
		while True:
			i = int(input())
			note_list, font, midi_len = midis[ls[i]]
			oled_q.put((font,))
			mc.print('Length: %.2f' % midi_len)
			#mc.print('Start playing in {} seconds.'.format(3))
			#time.sleep(3)
			try:
				MIDINotes.play(note_list, mc, buz, oled_q)
			except KeyboardInterrupt:
				buz.reset()
			mc.print('Thanks for listening.')
	except KeyboardInterrupt:
		pass
	except Exception as e:
		print('[music] {} occurred: "{}"'.format(type(e), e))
		raise e


	buz.stop()
	oled_q.put(None)
	oled_proc.join()

if __name__ == '__main__':
	mc = Minecraft.create(address = MC_IP)
	args = init(mc)
	main(*args)
	GPIO.cleanup()
