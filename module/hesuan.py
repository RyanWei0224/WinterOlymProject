# -*- coding: utf-8 -*-

from init import NULL
from config import SERVER_IP, MC_IP, PI_IP, ATHLETE_NAME, TCS_PINS, BUTTON_PIN

import time
from threading import Lock

from mcpi.minecraft import Minecraft
from mcpi import block
import RPi.GPIO as GPIO

from lib.netch import NetCh
from lib.color import TCS3200
from lib.LCD import I2CLCD

def openTheDoor(mc):
	mc.setBlock(166, 61-64, 211, block.STONE)

def closeTheDoor(mc):
	mc.setBlock(166, 61-64, 211, block.REDSTONE_BLOCK)

def geli(mc):
	mc.player.setPos(220, 64-64, 173)
	mc.postToChat("您已被隔离!")

def isNeedToTest(pos):
	a=((pos.x>=160)&(pos.x<=174))
	b=((pos.y>=64-64)&(pos.y<=68-64))
	c=((pos.z>=210)&(pos.z<=219))
	if (a&b&c):
		return True
	else:
		return False

def init(mc, tcs, lcd, lcd_lock):
	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)
	GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down = GPIO.PUD_UP)

	hesuan_ch = NetCh(PI_IP, SERVER_IP, 'hesuan')
	closeTheDoor(mc)
	lcd_lock.acquire()
	lcd.print_line('TRY WHITE BALANCE...', 3)
	lcd_lock.release()

	GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)

	tcs.tryWB()
	lcd_lock.acquire()
	lcd.print_line('', 3)
	lcd_lock.release()
	return hesuan_ch

def main(mc, tcs, lcd, lcd_lock, channel):
	try:
		while True:
			time.sleep(1)
			pos = mc.player.getTilePos()
			if not isNeedToTest(pos):
				continue
			
			mc.postToChat("请展示您的北京健康宝:")
			lcd_lock.acquire()
			lcd.print_line('PLS SHOW YOUR CODE', 3)
			lcd_lock.release()

			GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)

			color = tcs.getRGB()
			lcd_lock.acquire()
			lcd.print_line('', 3)
			lcd_lock.release()
			green = (color[0] <= color[1])
			msg = time.strftime('%Y-%m-%d %H:%M:%S 核酸{}码'.format('绿' if green else '红'))
			channel.send(msg)

			if green:
				openTheDoor(mc)
				mc.postToChat("欢迎来到北京冬奥会!")
				time.sleep(10)
				closeTheDoor(mc)
			else:
				geli(mc)

	except KeyboardInterrupt:
		pass
	tcs.close()

if __name__ == '__main__':
	mc = Minecraft.create(address = MC_IP, name = ATHLETE_NAME)
	lcd = I2CLCD()
	lcd_lock = Lock()
	tcs = TCS3200(**TCS_PINS)
	hesuan_ch = init(mc, tcs, lcd, lcd_lock)
	# hesuan_ch.start()
	main(mc, tcs, lcd, lcd_lock, hesuan_ch)
	lcd.clear()
	# hesuan_ch.end()
	GPIO.cleanup()
