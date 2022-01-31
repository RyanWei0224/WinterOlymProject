# -*- coding: utf-8 -*-

from init import NULL
from config import SERVER_IP, MC_IP, PI_IP, ATHLETE_NAME

import time
import random
#from PIL import Image, ImageDraw, ImageFont
from threading import Lock, Condition

from mcpi.minecraft import Minecraft
#import RPi.GPIO as GPIO
#import board
#import busio
#import adafruit_ssd1306

from lib.netch import NetCh
from lib.LCD import I2CLCD
from lib.util import start_timer, timer_wait

jl_lock = None
jl_cond = None

stat = None

def send_rf(data):
	global jl_lock, jl_cond, stat
	if data != 'cancel' and data != 'ok':
		return None
	jl_lock.acquire()
	jl_cond.notify()
	stat = (data == 'ok')
	jl_lock.release()
	return True

def openTheDoor(mc):
	mc.setBlock(-152,181-64,787,76,1)
	mc.setBlock(-145,181-64,787,76,2)

def closeTheDoor(mc):
	mc.setBlock(-152,181-64,787,0)
	mc.setBlock(-145,181-64,787,0)

def isNeedShowPassword(pos):
	a=((pos.x>=-153) and (pos.x<=-143))
	b=((pos.y>=185-64) and (pos.y<=190-64))
	c=((pos.z>=777) and (pos.z<=788))
	return (a and b and c)

'''
def printPos(pos):
	print("("+str(pos.x)+","+str(pos.y)+","+str(pos.z)+")")
'''

def checking(mc, lcd, lcd_lock, channel): # oled
	global jl_lock, jl_cond, stat
	need_clear = False
	while True:
		time.sleep(1)
		if need_clear:
			lcd_lock.acquire()
			lcd.print_line('', 1)
			lcd_lock.release()
			need_clear = False
		pos = mc.player.getTilePos()
		if not isNeedShowPassword(pos):
			continue

		need_clear = True

		password=random.randint(100000,999999)
		lcd_lock.acquire()
		lcd.print_line('PASSWORD:', 1)
		lcd.print_line(str(password), 2, 'R')
		'''
		draw.rectangle((0, 0, 128, 64), fill=0, outline=0)
		draw.text((0, 0), str(password), fill=1, font=font)
		oled.image(img)
		oled.show()
		'''
		lcd_lock.release()
		channel.send({'pwd' : password})

		jl_lock.acquire()
		while stat is None:
			jl_cond.wait()
		cur_stat = stat
		stat = None
		jl_lock.release()
		lcd_lock.acquire()
		lcd.print_line('', 1)
		lcd.print_line('', 2)
		'''
		oled.fill(0)
		oled.show()
		'''
		lcd_lock.release()

		if not cur_stat:
			lcd_lock.acquire()
			lcd.print_line('CANCELLED', 1)
			lcd_lock.release()
			continue

		openTheDoor(mc)
		start_timer()
		lcd_lock.acquire()
		lcd.print_line('DOOR OPENED', 1)
		lcd_lock.release()
		_ = channel.send('open')
		mc.postToChat("已开启大门!")
		timer_wait(10)
		closeTheDoor(mc)
		lcd_lock.acquire()
		lcd.print_line('DOOR CLOSED', 1)
		lcd_lock.release()
		_ = channel.send('close')

def init(mc):
	global jl_lock, jl_cond
	jl_lock = Lock()
	jl_cond = Condition(lock = jl_lock)
	closeTheDoor(mc)
	'''
	i2c = busio.I2C(board.SCL, board.SDA)
	oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)
	oled.fill(0)
	oled.show()
	img = Image.new('1', (128, 64))
	draw = ImageDraw.Draw(img)
	font = ImageFont.truetype(FONT, size=FONT_SIZE)
	'''
	jianlu_ch = NetCh(PI_IP, SERVER_IP, 'jianlu')
	jianlu_ch.set_send_retf(send_rf)
	return jianlu_ch

def main(mc, lcd, lock, channel):
	try:
		checking(mc, lcd, lock, channel) # oled
	except KeyboardInterrupt:
		pass
	'''
	oled.fill(0)
	oled.show()
	'''

if __name__ == '__main__':
	mc = Minecraft.create(address = MC_IP, name = ATHLETE_NAME)
	lcd = I2CLCD()
	lcd_lock = Lock()
	jianlu_ch = init(mc)
	jianlu_ch.start()
	main(mc, lcd, lcd_lock, jianlu_ch)
	jianlu_ch.end()
	lcd.clear()
