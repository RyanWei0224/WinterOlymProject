# -*- coding: utf-8 -*-

from config import PORT, CH_PORT, PI_IP, SERVER_IP, APP_IP, CAR_ENDP, CAR_SL

from flask import Flask, request as fl_req, abort as fl_abort,\
	render_template, render_template_string, redirect
from threading import Lock
from math import floor

from lib.netch import NetCh

light_stat = '自动'
light_lock = None
light_ch = None

def get_lstat():
	global light_stat, light_ch, light_lock
	light_lock.acquire()
	stat = light_stat
	if light_stat == '自动':
		res = light_ch.query('auto')
		light_lock.release()
		data = res['data']
		if data == 'open':
			stat = '打开'
		elif data == 'close':
			stat = '关闭'
		else:
			res = '开启' if data else '关闭'
			stat += '(当前已{})'.format(res)
	else:
		light_lock.release()
	return stat

def light_get():
	return render_template('light.html', stat = get_lstat(), resp = '')

def light_post():
	global light_stat, light_ch, light_lock
	form = fl_req.form
	if not form:
		fl_abort(400)
	key, val = next(form.items())
	light_lock.acquire()
	if val == light_stat:
		pass
	elif key in ('open', 'close', 'auto'):
		_ = light_ch.send(key)
	else:
		light_lock.release()
		fl_abort(400)
	light_stat = val
	light_lock.release()
	return render_template('light.html', stat = get_lstat(), resp = '设置成功！')

'''
# jianlu logic:
server: [0, None]
1. person walks in (mc)
2. mc -> server: 1, passwd
3. server wait until user enters passwd
4. server -> mc: 2
(4'. if user cacels, server -> mc: 0, goto 1.)
5. mc opens door
6. mc -> server: 3
7. mc closes door
8. mc -> server: 0
'''

jianlu_stat = [0, None]
jianlu_ch = None
jianlu_lock = None
JL_STATMSG = {
0: '暂未检测到选手，请确认您已位于大门边，并刷新重试。',
2: '正在打开大门，请稍候...',
3: '大门已打开',
}

def jianlu_srf(msg):
	global jianlu_lock
	jianlu_lock.acquire()
	if msg == 'open':
		jianlu_stat[0] = 3
		jianlu_stat[1] = None
	elif msg == 'close':
		jianlu_stat[0] = 0
		jianlu_stat[1] = None
	elif isinstance(msg, dict) and 'pwd' in msg:
		jianlu_stat[0] = 1
		jianlu_stat[1] = str(msg['pwd'])
	else:
		jianlu_lock.release()
		return None
	jianlu_lock.release()
	return True

def jianlu_get():
	global jianlu_stat, jianlu_lock
	jianlu_lock.acquire()
	if jianlu_stat[0] == 1:
		jianlu_lock.release()
		return render_template('jianlu_post.html', pwd = '', resp = '')
	msg = JL_STATMSG.get(jianlu_stat[0], '发生错误。')
	jianlu_lock.release()
	return render_template('jianlu_get.html', stat = msg)

def jianlu_post():
	global jianlu_stat, jianlu_ch, jianlu_lock
	form = fl_req.form
	jianlu_lock.acquire()
	if jianlu_stat[0] != 1 or 'pwd' not in form:
		jianlu_lock.release()
		fl_abort(400)
	if jianlu_stat[1] is None:
		jianlu_lock.release()
		fl_abort(500)
	if 'cancel' in form:
		jianlu_stat[0] = 0
		jianlu_stat[1] = None
		jianlu_lock.release()
		_ = jianlu_ch.send('cancel')
		return render_template('jianlu_get.html', stat = '已成功取消检录。若需重新检录，请刷新。')
	if 'ok' not in form:
		jianlu_lock.release()
		fl_abort(400)
	if form['pwd'] != jianlu_stat[1]:
		jianlu_lock.release()
		return render_template('jianlu_post.html',  pwd = form['pwd'], resp = '密码错误，请重新输入！')
	
	jianlu_stat[0] = 2
	jianlu_stat[1] = None
	jianlu_lock.release()
	_ = jianlu_ch.send('ok')
	return render_template('jianlu_get.html', stat = JL_STATMSG[2])



hesuan_list = []
hesuan_ch = None
hesuan_lock = None

def hesuan_srf(msg):
	global hesuan_list, hesuan_lock
	hesuan_lock.acquire()
	hesuan_list.append(msg)
	hesuan_lock.release()
	with open("hesuan.csv", 'a', encoding = 'utf-8') as f:
		f.write(msg+'\n')
	return True

def hesuan_get():
	global hesuan_list, hesuan_lock
	s = ''
	hesuan_lock.acquire()
	for hs in hesuan_list:
		t = hs.split()
		s += '<tr><td>{}</td><td>{}</td><td>{}</td></tr>'.format(t[0], t[1], t[2])
	hesuan_lock.release()
	with open("templates/hesuan.html", 'r', encoding='utf-8') as f:
		html = f.read()
	html = html.replace('{{records}}', s)
	return html




