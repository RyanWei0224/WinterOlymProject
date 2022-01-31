# -*- coding: utf-8 -*-

from init import NULL
from config import MC_IP

import time
from threading import Lock

from mcpi.minecraft import Minecraft
from mcpi import block

from lib.LCD import I2CLCD
from lib.util import start_timer, timer_wait

DIGIT_SHIFT = (-4, 2, 292)
DIGIT_POS = (128, 106, 75, 53, 22, 0)
COMMA_POS = (97, 44)

DIGIT_BLOCK = block.WOOL_ORANGE
AIR_BLOCK = block.AIR
BGR_BLOCK = block.GLASS

DIGIT_CODE = ( # See LINE_FUNC for the meaning of each 0/1.
(1, 1, 1, 0, 1, 1, 1), # 0
(1, 1, 0, 0, 0, 0, 0), # 1
(0, 1, 1, 1, 1, 1, 0), # 2
(1, 1, 1, 1, 1, 0, 0), # 3
(1, 1, 0, 1, 0, 0, 1), # 4
(1, 0, 1, 1, 1, 0, 1), # 5
(1, 0, 1, 1, 1, 1, 1), # 6
(1, 1, 0, 0, 1, 0, 0), # 7
(1, 1, 1, 1, 1, 1, 1), # 8
(1, 1, 1, 1, 1, 0, 1), # 9
(0, 0, 0, 0, 0, 0, 0), # space
)

cur_digits = None


def set_comma(mc, on, lcd, lcd_lock):
	ch = ':' if on else ' '
	lcd_lock.acquire()
	lcd.move_cursor(0, -6)
	lcd.print(ch)
	lcd.move_cursor(0, -3)
	lcd.print(ch)
	lcd_lock.release()
	dx0, dy, dz = DIGIT_SHIFT
	for c in COMMA_POS:
		dx = dx0 + c
		if on:
			bl = DIGIT_BLOCK
			mc.setBlocks(dx,	dy+22,	dz,	dx+4,	dy+22,	dz,	bl)
			mc.setBlocks(dx+1,	dy+21,	dz,	dx+3,	dy+23,	dz,	bl)
			mc.setBlocks(dx+2,	dy+20,	dz,	dx+2,	dy+24,	dz,	bl)

			mc.setBlocks(dx,	dy+8,	dz,	dx+4,	dy+8,	dz,	bl)
			mc.setBlocks(dx+1,	dy+7,	dz,	dx+3,	dy+9,	dz,	bl)
			mc.setBlocks(dx+2,	dy+6,	dz,	dx+2,	dy+10,	dz,	bl)
		else:
			mc.setBlocks(dx,	dy+6,	dz,	dx+4,	dy+24,	dz,	AIR_BLOCK)

def set_rd(mc, dnum, bl):
	dx, dy, dz = DIGIT_SHIFT
	dx += DIGIT_POS[dnum]
	mc.setBlocks(dx,	dy+1,	dz,	dx,		dy+12,	dz,	bl)
	mc.setBlocks(dx+1,	dy+2,	dz,	dx+1,	dy+13,	dz,	bl)
	mc.setBlocks(dx+2,	dy+3,	dz,	dx+2,	dy+14,	dz,	bl)
	mc.setBlocks(dx+3,	dy+4,	dz,	dx+3,	dy+13,	dz,	bl)
	mc.setBlocks(dx+4,	dy+5,	dz,	dx+4,	dy+12,	dz,	bl)

def set_ru(mc, dnum, bl):
	dx, dy, dz = DIGIT_SHIFT
	dx += DIGIT_POS[dnum]
	mc.setBlocks(dx,	dy+18,	dz,	dx,		dy+29,	dz,	bl)
	mc.setBlocks(dx+1,	dy+17,	dz,	dx+1,	dy+28,	dz,	bl)
	mc.setBlocks(dx+2,	dy+16,	dz,	dx+2,	dy+27,	dz,	bl)
	mc.setBlocks(dx+3,	dy+17,	dz,	dx+3,	dy+26,	dz,	bl)
	mc.setBlocks(dx+4,	dy+18,	dz,	dx+4,	dy+25,	dz,	bl)

def set_d(mc, dnum, bl):
	dx, dy, dz = DIGIT_SHIFT
	dx += DIGIT_POS[dnum]
	mc.setBlocks(dx+1,	dy,		dz,	dx+16,	dy,		dz,	bl)
	mc.setBlocks(dx+2,	dy+1,	dz,	dx+15,	dy+1,	dz,	bl)
	mc.setBlocks(dx+3,	dy+2,	dz,	dx+14,	dy+2,	dz,	bl)
	mc.setBlocks(dx+4,	dy+3,	dz,	dx+13,	dy+3,	dz,	bl)
	mc.setBlocks(dx+5,	dy+4,	dz,	dx+12,	dy+4,	dz,	bl)

