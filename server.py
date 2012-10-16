# -*- coding: utf-8 -*-
import sys
import os
import logging
import logging.config
import simplejson

from twisted.internet import reactor
from twisted.web import server
from twisted.web import wsgi

import rtavsp
import webui
import stream

'''
On patch le code de simplejson pour qu'il fasse ce qu'on veut, s'arreter
apres le premier objet JSON decode et retourner le reste de la chaine.
'''
def my_decode(self, s, _w=simplejson.decoder.WHITESPACE.match):
  obj, end = self.raw_decode(s)
  end = _w(s, end).end()
  return obj, s[end:]
 
simplejson.decoder.JSONDecoder.decode = my_decode

'''
Classe demarrant un serveur RTAVSP.
'''
class RTAVSPServer:
  def __init__(self, streams_dir):
    self.factory = rtavsp.RTAVSPFactory(self)
    self.streams = dict()
    self.clients = set()
    self.stlog = logging.getLogger('etudiants')
    self.log = logging.getLogger('interne')
    self.initStreams(streams_dir)

  def initStreams(self, streams_dir):
    l = os.listdir(streams_dir)
    l = filter((lambda d: d.startswith('stream-') and os.path.isdir(d)), l)
    l.sort()

    i = 0
    for d in l:
      shortname = d[len('stream-'):]
      stream_id = i
      self.log.info('Adding stream %d %s.', stream_id, shortname)

      infofile = open(d + os.sep + "info.txt")
      infos = infofile.readlines();
      name = infos.pop(0).strip()
      desc = ''.join(infos).strip()

      self.streams[stream_id] = stream.Stream(self.log, stream_id, shortname, name, desc)
      i = i + 1

    self.log.info('Loaded %d streams.', len(self.streams))

  def startListen(self, port, portHttp):
    ''' avec listenTCP on peut definir l'interface sur laquelle ecouter. '''
    self.selectThread = stream.SelectThread(self.streams, self.log)
    self.selectThread.start()

    # Un peu ghetto... donner au webui une reference vers le serveur.
    webui.app.server = self
    resource = wsgi.WSGIResource(reactor, reactor.getThreadPool(), webui.app)
    reactor.listenTCP(portHttp, server.Site(resource))
    reactor.listenTCP(port, self.factory)
    reactor.run()

  def addClient(self, client):
    self.clients.add(client)

  def removeClient(self, client):
    self.clients.discard(client)
    for stream_id in self.streams:
      self.streams[stream_id].unsubscribe(client)

def initLogging():
  logging.config.fileConfig("logging.conf")

def main(argv):
  initLogging()
  server = RTAVSPServer(os.getcwd())
  server.startListen(1234, 1235)

main(sys.argv)
