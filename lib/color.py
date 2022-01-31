# -*- coding: utf-8 -*-

from config import NULL

from enum import Enum, auto
import time

import RPi.GPIO as GPIO

class TCS3200:
	class Color(Enum):
		RED = auto()
		GREEN = auto()
		BLUE = auto()

	FIL_PINS = {
		Color.RED:   (0,0),
		Color.GREEN: (1,1),
		Color.BLUE:  (0,1),
	}

	def __init__(self, out, led, s0, s1, s2, s3):
		self.out=out
		self.led=led
		self.s0=s0
		self.s1=s1
		self.s2=s2
		self.s3=s3
		self.jizhunshijian = {c: 0.1 for c in TCS3200.Color} #以255个方波为基准，将rgb的基准时间分别保存
		# self.rgbfangbo = [0, 0, 0] #r,g,b方波数量，基准时间内测的的3个方波个数就表示此刻rgb的值

		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)
		GPIO.setup((led, s0, s1, s2, s3), GPIO.OUT)
		GPIO.setup(out, GPIO.IN, pull_up_down = GPIO.PUD_UP)

		self.out1than5()
		self.close()

	def close(self):
		self.noFilter()
		self.closeLed()

	def openLed(self):
		GPIO.output(self.led,1)

	def closeLed(self):
		GPIO.output(self.led,0)

	def colorFilter(self, color):
		s2p, s3p = TCS3200.FIL_PINS[color]
		GPIO.output(self.s2,s2p)
		GPIO.output(self.s3,s3p)

	def noFilter(self):
		GPIO.output(self.s2,1)
		GPIO.output(self.s3,0)

	#内部震荡方波频率与光强成正比，OUT引脚输出方波频率与震荡器成比例关系，比例因子通过s0,s1设置
	def noPower(self):
		GPIO.output(self.s0,0)
		GPIO.output(self.s1,0)

	def out1than50(self):
		GPIO.output(self.s0,0)
		GPIO.output(self.s1,1)

	def out1than5(self):
		GPIO.output(self.s0,1)
		GPIO.output(self.s1,0)

	def out1than1(self):
		GPIO.output(self.s0,1)
		GPIO.output(self.s1,1)

	def _getjzsj(self):
		for c in TCS3200.Color:
			self.colorFilter(c) #time for c
			time.sleep(0.01)
			GPIO.wait_for_edge(self.out,GPIO.RISING)
			t1 = time.time()
			for _ in range(255):
				GPIO.wait_for_edge(self.out,GPIO.RISING)
			t2 = time.time()
			self.jizhunshijian[c]= t2 - t1

	def tryWB(self):
		'''White Balance'''
		self.openLed()
		self.out1than1()
		self._getjzsj()
		if sum(self.jizhunshijian.values()) < 0.1:
			self.out1than5()
			self._getjzsj()
			if sum(self.jizhunshijian.values()) < 0.05:
				self.out1than50()
				self._getjzsj()
		self.close()

	def getRGB(self):
		self.openLed()
		rgb = []

		for c in TCS3200.Color:
			self.colorFilter(c) #检测c
			time.sleep(0.01)
			fangbo = 0
			GPIO.wait_for_edge(self.out,GPIO.RISING)
			td = time.time() + self.jizhunshijian[c]
			while time.time() < td:
				GPIO.wait_for_edge(self.out,GPIO.RISING) #等待边缘检测，发现了fangbo就+1
				fangbo += 1
			rgb.append(fangbo)

		self.close()
		return rgb