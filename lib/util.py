# -*- coding: utf-8 -*-

from config import NULL

import threading
import time

lcl = threading.local()
lcl.last_time = None

def start_timer():
	global lcl
	lcl.last_time = time.time()

def timer_wait(sec):
	global lcl
	assert lcl.last_time is not None
	sec += lcl.last_time
	sec -= time.time()
	lcl.last_time = None
	if sec > 0:
		time.sleep(sec)