car_ch = None
CAR_STR = '|' + ('-' * CAR_SL) + '|'
CAR_CHAR = '█'

def car_get():
	global car_ch
	cur_pos = car_ch.query('pos')['data']
	pos_str = str(CAR_STR)
	lstr = ' '
	rstr = ' '
	if cur_pos is None:
		cur_pos = float('nan')
	elif cur_pos < CAR_ENDP[0]:
		lstr = CAR_CHAR
	elif cur_pos >= CAR_ENDP[1]:
		rstr = CAR_CHAR
	else:
		rel_pos = (cur_pos - CAR_ENDP[0]) / (CAR_ENDP[1] - CAR_ENDP[0])
		cpos = floor(1 + rel_pos * CAR_SL)
		pos_str = pos_str[:cpos] + CAR_CHAR + pos_str[cpos+1:]
	pos_str = 'L' + lstr + pos_str + rstr + 'R'
	return render_template('car.html', pos = "%.1f"%cur_pos, pos_str = pos_str)


DEFAULT_TEMPLATE = {
#'song_name': 'name',
#'lyric3': 'Lyric3',
'ttime_m': '00',
'ttime_s': '00',

#'isplay': '_',

#'slow': 'disabled',
#'fast': 'disabled',
'times': '1.0',

'ctime_m': '00',
'ctime_s': '00',
'pos': '0%',
'next_fresh': '15',
}

SPEEDS = (
(0.5, '0.5'),
(0.75, '0.75'),
(1.0, '1.0'),
(1.5, '1.5'),
(2.0, '2.0'),
)

song_list = ()
cur_speed = 2
cur_song = None
cur_time = 0
is_play = False


def music_get():
	with open("templates/music.html", 'r', encoding='utf-8') as f:
		html = f.read()
	s = ''
	music_list = []#['a','b','C'*70]*10
	for song in music_list:
		s += '<tr><td><input class="music_names" type="submit" name="song" value="{}"></td></tr>'.format(song)
	
	html = html.replace('{{music_list}}', s)
	d = dict(DEFAULT_TEMPLATE)
	return render_template_string(html, **d)

def music_post():
	global song_list, cur_speed, cur_song, cur_time, is_play
	form = tuple(fl_req.form.items())
	if len(form) != 1:
		fl_abort(400)
	key, val = form[0]
	if key == 'song':
		# Change to music val
		pass
	elif key == 'stop':
		# Stop
		pass
	elif key == 'play':
		# Play
		pass
	elif key == 'pause':
		# Pause
		pass
	elif key in ['slower', 'faster']:
		pass
	elif len(form) == 6 and form[:4] == 'time':
		pass
	else:
		fl_req(400)
	return music_get()

def intro_get():
	with open("templates/intro.html", 'r', encoding='utf-8') as f:
		html = f.read()
	return render_template_string(html)#render_template("intro.html")

def index_get():
	return render_template("index.html")

def main_get():
	return redirect('index.html')

if __name__ == '__main__':
	app = Flask(__name__)
	# app._static_folder = "./static"

	app.add_url_rule("/", methods = ('GET',), view_func = main_get)
	app.add_url_rule("/index.html", methods = ('GET',), view_func = index_get)
	app.add_url_rule("/intro.html", methods = ('GET',), view_func = intro_get)

	app.add_url_rule("/interact/light.html", methods = ('GET',), view_func = light_get)
	app.add_url_rule("/interact/light.html", methods = ('POST',), view_func = light_post)

	app.add_url_rule("/interact/jianlu.html", methods = ('GET',), view_func = jianlu_get)
	app.add_url_rule("/interact/jianlu.html", methods = ('POST',), view_func = jianlu_post)

	app.add_url_rule("/interact/hesuan.html", methods = ('GET',), view_func = hesuan_get)

	app.add_url_rule("/interact/car.html", methods = ('GET',), view_func = car_get)

	#app.add_url_rule("/interact/music.html", methods = ('GET', 'POST'), view_func = music_get)

	light_ch = NetCh(SERVER_IP, PI_IP, 'light')
	jianlu_ch = NetCh(SERVER_IP, PI_IP, 'jianlu')
	hesuan_ch = NetCh(SERVER_IP, PI_IP, 'hesuan')
	car_ch = NetCh(SERVER_IP, PI_IP, 'car')

	jianlu_ch.set_send_retf(jianlu_srf)
	hesuan_ch.set_send_retf(hesuan_srf)

	light_lock = Lock()
	jianlu_lock = Lock()
	hesuan_lock = Lock()

	NetCh.start()
	app.run(host = APP_IP, port = PORT)
	NetCh.end()

'''
ms_stat = 'Stop'
@app.route("/server/music", methods = ['GET'])
def _ms_l():
	global ms_stat
	return ms_stat
'''