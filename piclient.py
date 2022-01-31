# -*- coding: utf-8 -*-

from config import MC_IP, ATHLETE_NAME, TCS_PINS

from threading import Thread, Lock

from mcpi.minecraft import Minecraft

from lib.netch import NetCh
from lib.LCD import I2CLCD
from lib.color import TCS3200

from module.jianlu import init as jianlu_init, main as jianlu_main
from module.light import  init as light_init, main as light_main
from module.digclock import init as dc_init, main as dc_main
from module.hesuan import init as hesuan_init, main as hesuan_main
from module.car import init as car_init, main as car_main

if __name__ == '__main__':
	mcl = Minecraft.create(address = MC_IP)
	mcj = Minecraft.create(address = MC_IP, name = ATHLETE_NAME)
	mcd = Minecraft.create(address = MC_IP)
	mch = Minecraft.create(address = MC_IP, name = ATHLETE_NAME)
	mcc = Minecraft.create(address = MC_IP)
	lcd = I2CLCD()
	lcd_lock = Lock()
	tcs = TCS3200(**TCS_PINS)

	light_ch = light_init(mcl)
	jianlu_ch = jianlu_init(mcj)
	dc_init(mcd)
	hesuan_ch = hesuan_init(mch, tcs, lcd, lcd_lock)
	car_ch, car_idx = car_init(mcc)

	NetCh.start()
	funcs = [(light_main, light_ch), 
			 (jianlu_main, mcj, lcd, lcd_lock, jianlu_ch),
			 (dc_main, mcd, lcd, lcd_lock),
			 (hesuan_main, mch, tcs, lcd, lcd_lock, hesuan_ch),
			 (car_main, mcc, car_ch, car_idx),
			]
	threads = [Thread(target = f[0], args = f[1:]) for f in funcs]
	for t in threads:
		t.start()
	
	for t in threads:
		t.join()

	lcd_lock.acquire()
	lcd.clear()
	lcd_lock.release()
	NetCh.end()
	GPIO.cleanup()