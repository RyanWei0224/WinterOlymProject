# -*- coding: utf-8 -*-

from config import PASSWD, CH_PORT, NETCH_DEBUG

from flask import Flask, request as fl_req, abort as fl_abort
import requests
import ctypes

######### FUTURE WORK #########
# Use multi-PROCESS instead of multi-THREAD, 
# since python can only run one thread at a time

#from multiprocessing import Process, SimpleQueue as mpQueue
from threading import Thread

class NetCh:
	'''A network channel between ip addresses.'''

	#QUERY_FUNCS = dict()
	#SEND_FUNCS = dict()
	FLASK_APPS = dict()
	FLASK_THDS = dict()

	def __init__(self, cur_ip, other_ip, channel_name, other_port = CH_PORT, port = CH_PORT, timeout = 3):
		'''
		Create the channel with the other end at other_ip:port/netch/channel_name
		'''

		'''
		Create the channel with the other end at other_ip:port/(nameOther)/channel_name
		The name of this side is nameThis.
		end_name: a tuple of form (nameThis, nameOther)
		end_name = True  represents ('server', 'client')
		end_name = False represents ('client', 'server')
		if end_name is True:
			end_name = ('server', 'client')
		elif end_name is False:
			end_name = ('client', 'server')
		'''
		self._rule = "/netch/{}".format(channel_name)
		self.other_url = "http://{}:{}{}".format(other_ip, other_port, self._rule)
		self.TIMEOUT = timeout
		self.port = port
		self._ip = cur_ip

		self.app = None
		self._run_thread = None

	def init_app(self):
		if self.app is not None:
			return
		key = (self._ip, self.port)
		if key in self.FLASK_APPS:
			self.app = self.FLASK_APPS[key]
		else:
			self.app = Flask(__name__)
			self.app._static_folder = "./static"
			self.FLASK_APPS[key] = self.app

	def set_query_retf(self, f):
		self.init_app()
		#QUERY_FUNCS[self._rule] = (mpQueue(), mpQueue())

		@self.app.get(self._rule, endpoint = self._rule + '_qrf')
		def qrf():
			form = fl_req.get_json(silent = True)
			if form is None or form.get('passwd', None) != PASSWD:
				fl_abort(404)
			if 'data' in form:
				ret_data = f(form['data'])
			else:
				ret_data = f()
			return {'passwd' : PASSWD, 'data' : ret_data}

	def set_send_retf(self, f):
		self.init_app()

		@self.app.post(self._rule, endpoint = self._rule + '_srf')
		def srf():
			form = fl_req.get_json(silent = True)
			if form is None or form.get('passwd', None) != PASSWD or 'data' not in form:
				fl_abort(404)
			ret_data = f(form['data'])
			return {'passwd' : PASSWD, 'data' : ret_data}

	def query_once(self, data = None):
		try:
			json_dict = {'passwd' : PASSWD, 'data' : data} if data is not None else {'passwd' : PASSWD}
			res = requests.get(self.other_url, json = json_dict, timeout=self.TIMEOUT)
			res.raise_for_status()
			data = res.json()
			if data.get('passwd', None) != PASSWD or 'data' not in data:
				if NETCH_DEBUG:
					print('\n[NetCh.query_once] Invalid data!\n')
				return None
		except Exception as e:
			if NETCH_DEBUG:
				print('\n[NetCh.query_once] Error querying data: {} of type {}\n'.format(e, type(e)))
			return None
		return {'data' : data['data']}

	def send_once(self, data):
		try:
			res = requests.post(self.other_url, json = {'passwd' : PASSWD, 'data' : data}, timeout=self.TIMEOUT)
			res.raise_for_status()
			data = res.json()
			if data.get('passwd', None) != PASSWD or 'data' not in data:
				if NETCH_DEBUG:
					print('\n[NetCh.send_once] Invalid data!\n')
				return None
		except Exception as e:
			if NETCH_DEBUG:
				print('\n[NetCh.send_once] Error sending data: {} of type {}\n'.format(e, type(e)))
			return None
		return {'data' : data['data']}

	def query(self, data = None, tries = 3):
		res = None
		while tries != 0 and res is None:
			res = self.query_once(data)
			tries -= 1
		return res

	def send(self, data, tries = 3):
		res = None
		while tries != 0 and res is None:
			res = self.send_once(data)
			tries -= 1
		return res

	@classmethod
	def start(cls):
		for (host, port), app in cls.FLASK_APPS.items():
			_run_thread = Thread(target = app.run, 
								kwargs = {'host' : host, 'port' : port})
			_run_thread.start()
			cls.FLASK_THDS[(host, port)] = _run_thread

	@classmethod
	def end(cls):
		def stop_thread(thread):
			tid = thread.ident
			res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), ctypes.py_object(KeyboardInterrupt))
			if res == 0:
				raise ValueError("invalid thread id")
			elif res != 1:
				# """if it returns a number greater than one, you're in trouble,
				# and you should call it again with exc=NULL to revert the effect"""
				ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
				raise SystemError("PyThreadState_SetAsyncExc failed")

		for addr, thr in cls.FLASK_THDS.items():
			if thr.is_alive():
				stop_thread(thr)
			#del cls.FLASK_APPS[addr]
		cls.FLASK_THDS.clear()

		'''
		Another way to shutdown:

		def shutdown_server():
			func = request.environ.get('werkzeug.server.shutdown')
			if func is None:
				raise RuntimeError('Not running with the Werkzeug Server')
			func()

		@app.route('/api/shutdown')
		def shutdown():
			shutdown_server()
			return 'Server shutting down...'
		'''

	def __del__(self):
		self.end()
