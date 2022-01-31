# -*- coding: utf-8 -*-

from init import NULL
from config import SERVER_IP, MC_IP, PI_IP

from threading import Lock, Condition
import requests
import time

from mcpi.minecraft import CmdPlayer, Minecraft
from mcpi import block

from lib.netch import NetCh
from lib.util import start_timer, timer_wait

LIGHT_BLOCK = block.GLOWSTONE_BLOCK
HARD_BLOCK = block.QUARTZ_BLOCK

REDS = [
	(46, 3, 161), (46, 3, 166), (46, 3, 171), (60, 3, 147), (84, 3, 145), (84, 3, 152), 
	(49, 4, 168), (49, 4, 169), (65, 4, 150), (66, 4, 150), (68, 4, 129), (69, 4, 180), 
	(74, 4, 185), (78, 4, 161), (78, 4, 162), (78, 4, 163), (78, 4, 164), (81, 4, 185), 
	(82, 4, 170), (84, 4, 129), (84, 4, 145), (84, 4, 152), (84, 4, 160), (84, 4, 165), 
	(86, 4, 173), (86, 4, 180), (88, 4, 134), (88, 4, 143), (52, 5, 166), (58, 5, 158), 
	(58, 5, 160), (59, 5, 166), (59, 5, 171), (61, 5, 151), (64, 5, 155), (66, 5, 158), 
	(66, 5, 159), (66, 5, 160), (66, 5, 165), (71, 5, 151), (71, 5, 170), (72, 5, 151), 
	(72, 5, 159), (72, 5, 160), (72, 5, 165), (72, 5, 166), (73, 5, 142), (74, 5, 144), 
	(76, 5, 131), (77, 5, 144), (77, 5, 156), (77, 5, 159), (77, 5, 166), (47, 6, 176), 
	(47, 6, 177), (48, 6, 176), (48, 6, 177), (62, 6, 171), (62, 6, 172), (62, 6, 173), 
	(62, 6, 174), (67, 6, 167), (67, 6, 168), (67, 6, 169), (68, 6, 145), (69, 6, 138), 
	(69, 6, 139), (69, 6, 145), (69, 6, 175), (70, 6, 145), (71, 6, 138), (71, 6, 139), 
	(77, 6, 176), (77, 6, 177), (78, 6, 176), (78, 6, 177), (57, 7, 159), (59, 7, 159), 
	(62, 10, 155), (66, 10, 170), (67, 10, 170), (62, 11, 166), (64, 11, 166), 
	(66, 11, 158), (66, 11, 161), (67, 11, 158), (67, 11, 161), (69, 11, 180), 
	(70, 11, 148), (70, 11, 149), (71, 11, 151), (72, 11, 151), (72, 11, 168), 
	(73, 11, 151), (73, 11, 168), (74, 11, 168), (74, 11, 185), (75, 11, 168), 
	(76, 11, 168), (77, 11, 168), (82, 11, 169), (86, 11, 173), (66, 14, 148), 
	(67, 14, 148), (73, 14, 174), (73, 14, 175), (73, 14, 176), (74, 14, 173), 
	(75, 14, 172), (76, 14, 172), (77, 14, 172), (78, 14, 181), (79, 14, 172), 
	(79, 14, 181), (80, 14, 172), (80, 14, 181), (81, 14, 173), (81, 14, 180), 
	(82, 14, 174), (82, 14, 175), (82, 14, 177), (82, 14, 178), (82, 14, 179), 
	(61, 15, 148), (61, 15, 157), (62, 15, 157), (63, 15, 157), (64, 15, 157), 
	(66, 15, 155), (77, 15, 161), (77, 15, 168), (55, 16, 169), (55, 16, 173), 
	(56, 16, 169), (56, 16, 173), (66, 16, 167), (66, 16, 168), (73, 16, 152), 
	(73, 16, 153), (66, 17, 163), (66, 17, 167), (67, 17, 163), (73, 17, 159), 
	(74, 17, 159), (75, 17, 159), (76, 17, 159), (69, 18, 163), (70, 18, 163), 
	(71, 18, 163)
]

'''
bls = mc.getBlocks(35,0,125,95,20,195)
bl_list = []
i=0
for y in range(0,21):
	for x in range(35,96):
		for z in range(125,196):
			if bls[i] == 89:
				bl_list.append((x,y,z))
			i+=1

print(bl_list)
'''
mc_serv = None

def changeLight(on):
	global mc_serv
	blk = LIGHT_BLOCK if on else HARD_BLOCK
	for pos in REDS:
		mc_serv.setBlock(pos, blk)

lock = None
condition = None
mode = 'auto'
status = None

def query_rf(data):
	global mode, status, lock, condition
	if data != 'auto':
		return None
	lock.acquire()
	if mode == 'auto':
		st = status
	else:
		st = mode
	lock.release()
	return st

def send_rf(data):
	global mode, status, mc_serv, lock, condition
	if data == mode:
		return True

	if data == 'open':
		lock.acquire()
		mode = 'open'
		if status != True:
			status = True
			changeLight(True)
		lock.release()
	elif data == 'close':
		lock.acquire()
		mode = 'close'
		if status != False:
			status = False
			changeLight(False)
		lock.release()
	elif data == 'auto':
		lock.acquire()
		condition.notify()
		mode = 'auto'
		autoLight(mc_serv)
		lock.release()
	else:
		return None
	return True
	

def autoLight(mc):
	global status, lock
	pls = mc.getPlayerEntityIds()
	hasP = False
	for pid in pls:
		pos = CmdPlayer(mc.conn, playerId=pid).getTilePos()
		if pos.x<95 and pos.x>35 and pos.y<30 and pos.z<195 and pos.z>125:
			hasP = True
			break
	if mode == 'auto' and status != hasP:
		changeLight(hasP)
		status = hasP

def lights(mc, light_ch):
	global status, mode, lock, condition
	while True:
		start_timer()
		lock.acquire()
		while mode != 'auto':
			condition.wait()
		autoLight(mc)
		lock.release()
		timer_wait(0.4)
		time.sleep(0.1)

def init(mc):
	global mc_serv, lock, condition
	lock = Lock()
	condition = Condition(lock = lock)
	mc_serv = mc
	light_ch = NetCh(PI_IP, SERVER_IP, 'light')
	light_ch.set_query_retf(query_rf)
	light_ch.set_send_retf(send_rf)
	autoLight(mc_serv)
	return light_ch

def main(light_ch):
	global mc_serv
	try:
		lights(mc_serv, light_ch)
	except KeyboardInterrupt:
		pass

if __name__ == '__main__':
	mc = Minecraft.create(address = MC_IP)
	light_ch = init(mc)
	light_ch.start()
	main(light_ch)
	light_ch.end()
	