# -*- coding: utf-8 -*-

from config import NULL

import RPi.GPIO as GPIO

# MCAPI
from mcpi import block

# EventKind
from enum import Enum, auto

# MIDINotes
import os
import time
from collections import defaultdict
#from multiprocessing import Process as Proc, SimpleQueue as Queue
from threading import Thread as Proc
from queue import Queue
import midi

C2 = 2 ** (1/3)
C4 = 4 ** (1/3)
NOTE_12 = [1, 16384*C2/19683, 8*C2/9, 32/27,
64*C4/81, 4/3, 1024/729, 32*C2/27, 8192*C2/6561, 256*C4/243, 9/(4*C2), 4096/2187]

#NOTES = [440 * (2 ** ((note - 69)/12)) for note in range(120)]
NOTES = [261.6255653 * (2 ** ((note-60) // 12)) * NOTE_12[note % 12] for note in range(120)]

class LocalAPI:
	def __init__(self, *args, **kwargs):
		self.pr = False
		if 'pr' in kwargs:
			self.pr = kwargs[pr]

	def play_note(self, note, on):
		if self.pr:
			print("Turn {} note {} in MC.".format('on' if on else 'off', note))

	def print(self, msg):
		print("MC: {}".format(msg))

class MCAPI:
	NB_ID = block.NOTEBLOCK.id
	RS_ID = block.REDSTONE_BLOCK.id
	EMPTY_ID = block.AIR.id

	LOW_ID = block.WOOD.id
	HIGH_ID = block.GOLD_BLOCK.id

	NOTE_NUM = 72 + 1

	def __init__(self, mc, x, y, z, pr = False): # pr: For compatibility.
		self.mc = mc
		self.pl = mc.player
		self.x = x
		self.y = y
		self.z = z
		self.init()

	def init(self):
		x, y, z, mc = self.x, self.y, self.z, self.mc
		mc.setBlocks(x, y - 1, z - 2, x + 24, y + 1, z + 2, self.EMPTY_ID)
		mc.setBlocks(x, y - 1, z - 1, x + 24, y - 1, z - 1, self.LOW_ID)
		mc.setBlocks(x, y - 1, z + 1, x + 24, y - 1, z + 1, self.HIGH_ID)
		for note in range(25):
			for i in (-1, 0, 1):
				mc.setBlockWithNBT(x + note, y, z + i, self.NB_ID, 0, '{note:%d}' % note)
		'''
		mc.setBlocks(x, y - 4, z - 1, x + 24, y + 4, z + 1, 0)
		mc.setBlocks(x, y - 4, z, x + 24, y - 4, z, LOW_ID)
		mc.setBlocks(x, y + 2, z, x + 24, y + 2, z, HIGH_ID)
		for note in range(25):
			for i in [-3, 0, 3]:
				mc.setBlockWithNBT(x + note, y + i, z, NB_ID, 0, '{note:%d}' % note)
		'''
		'''
		for note in range(NOTE_NUM):
			mc.setBlockWithNBT(x + note, y, z, NB_ID, 0, '{note:%d}' % note)
		'''

	def rb_pos(self, note):
		y_shift = 0
		z_shift = 0
		if note < 24:
			#y_shift = -3
			y_shift = 0
			z_shift = -2
		elif note < 49:
			note -= 24
			#y_shift = 0
			y_shift = -1
			z_shift = 0
		else:
			note -= 48
			#y_shift = 3
			y_shift = 0
			z_shift = 2

		return self.x + note, self.y + y_shift, self.z + z_shift

	def play_note(self, note, on):
		self.mc.setBlock(*self.rb_pos(note), self.RS_ID if on else self.EMPTY_ID)

	def print(self, msg):
		pls = self.mc.getPlayerEntityIds()
		hasP = False
		for pid in pls:
			try:
				pl = CmdPlayer(self.mc.conn, playerId=pid)
				pos = pl.getTilePos()
				if pos.x<95 and pos.x>35 and pos.y<30 and pos.z<195 and pos.z>125:
					self.mc.postToChat(msg)
			except Exception:
				pass

class EventKind(Enum):
	MC = auto()
	BUZZER = auto()
	LYRIC = auto()

class MIDINotes:
	"""Extracts note info from MIDIFile"""
	def __init__(self, file, same_note = True):
		self.same_note = same_note
		self._valid = True
		try:
			self.process(file)
		except Exception as e:
			print("[MIDINotes] Exception occured while processing '{}':\n\t{}".format(file, e))
			self._valid = False

	@staticmethod
	def merge(ch_dicts):
		# Input : list of "{note:[(t, is_on)...]}"
		notes = {}
		for ch_dict in ch_dicts:
			notes |= ch_dict.keys()
		merged_dict = {n : [] for n in notes}
		for note in notes:
			ml = merged_dict[note]
			nlist = [(t, not is_on, i) for i, ch_dict in enumerate(ch_dicts) \
										for t, is_on in ch_dict.get(note, [])]
			nlist.sort()
			on_channel = set()
			last_t = -1
			for t, is_off, i in nlist:
				if is_off:
					assert i in on_channel, "Error: note {} is off before on!".format(note)
					on_channel.remove(i)
					if not on_channel:
						ml.append((t, False))
						assert last_t < t, "Error: internal error with code 1."
				else:
					on_channel.add(i)
					if last_t < t:
						ml.append((t, True))
						last_t = t

		return merged_dict

	def get_time(self, tick):
		real_time = 0
		last_t, last_r = self.tempos[0]
		for t, ratio in self.tempos[1:]:
			if t >= tick:
				break
			real_time += (t - last_t) * last_r
			last_t, last_r = t, ratio
		real_time += (tick - last_t) * last_r
		return real_time

	def process(self, file):
		raw_midi = midi.read_midifile(file)
		self.res = raw_midi.resolution
		raw_midi.make_ticks_abs()

		tempos = dict()
		for track in raw_midi:
			for e in track:
				if isinstance(e, midi.SetTempoEvent):
					spt = 60 / (e.get_bpm() * self.res)
					t = e.tick
					if t in tempos:
						assert tempos[t] == spt, \
						'Found different tempos at the same time'\
						'{}: {} and {}'.format(t, tempos[t], spt)
					else:
						tempos[t] = spt

		assert 0 in tempos, "No speed at tick 0!"
		self.tempos = sorted(tempos.items())

		channel_dicts = defaultdict(lambda:defaultdict(lambda:defaultdict(set)))
		max_t = -1
		for track in raw_midi:
			for e in track:
				if not (isinstance(e, midi.NoteOnEvent) or isinstance(e, midi.NoteOffEvent)):
					continue

				t = self.get_time(e.tick)
				max_t = max(max_t, t)
				pitch = e.get_pitch()
				is_on = isinstance(e, midi.NoteOnEvent) and e.get_velocity() > 0
				ch = e.channel

				channel_dicts[ch][pitch][t]=is_on

		assert max_t > 0, "No pitch detected!"
		self.max_t = max_t + 1
		self.ch_dicts = [
			{p: sorted(defd.items()) for p, defd in channel_dicts[ch].items()}
			for ch in sorted(channel_dicts)]
		for cd in self.ch_dicts:
			remove_notes = []
			for p in cd:
				ls = []
				last_on = False
				for t, is_on in cd[p]:
					if is_on == False and last_on == False:
						continue
					ls.append((t, is_on))
					last_on = is_on
				if not ls:
					remove_notes.append(p)
				else:
					cd[p] = ls
			for p in remove_notes:
				del cd[p]

		self.ch_dicts = [c for c in self.ch_dicts if c]

		#print(len(self.ch_dicts))
		assert self.ch_dicts, "Error! No note detected."
		assert all(p[-1][-1] == False for d in self.ch_dicts for p in d.values()),\
		"Error! Pitch not ended."

		self.merged_cd = MIDINotes.merge(self.ch_dicts)
		#print(self.mc_events())

		self.lyrics = []

		x = file.rfind('.')
		text_name = file[:x] + '.txt'
		self.font = None
		self.font_size = None
		if os.path.isfile(text_name):
			with open(text_name, 'r', encoding = 'utf-8') as f:
				text_list = []
				for line in f.readlines():
					if line[-1] == '\n':
						line = line[:-1]
					if line == '' or line[0] == '#':
						continue
					if line.startswith('font: '):
						self.font = line[6:]
						continue
					if line.startswith('font_size: '):
						try:
							self.font_size = int(line[11:])
						except Exception as e:
							print("[MIDINotes] Error in font_size: can't convert \"{}\" to int.".format(line[11:]))
						continue
					r = line.find('\t')
					if r == -1:
						print("[MIDINotes] Error in lyric: can't find tab in \"{}\"".format(line))
						continue
					try:
						nbeat = float(line[:r])
					except Exception as e:
						print("[MIDINotes] Error in lyric: can't convert \"{}\" to float.".format(line[:r]))
						continue
					text_list.append((self.get_time(nbeat * self.res), line[r+1:]))
				self.lyrics = [(t, txt, None, EventKind.LYRIC, 0) for t, txt in text_list]

	def lyric_events(self):
		return self.lyrics

	def mc_events(self):
		note_list = []
		notes = self.merged_cd.keys()

		max_note = max(notes)
		min_note = min(notes)
		NOTE_NUM = MCAPI.NOTE_NUM
		if self.same_note:
			zero_note = 30 # F#1 = 30 in midi
			if min_note < zero_note or max_note >= zero_note + NOTE_NUM:
				print('Warning: The variety of the song is too large, can only play a part!')
		else:
			avan_list = []
			len_dict = defaultdict(int)
			len_dict.update((x, len(self.merged_cd[x])) for x in notes)
			if max_note - min_note >= NOTE_NUM:
				for n in range(min_note, max_note - NOTE_NUM + 2):
					avan = sum(len_dict[i] for i in range(n, n+NOTE_NUM))
					avan_list.append((avan, n))
				avan_list.sort()
				zero_note = avan_list[-1][-1]
				print('Warning: The variety of the song is too large, can only play a part!')
			else:
				zero_note = (min_note + max_note - NOTE_NUM + 1) // 2

		for p in notes:
			if p < zero_note or p >= zero_note + NOTE_NUM:
				continue
			ts = sorted(self.merged_cd[p])
			p -= zero_note
			last_t = ts[0][0]
			assert ts[0][1], "First note is off!"
			note_list.append((last_t, p, True, EventKind.MC, 0))
			last_off = None
			for t in ts[1:]:
				if not t[1]:
					if last_off is None:
						last_off = t[0]
					continue
				t = t[0]
				# As short as possible
				t_end = last_t + min(0.25, (t - last_t) / 2)
				if last_off is not None:
					t_end = min(t_end, last_off)
					last_off = None
				note_list.append((t_end, p, False, EventKind.MC, 0))
				note_list.append((t, p, True, EventKind.MC, 0))
				last_t = t
			assert not ts[-1][1], "Last note is on!"
			note_list.append((ts[-1][0], p, False, EventKind.MC, 0))

		return note_list

	def buzz_events(self):
		# ch_dicts : list of "{note:[(t, is_on)...]}"

		notes = [(t, not is_on, -note, ch) \
					for ch, ch_dict in enumerate(self.ch_dicts) \
					for note, lst in ch_dict.items() \
					for t, is_on in lst
				]
		notes.sort()

		buzz_list = []
		note_to_bch = dict()
		last_time = dict()
		ava_bch = set()
		num_bch = 0

		for t, is_off, mnote, ch in notes:
			note = -mnote
			cur_bch = None
			if is_off:
				cur_bch = note_to_bch.pop((note, ch), None)
				if cur_bch is None:
					continue
				del last_time[(note, ch)]
				ava_bch.add(cur_bch)
			elif (note, ch) in note_to_bch:
				cur_bch = note_to_bch[(note, ch)]
				min_stime = (t + last_time[(note, ch)]) * 0.5
				last_t = max(min_stime, t - 0.1)
				buzz_list.append((last_t, note, False, EventKind.BUZZER, cur_bch))
				last_time[(note, ch)] = t
				if ava_bch:
					next_bch = min(ava_bch)
					ava_bch.remove(next_bch)
					ava_bch.add(cur_bch)
					cur_bch = next_bch
					note_to_bch[(note, ch)] = cur_bch
			else:
				if ava_bch:
					cur_bch = min(ava_bch)
					ava_bch.remove(cur_bch)
				else:
					cur_bch = num_bch
					num_bch += 1
				note_to_bch[(note, ch)] = cur_bch
				last_time[(note, ch)] = t
			buzz_list.append((t, note, not is_off, EventKind.BUZZER, cur_bch))

		#print("{} buzzers needed...".format(num_bch))

		return buzz_list

	@property
	def valid(self):
		return self._valid

	@property
	def length(self):
		return self.max_t

	@property
	def lyric_font(self):
		if self.font_size is None:
			return self.font
		return (self.font, self.font_size)

	def full_events(self, buzz_pfunc):
		buzz_evt, nch = buzz_pfunc(self.buzz_events())
		note_list = self.mc_events() + self.lyric_events() + buzz_evt
		note_list.sort(key = lambda x:(x[0], x[1] if isinstance(x[1],int) else -1, -1 if x[2] is None else int(x[2]), x[3].value, x[4]))
		return note_list, nch

	@staticmethod
	def play(note_list, mc = None, buz = None, oled_q = None):
		t0 = time.time()
		last_t = 0

		for t, note, on, kind, channel in note_list:
			#print(note, t, on)
			if t > last_t:
				time.sleep(max(t0 + t - time.time(), 0))
				last_t = t

			if kind == EventKind.MC:
				mc.play_note(note, on)
			elif kind == EventKind.BUZZER:
				buz.play_note(note, on, channel)
			elif kind == EventKind.LYRIC:
				mc.print(note)
				oled_q.put(note)

		oled_q.put('')
		buz.reset()

class MultiBuzzer:
	def __init__(self, pins):
		'''
		The following implementation is deprecated.
		It will have lower frequency pitch (may be caused by software delays).

		Notice that RPi.GPIO cannot control hardware PWMs,
		and thus GPIO.PWM runs on software PWM.

		The reason not using hardware PWM is that there are too few of them:
		We ONLY have TWO PWMs on a raspi 3B+ !!!

		Let's just write our own PWM instead...

		def gpio_thread(pin, q):
			p = GPIO.PWM(pin, 440)
			cur_freq = q.get()
			while cur_freq is not None:
				if cur_freq != -1:
					p.ChangeFrequency(cur_freq)
					p.start(50)
				cur_freq = q.get()
				p.stop()
			del p
		'''

		def gpio(pin, q):
			# GPIO.output(pin, GPIO.LOW)
			cur_freq = -1
			cur_stat = GPIO.LOW
			t = 0
			while True:
				while cur_freq == -1:
					cur_freq = q.get()

				if cur_freq is None:
					break

				hcyc = 0.5 / cur_freq
				t = time.time()
				while q.empty():
					t += hcyc
					cur_stat = GPIO.HIGH if cur_stat == GPIO.LOW else GPIO.LOW
					time.sleep(max(t - time.time(), 0))
					GPIO.output(pin, cur_stat)
				cur_freq = q.get()

		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)
		self.pins = pins
		for p in pins:
			GPIO.setup(p, GPIO.OUT, initial=GPIO.LOW)
		self.queues = [Queue() for _ in pins]
		self.processes = [Proc(target = gpio, args=(pin, q)) for pin, q in zip(pins, self.queues)]
		for p in self.processes:
			p.start()

	def play_note(self, note, is_on, ch):
		self.queues[ch].put(NOTES[note] if is_on else -1)

	def reset(self):
		for q in self.queues:
			q.put(-1)

		for q in self.queues:
			while not q.empty():
				pass

	def stop(self):
		for q in self.queues:
			q.put(None)
		for p in self.processes:
			p.join()

	def proc_buz(self, buzz_list):
		ch_num = max(b[-1] for b in buzz_list) + 1
		pnum = len(self.pins)
		if ch_num > pnum:
			print("[MultiBuzzer] Warning: Needs {} channels but only have {}".format(ch_num, pnum))
		return [b for b in buzz_list if b[-1] < pnum], ch_num

'''
class MultiBuzzer2:
	def __init__(self, pins):
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)
		self.pins = pins
		for p in pins:
			GPIO.setup(p, GPIO.OUT, initial=GPIO.LOW)

	def play_note(self, note, is_on, ch):
		GPIO.output(ch, is_on)

	def reset(self):
		pass

	def stop(self):
		pass

	def proc_buz(self, buzz_list):
		def try_add(cur_list, last_t, on, bch, delta):
			bch = self.pins[bch]
			on = GPIO.HIGH if on else GPIO.LOW
			if not cur_list:
				cur_list.append((last_t, -1, on, EventKind.BUZZER, bch))
				return

			st = 0
			ed = len(cur_list)
			while st < ed:
				md = (st + ed) // 2
				nmd = cur_list[md][0]
				if nmd < last_t - delta:
					st = md + 1
				elif nmd > last_t + delta:
					ed = md
				else:
					last_t = nmd
					st = md + 1
					break
			cur_list.insert(st, (last_t, -1, on, EventKind.BUZZER, bch))

		if not buzz_list:
			return buzz_list
		buzz_list.sort()
		num_ch = max(i[-1] for i in buzz_list) + 1
		_num_ch = num_ch
		pnum = len(self.pins)
		if num_ch > pnum:
			print("[MultiBuzzer2] Warning: Needs {} channels but only have {}".format(num_ch, pnum))
			num_ch = pnum
		new_blist = []
		for ch in range(num_ch):
			print("Processing ch {}/{}".format(ch, num_ch))
			last_t = -1
			last_note = None
			cur_stat = False
			for t, note, on, _, bch in buzz_list:
				if bch != ch:
					continue
				if last_note is not None:
					hcyc = 0.5 / last_note
					while last_t < t:
						try_add(new_blist, last_t, cur_stat, bch, hcyc / 300)
						last_t += hcyc
						cur_stat = not cur_stat

				if not on:
					assert NOTES[note] == last_note
					last_note = None
				else:
					last_note = NOTES[note]
					last_t = t
			assert last_note is None
		return new_blist, _num_ch
'''
