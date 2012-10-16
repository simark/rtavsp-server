# -*- coding: utf-8 -*-
import flask
import simplejson
import os

from decorators import templated 
from jinja2 import Environment

import time

app = flask.Flask(__name__)

def load_image_no_image():
	with open('static/img/aucune.jpg') as f:
		return f.read()

image_no_image_sent = load_image_no_image()

def is_int(s):
	try:
		int(s)
		return True
	except:
		return False


@app.route('/')
@templated()
def streams():
  varz = {}

  varz['streams'] = app.server.streams

  return varz


@app.route('/last_image')
def last_image():
	response = ""
	status = 404
	headers = {}
	headers['Cache-control'] = 'no-cache'

	id = flask.request.args.get('id')
	if id is not None and is_int(id):
		id = int(id)
		if id in app.server.streams:
			last_image = app.server.streams[id].last_image
			if last_image is not None:
				response = last_image
				status = 200
				headers['Content-type'] = 'image/jpeg'
			else:
				global image_no_image_sent
				response = image_no_image_sent
				status = 200
				headers['Content-type'] = 'image/jpeg'
		else:
			response = "Image non trouvée - flux inexistant."
	else:
		response = "Image non trouvée - paramètre 'id' manquant ou invalide."
	return (response, status, headers)

@app.route('/liens')
@templated()
def liens():
	return None

@app.route('/clients')
@templated()
def clients():
  varz = {}

  varz['streams'] = app.server.streams
  varz['clients'] = app.server.clients

  return varz

@app.route('/journaux')
@templated()
def log():
	varz = {}
	logs_txt = ""

	if os.path.exists('logs/etudiants.log'):
		f = open('logs/etudiants.log')
		logs = f.readlines()
		f.close()
		logs.reverse()
		logs_txt += unicode(''.join(logs), 'utf8')

	if os.path.exists('logs/etudiants.log.1'):
		f = open('logs/etudiants.log.1')
		logs = f.readlines()
		f.close()
		logs.reverse()
		logs_txt += unicode(''.join(logs), 'utf8')

	varz['log'] = logs_txt.strip()
	return varz

@app.route('/journaux_json')
def logs_json():
	ret = {}
	headers = {'Content-type': 'application/json'}
	logs = []

	if os.path.exists('logs/etudiants.log.1'):
		f = open('logs/etudiants.log.1')
		logs += f.readlines()
		f.close()

	if os.path.exists('logs/etudiants.log'):
		f = open('logs/etudiants.log')
		logs += f.readlines()
		f.close()

	logs.reverse()	

	logs = [ [part.strip() for part in line.split('|')] for line in logs]

	ret['aaData'] = logs
	return (simplejson.dumps(ret), 200, headers)

@app.route('/journaux_texte')
def logs_text():
	ret = {}
	headers = {'Content-type': 'text/plain; charset=utf-8'}
	logs = []

	if os.path.exists('logs/etudiants.log.1'):
		f = open('logs/etudiants.log.1')
		logs += f.readlines()
		f.close()

	if os.path.exists('logs/etudiants.log'):
		f = open('logs/etudiants.log')
		logs += f.readlines()
		f.close()

	logs.reverse()	

	ret = ''.join(logs)
	return (ret, 200, headers)

 # Filters for jinja

def format_since(timestamp):
 	now = time.time()
 	diff = now - timestamp
 	heures = int(diff / 3600)
 	diff -= heures * 3600
 	minutes = int(diff / 60)
 	diff -= minutes * 60
 	secondes = int(diff)

 	heures_s = "s" if heures > 1 else ""
 	minutes_s = "s" if minutes > 1 else ""
 	secondes_s = "s" if secondes > 1 else ""

 	if heures > 0: 
 		return "%d heure%s, %d minute%s, %d seconde%s" % (heures, heures_s, minutes, minutes_s, secondes, secondes_s)
 	elif minutes > 0:
 		return "%d minute%s, %d seconde%s" % (minutes, minutes_s, secondes, secondes_s)
 	else:
 		return "%d seconde%s" % (secondes, secondes_s)

app.jinja_env.filters['format_since'] = format_since

def format_json(obj):
	return simplejson.dumps(obj)

app.jinja_env.filters['format_json'] = format_json
