# -*- coding: utf-8 -*-

from config import OLED_W, OLED_H, FONT_DIR, OLED_FONT, OLED_FSIZE

import busio
import board
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont

class OLED:
	def __init__(self, w = OLED_W, h = OLED_H, font = None):
		i2c = busio.I2C(board.SCL, board.SDA)
		self.oled = adafruit_ssd1306.SSD1306_I2C(w, h, i2c)
		self.img = Image.new('1', (w, h))
		self.draw = ImageDraw.Draw(self.img)
		self.w, self.h = w, h
		_ = self.set_font(font)
		_ = self.clear()

	def clear(self):
		self.oled.fill(0)
		try:
			self.oled.show()
		except Exception as e:
			print("[OLED] Exception occurred when clearing oled:\n\t{} of type {}".format(e, type(e)))
			return False
		return True

	def set_font(self, font):
		size = OLED_FSIZE
		if isinstance(font, tuple) or isinstance(font, list):
			assert len(font) == 2
			font, size = font
		if font is None:
			font = OLED_FONT

		if isinstance(font, str):
			try:
				font = ImageFont.truetype(font, size = size)
			except OSError:
				try:
					font = ImageFont.truetype(FONT_DIR + font, size = size)
				except OSError:
					print("[OLED] Warning: font {} cannot be found.".format(font))
					print("Will not use custom font.")
					font = None

		self.font = font
		return self.font is not None

	def print(self, text):
		self.draw.rectangle((0, 0, self.w, self.h), fill=0, outline=0)
		line_s = ''
		x = 0
		for c in text:
			if not (line_s or c.strip()):
				continue
			line_s += c
			tl, th = self.draw.textsize(line_s, font = self.font)
			if tl > self.w:
				self.draw.text((0, x), line_s[:-1], fill = 1, font = self.font)
				x += th
				if x >= self.h:
					print("[OLED] Warning: Text size exceeded the display.")
					break
				line_s = line_s[-1].strip()
		else:
			if line_s:
				self.draw.text((0, x), line_s, fill = 1, font = self.font)
		self.oled.image(self.img)
		try:
			self.oled.show()
		except Exception as e:
			print("[OLED] Exception occurred when printing oled:\n\t{} of type {}".format(e, type(e)))
			return False
		return True


