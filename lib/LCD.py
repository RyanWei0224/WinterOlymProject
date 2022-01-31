# -*- coding: utf-8 -*-

from config import NULL

import smbus
import time

# Note for developers
#
# I2C byte:   [H ------------------------ L]
#             [    data    ]  [  ctrl_bits ]
# PCA8574:    P7  P6  P5  P4  P3  P2  P1  P0
# LCD1602:    D7  D6  D5  D4  BT  E   R/W RS

class I2CLCD:
	# Define some device constants
	SETUP_TIME = 40e-9
	PULSE_WIDTH = 230e-9
	HOLD_TIME = 500e-9 - PULSE_WIDTH

	INST_TIME = 40e-6
	CLEAR_TIME = 1.64e-3

	# For I2C:
	BL_CMD = 0x08  # Backlight Command.

	READ_CMD = 0x02 # Backlight Command.
	WRITE_CMD = 0x00 # Backlight Command.

	LCD_DAT = 0x01  # Mode - Sending data
	LCD_CMD = 0x00  # Mode - Sending command

	# For LCD:
	SMOD_CMD = 0b0100
	CMOV_BIT = 0b0010
	SH_BIT   = 0b0001

	DISP_CMD = 0b1000
	DISP_BIT = 0b0100
	CURV_BIT = 0b0010
	CURB_BIT = 0b0001

	SHIFT_CMD = 0b10000
	CURLR_BIT = 0b00000
	DISLR_BIT = 0b01000
	SFTL_BIT  = 0b00000
	SFTR_BIT  = 0b00100

	CGRAM_CMD = 0x40

	# LINE_1 = 0x80   # LCD RAM address for the 1st line
	# LINE_2 = 0xC0   # LCD RAM address for the 2nd line
	# LINE_3 = 0x94   # LCD RAM address for the 3rd line
	# LINE_4 = 0xD4   # LCD RAM address for the 4th line
	LCD_LINES = (0x80, 0xC0, 0x94, 0xD4)

	# Character code for custom characters in CGRAM
	CGRAM_CHR = ('\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07')

	# Character set
	CSET =  { **{c:i for i,c in enumerate(CGRAM_CHR)}
			, **{chr(i):i for i in range(0x20, 0x7e)}
			, **{bytes((i,)).decode('cp932'):i for i in range(0xa0, 0xe0)}
			, '→':0x7e, '←':0x7f, '■':0xff, '█':0xff
			, **{c if c != '_' else chr(i+0xe0):i+0xe0 for i,c in enumerate('αäβεμσρ_√¹_ⁿ￠£_ö') }
			, **{c if c != '_' else chr(i+0xf0):i+0xf0 for i,c in enumerate('__θ∞ΩüΣπ__千万円÷') }
			}

	DEFAULT_CHAR = CSET['ﾛ']

	def __init__(self, i2c_bus=1, i2c_addr=0x27, lcd_width=20, backlight = True):
		"""
		initialize the connection with the LCD
		i2c_bus:    the smbus where the LCD connected to,
					for Raspberry Pi, it should be 1 or 0 (depending on the model)
		i2c_addr:   I2C address of the adapter, usually 0x27, 0x20 or 0x3f
		lcd_width:  the width of the LCD, e.g. 16 for LCD1602, 20 for LCD2002/2004
		backlight:  whether should we turn backlight on.
		"""

		self._bus = smbus.SMBus(i2c_bus)
		self._i2c_addr = i2c_addr
		self._lcd_width = lcd_width

		self._backlight = I2CLCD.BL_CMD if backlight else 0x00
		self._disp_bits = I2CLCD.DISP_CMD | I2CLCD.DISP_BIT

		self.init()

	def _i2c_write(self, data):
		"""write one byte to I2C bus"""
		self._bus.write_byte(self._i2c_addr, data)

	def _raw_write(self, data, ctrl = LCD_CMD | WRITE_CMD):
		"""proform a high level pulse to EN"""
		data = (data << 4) | ctrl
		self._i2c_write(data)
		time.sleep(I2CLCD.SETUP_TIME)
		self._i2c_write(data | 0b00000100)
		time.sleep(I2CLCD.PULSE_WIDTH)
		self._i2c_write(data)
		time.sleep(I2CLCD.HOLD_TIME)

	def _write_byte(self, data, mode = LCD_CMD, rw = WRITE_CMD):
		"""write one byte to LCD"""
		ctrl = self._backlight | rw | mode
		data_H = data >> 4
		data_L = data & 0x0F

		self._raw_write(data_H, ctrl)
		self._raw_write(data_L, ctrl)
		time.sleep(I2CLCD.INST_TIME)

	def init(self):
		"""
		Initialize the LCD
		"""

		# setting LCD data interface to 4 bit
		self._raw_write(0x03)
		time.sleep(0.0041)
		self._raw_write(0x03)
		time.sleep(0.0001)
		self._raw_write(0x03)
		time.sleep(0.0001)
		self._raw_write(0x02)
		time.sleep(0.0001)

		self._write_byte(0b_0010_1000)		# 001F_LSXX, Function set: interface(F) 4bit, 2 lines(L), 5x8 font(S)
		self._write_byte(0b_0000_0100)		# 0000_0 1 I/D SH, I/D: Move left or right? SH: Shift display when write?
		self._write_byte(self._disp_bits)	# 0000_1DCB, Display ON/OFF: display on, cursor off, cursor blink off
		self.clear()						# Clear display

	def clear(self):
		"""
		Clear the display and reset the cursor position
		"""
		self._write_byte(0b_0000_0001)
		time.sleep(I2CLCD.CLEAR_TIME)

	def return_home(self):
		"""
		Reset cursor and display to the original position.
		"""
		self._write_byte(0b_0000_0010)
		time.sleep(I2CLCD.CLEAR_TIME)

	def set_backlight(self, on):
		"""
		Set whether the LCD backlight is on or off
		"""
		new_backlight = I2CLCD.BL_CMD if on else 0x00
		if self._backlight != new_backlight:
			self._backlight = new_backlight
			self._i2c_write(new_backlight)

	def set_shift_mode(self, inc_dec, shift_disp):
		"""
		Sets shift mode
		inc_dec:      True for inc (going right), False for dec (going left)
		shift_disp:   False for moving the cursor, True for moving the entire display backwards.
		"""
		cmd = I2CLCD.SMOD_CMD
		if inc_dec:
			cmd |= I2CLCD.CMOV_BIT
		if shift_disp:
			cmd |= I2CLCD.SH_BIT
		self._write_byte(cmd)

	def set_display(self, on):
		if on and self._disp_bits & I2CLCD.DISP_BIT == 0:
			self._disp_bits |= I2CLCD.DISP_BIT
		elif not (on or self._disp_bits & I2CLCD.DISP_BIT == 0):
			self._disp_bits &= (0xFF & ~I2CLCD.DISP_BIT)
		else:
			return
		self._write_byte(self._disp_bits)

	def set_cursor(self, cursor_visible, cursor_blink):
		"""
		Set whether the cursor is visible and whether it will blink
		"""
		if cursor_visible:
			self._disp_bits |= I2CLCD.CURV_BIT
		else:
			self._disp_bits &= (0xFF & ~I2CLCD.CURV_BIT)

		if cursor_blink:
			self._disp_bits |= I2CLCD.CURB_BIT
		else:
			self._disp_bits &= (0xFF & ~I2CLCD.CURB_BIT)
		
		self._write_byte(self._disp_bits)

	def move_cursor(self, line, column = 0):
		"""
		Move the cursor to a new posotion
		line:   line number starts from 0
		column: column number starts from 0
		"""
		if column >= self._lcd_width or column < -self._lcd_width:
			raise ValueError('Column exceeds lcd width!')
		if column < 0:
			column = self._lcd_width + column
		cmd = I2CLCD.LCD_LINES[line] + column
		self._write_byte(cmd)

	def shift(self, direction='R', move_display=False):
		"""
		Move the cursor and display left or right
		direction:      could be 'R' (default) or 'L'
		move_display:   move the entire display and cursor, or only move the cursor
		"""
		cmd = I2CLCD.SHIFT_CMD 
		cmd |= (I2CLCD.SFTR_BIT if direction == 'R' else I2CLCD.SFTL_BIT)
		cmd |= (I2CLCD.DISLR_BIT if move_display else I2CLCD.CURLR_BIT)
		self._write_byte(cmd)

	def write_CGRAM(self, chr_data, CGRAM_solt=0):
		"""
		Write a custom character to CGRAM
		chr_data:     a tuple that stores the character model data
		CGRAM_solt:   int from 0 to 7 to determine where the font data is written
		NOTICE: re-setting the cursor position after calling this method, e.g.
		lcd.write_CGRAM((0x10, 0x06, 0x09, 0x08, 0x08, 0x09, 0x06, 0x00), 2)
		lcd.move_cursor(1, 0)
		lcd.print(b'New char: ' + i2clcd.CGRAM_CHR[2])
		"""
		cmd = I2CLCD.CGRAM_CMD | (CGRAM_solt << 3)
		self._write_byte(cmd)
		for dat in chr_data:
			self._write_byte(dat, I2CLCD.LCD_DAT)

	def print(self, text):
		"""
		Print a string at the current cursor position
		text:   bytes or str object, str object will be encoded with ASCII
		"""
		if isinstance(text, str):
			text = bytes(I2CLCD.CSET.get(b, I2CLCD.DEFAULT_CHAR) for b in text)

		for b in text:
			self._write_byte(b, I2CLCD.LCD_DAT)

	def print_line(self, text, line, align='L'):
		"""
		Fill a whole line of the LCD with a string
		text:   bytes or str object, str object will be encoded with ASCII
		line:   line number starts from 0
		align:  could be 'L' (default), 'R' or 'C'
		"""
		text = text[:self._lcd_width]

		if isinstance(text, str):
			text = bytes(I2CLCD.CSET.get(b, I2CLCD.DEFAULT_CHAR) for b in text)

		text_length = len(text)
		if text_length < self._lcd_width:
			blank_space = self._lcd_width - text_length
			if align == 'L':
				text = text + b' ' * blank_space
			elif align == 'R':
				text = b' ' * blank_space + text
			else:
				text = b' ' * (blank_space // 2) + text + b' ' * (blank_space - blank_space // 2)

		self.move_cursor(line, 0)
		self.print(text)

assert all(i <= 0xff and i >= 0x00 for i in I2CLCD.CSET.values()), \
	"Error: char value out of bound in module LCD!"