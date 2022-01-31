# -*- coding: utf-8 -*-

from init import NULL
from config import MC_IP, PI_IP, SERVER_IP, MINECART_NAME, \
					CAR_PIN, DETECT_INT, MAX_SPEED, PWM_PERITER

import time
from threading import Lock

from mcpi.minecraft import Minecraft, CmdEntity
import RPi.GPIO as GPIO

from lib.netch import NetCh
from lib.util import start_timer, timer_wait

class CarException(Exception):
    pass


def forward():
	GPIO.output(CAR_PIN[1],0)
	GPIO.output(CAR_PIN[2],1)
	GPIO.output(CAR_PIN[3],0)
	GPIO.output(CAR_PIN[4],1)
	GPIO.output(CAR_PIN[5],0)
	GPIO.output(CAR_PIN[6],1)
	GPIO.output(CAR_PIN[7],0)
	GPIO.output(CAR_PIN[8],1)


def stop():
	GPIO.output(CAR_PIN[1],0)
	GPIO.output(CAR_PIN[2],0)
	GPIO.output(CAR_PIN[3],0)
	GPIO.output(CAR_PIN[4],0)
	GPIO.output(CAR_PIN[5],0)
	GPIO.output(CAR_PIN[6],0)
	GPIO.output(CAR_PIN[7],0)
	GPIO.output(CAR_PIN[8],0)


def backward():
	GPIO.output(CAR_PIN[1],1)
	GPIO.output(CAR_PIN[2],0)
	GPIO.output(CAR_PIN[3],1)
	GPIO.output(CAR_PIN[4],0)
	GPIO.output(CAR_PIN[5],1)
	GPIO.output(CAR_PIN[6],0)
	GPIO.output(CAR_PIN[7],1)
	GPIO.output(CAR_PIN[8],0)


def left():
	GPIO.output(CAR_PIN[2],0)
	GPIO.output(CAR_PIN[1],1)
	GPIO.output(CAR_PIN[3],0)
	GPIO.output(CAR_PIN[4],1)
	GPIO.output(CAR_PIN[8],0)
	GPIO.output(CAR_PIN[7],1)
	GPIO.output(CAR_PIN[5],0)
	GPIO.output(CAR_PIN[6],1)


def right():
	GPIO.output(CAR_PIN[2],1)
	GPIO.output(CAR_PIN[1],0)
	GPIO.output(CAR_PIN[3],1)
	GPIO.output(CAR_PIN[4],0)
	GPIO.output(CAR_PIN[8],1)
	GPIO.output(CAR_PIN[7],0)
	GPIO.output(CAR_PIN[5],1)
	GPIO.output(CAR_PIN[6],0)

cur_pos = None
pos_lock = None

def car_qrf(msg):
	global cur_pos, pos_lock
	pos_lock.acquire()
	pos = cur_pos
	pos_lock.release()
	return pos

def get_car_id(mc):
	player_uuid = mc.player.getNameAndUUID()[1]
	c = CmdEntity(mc.conn)
	for idx in range(2000):
		try:
			name, uuid = c.getNameAndUUID(idx)
		except Exception:
			continue
		if name == MINECART_NAME:
			return idx
		if uuid == player_uuid:
			for j in range(idx+1, idx+100):
				try:
					name, uuid = c.getNameAndUUID(j)
				except Exception:
					continue
				if name == MINECART_NAME:
					return j
			return None
	return None

def init(mc):
	global pos_lock
	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)
	for pin in CAR_PIN[1:]:
		GPIO.setup(pin,GPIO.OUT)

	car_ch = NetCh(PI_IP, SERVER_IP, 'car')
	car_ch.set_query_retf(car_qrf)

	pos_lock = Lock()

	patrol = get_car_id(mc)
	if patrol is None:
		print("\n[car] Cannot detect patrol!\n")
	return car_ch, patrol


def main(mc, channel, idx):
	global cur_pos, pos_lock
	try:
		c = CmdEntity(mc.conn)
		def get_pos():
			nonlocal channel, c, idx, mc
			global cur_pos, pos_lock
			if idx is None:
				try:
					cidx = get_car_id(mc)
				except Exception:
					pass
				else:
					idx = cidx
			if idx is not None:
				try:
					curX = c.getPos(idx).x
				except Exception:
					idx = None
				else:
					pos_lock.acquire()
					if cur_pos is None:
						print("\n[car] Gain track of the car!\n")
					cur_pos = curX
					pos_lock.release()
					return curX
			pos_lock.acquire()
			if cur_pos is not None:
				print("\n[car] Lose track of the car!\n")
				cur_pos = None
			pos_lock.release()
			return None
			# raise CarException()

		curX = get_pos()
		while curX is None:
			time.sleep(DETECT_INT)
			curX = get_pos()
		carX = curX
		time.sleep(0.3 * DETECT_INT)
		MAXV = MAX_SPEED * DETECT_INT
		while True:
			curX = get_pos()
			if curX is None:
				time.sleep(DETECT_INT)
				continue
			dx = curX - carX
			v = dx / MAXV
			fwd = dx > 0
			v = min(abs(v), 1)
			move_t = DETECT_INT * v / PWM_PERITER
			stop_t = DETECT_INT * (1-v) / PWM_PERITER
			for i in range(PWM_PERITER):
				start_timer()
				if v > 0:
					if fwd:
						forward()
					else:
						backward()
					timer_wait(move_t)
					start_timer()
				stop()
				timer_wait(stop_t)
			carX += (v if fwd else (-v))* MAXV
	except KeyboardInterrupt:
		pass
	'''
	except CarException:
		print("\nLose track of the car! Module car will stop!\n")
		pos_lock.acquire()
		cur_pos = None
		pos_lock.release()
	'''

if __name__ == '__main__':
	mc = Minecraft.create(address = MC_IP)
	car_ch, car_idx = init(mc)
	car_ch.start()
	main(mc, car_ch, car_idx)
	car_ch.end()
	GPIO.cleanup()