def set_m(mc, dnum, bl):
	dx, dy, dz = DIGIT_SHIFT
	dx += DIGIT_POS[dnum]
	mc.setBlocks(dx+3,	dy+15,	dz,	dx+14,	dy+15,	dz,	bl)
	mc.setBlocks(dx+4,	dy+14,	dz,	dx+13,	dy+16,	dz,	bl)
	mc.setBlocks(dx+5,	dy+13,	dz,	dx+12,	dy+17,	dz,	bl)

def set_u(mc, dnum, bl):
	dx, dy, dz = DIGIT_SHIFT
	dx += DIGIT_POS[dnum]
	mc.setBlocks(dx+1,	dy+30,	dz,	dx+16,	dy+30,	dz,	bl)
	mc.setBlocks(dx+2,	dy+29,	dz,	dx+15,	dy+29,	dz,	bl)
	mc.setBlocks(dx+3,	dy+28,	dz,	dx+14,	dy+28,	dz,	bl)
	mc.setBlocks(dx+4,	dy+27,	dz,	dx+13,	dy+27,	dz,	bl)
	mc.setBlocks(dx+5,	dy+26,	dz,	dx+12,	dy+26,	dz,	bl)

def set_ld(mc, dnum, bl):
	dx, dy, dz = DIGIT_SHIFT
	dx += DIGIT_POS[dnum]
	mc.setBlocks(dx+17,	dy+1,	dz,	dx+17,	dy+12,	dz,	bl)
	mc.setBlocks(dx+16,	dy+2,	dz,	dx+16,	dy+13,	dz,	bl)
	mc.setBlocks(dx+15,	dy+3,	dz,	dx+15,	dy+14,	dz,	bl)
	mc.setBlocks(dx+14,	dy+4,	dz,	dx+14,	dy+13,	dz,	bl)
	mc.setBlocks(dx+13,	dy+5,	dz,	dx+13,	dy+12,	dz,	bl)

def set_lu(mc, dnum, bl):
	dx, dy, dz = DIGIT_SHIFT
	dx += DIGIT_POS[dnum]
	mc.setBlocks(dx+17,	dy+18,	dz,	dx+17,	dy+29,	dz,	bl)
	mc.setBlocks(dx+16,	dy+17,	dz,	dx+16,	dy+28,	dz,	bl)
	mc.setBlocks(dx+15,	dy+16,	dz,	dx+15,	dy+27,	dz,	bl)
	mc.setBlocks(dx+14,	dy+17,	dz,	dx+14,	dy+26,	dz,	bl)
	mc.setBlocks(dx+13,	dy+18,	dz,	dx+13,	dy+25,	dz,	bl)

LINE_FUNC = (set_rd, set_ru, set_d, set_m, set_u, set_ld, set_lu)

def set_digit(mc, digit, num, lcd, lcd_lock):
	global cur_digits
	lnum = cur_digits[digit]
	if lnum == num:
		return False
	lcd_lock.acquire()
	lcd.move_cursor(0, digit + digit // 2 - 8)
	lcd.print(chr(ord('0') + num))
	lcd_lock.release()
	cur_digits[digit] = num
	last_code = DIGIT_CODE[lnum]
	cur_code = DIGIT_CODE[num]
	for (lc, cc, f) in zip(last_code, cur_code, LINE_FUNC):
		if lc != cc:
			bl = DIGIT_BLOCK if cc == 1 else AIR_BLOCK
			f(mc, digit, bl)
	return True

def init(mc):
	global cur_digits
	cur_digits = [10] * 6
	dx, dy, dz = DIGIT_SHIFT
	mc.setBlocks(dx-1, dy-1, dz, dx+DIGIT_POS[0]+18, dy+31, dz, AIR_BLOCK)
	mc.setBlocks(dx-1, 0, dz+1, dx+DIGIT_POS[0]+18, dy+31, dz+1, BGR_BLOCK)

def main(mc, lcd, lcd_lock):
	try:
		has_comma = False
		d = [0] * 6
		lcd_lock.acquire()
		lcd.print_line('Time: XX:XX:XX', 0, 'R')
		lcd_lock.release()
		while True:
			start_timer()
			has_comma = not has_comma
			set_comma(mc, has_comma, lcd, lcd_lock)
			lct = time.localtime()
			d[0], d[1] = divmod(lct.tm_hour, 10)
			d[2], d[3] = divmod(lct.tm_min, 10)
			d[4], d[5] = divmod(lct.tm_sec, 10)
			
			for i, di in enumerate(d):
				_=set_digit(mc, i, di, lcd, lcd_lock)
			timer_wait(0.5)
	except KeyboardInterrupt:
		pass

if __name__ == '__main__':
	mc = Minecraft.create(address = MC_IP)
	lcd = I2CLCD()
	lcd_lock = Lock()
	init(mc)
	main(mc, lcd, lcd_lock)
	lcd.clear()
