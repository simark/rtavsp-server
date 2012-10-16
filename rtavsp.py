# -*- coding: utf-8 -*-
from twisted.internet import protocol
import simplejson
import time

'''
Classe qui garde les stats d'un abonnement.
'''
class SubscribeStats:
  def __init__(self):
    self.nb_frames = 0
    self.start_time = time.time()
    self.last_frame_time = None
    self.total_bytes_sent = 0

'''
Classe dont une instance est creee pour chaque connexion entrante.
'''
class RTAVSP(protocol.Protocol):
  def __init__(self, log, addr, server):
    self.log = log
    self.addr = addr
    self.server = server
    self.current_streams = dict()
    self.current_streams_stats = dict()
    self.data_available = ""
    self.connect_time = None
    self.last_commands = list()

  def __del__(self):
    self.log.debug("RTAVSP instance " + str(self.addr) + " gets deleted")

  def connectionMade(self):
    self.log.info("Connection accepted from %s", self.transport.getPeer())
    self.server.stlog.info("%s | Connexion acceptée.", self.addr)
    self.server.addClient(self)
    self.sendWelcomeMessage()
    self.connect_time = time.time()

  def connectionLost(self, reason):
    self.server.removeClient(self)
    self.server.stlog.info("%s | Connexion fermée.", self.addr)
    self.log.info("Connection lost")

  def sendFrame(self, stream_id, data):
    self.updateFrameStats(stream_id, data)
    self.transport.write(data)

  def updateFrameStats(self, stream_id, data):
    stats = self.current_streams_stats[stream_id]
    stats.nb_frames += 1
    stats.last_frame_time = time.time()
    stats.total_bytes_sent += len(data)

  def dataReceived(self, data):
    self.log.debug('Data received: %s', data)
    self.server.stlog.info("%s | %d octets recus.", self.addr, len(data))

    self.data_available += data
    self.data_available = self.data_available.lstrip()

    try:
      while len(self.data_available) > 0:
        request, rest = simplejson.loads(self.data_available, strict=False)
        self.log.debug("Parsed request " + str(request))
        self.log.debug("Data remaining: %s (%d bytes)", rest, len(rest))
        self.server.stlog.info("%s | Message JSON décodé avec succès.", self.addr)
        self.data_available = rest
        self.handleRequest(request)
    except simplejson.JSONDecodeError, e:
      self.log.debug("Decode fail: " + str(e))  
      self.log.debug("Data avail: %s", self.data_available)
      self.server.stlog.info("%s | Erreur de décodage JSON: %s", self.addr, str(e))  
  
  def handleRequest(self, request):
    self.log.debug("HandleRequest " + str(request))
    self.server.stlog.info("%s | Début de l'interprétation de la requête.", self.addr)
    try:
      if 'cmd' not in request:
        self.server.stlog.info("%s | Attribut 'cmd' absent de la requête.", self.addr)

      cmd = request['cmd']
      self.server.stlog.info("%s | Commande: %s", self.addr, cmd)
      if cmd == "jouer" or cmd == "lecture":
        if 'flux' not in request:
          self.server.stlog.info("%s | Attribut 'flux' absent de la requête.", self.addr)

        streams = request['flux']
        if not isinstance(streams, list):
          self.server.stlog.info("%s | Erreur, type de la liste de flux invalide.", self.addr)
          raise Exception("Invalid type for list of streams: " + str(type(streams)))
        
        self.last_commands.append( (cmd, streams, time.time()) )

        for stream_id in streams:
          if not isinstance(stream_id, int):
            self.server.stlog.info("%s | Erreur, type d'id de flux invalide: %s", self.addr, type(stream_id))
            self.log.debug("Client asked to play stream id that is not int: %s", type(stream_id))
            continue
            
          if stream_id not in self.server.streams:
            self.server.stlog.info("%s | Erreur, flux non-existant: %d", self.addr, stream_id)
            self.log.debug("Client asked to play nonexistent stream %d", stream_id)
            continue

          self.server.stlog.info("%s | Abonnement au flux %d.", self.addr, stream_id)
          stream = self.server.streams[stream_id]
          stream.subscribe(self)
          self.current_streams_stats[stream_id] = SubscribeStats()
          self.current_streams[stream_id] = stream
          
      elif cmd == "arret":
        if 'flux' not in request:
          self.server.stlog.info("%s | Attribut 'flux' absent de la requête.", self.addr)

        streams = request['flux']
        if streams is not None and not isinstance(streams, list):
          self.server.stlog.info("%s | Erreur, type de la liste de flux invalide.", self.addr)
          raise Exception("Invalid type for list of streams: " + str(type(streams)))

        self.last_commands.append( (cmd, streams, time.time()) )

        if streams is None:
          streams = self.current_streams.keys()

        for stream_id in streams:
          if not isinstance(stream_id, int):
            self.server.stlog.info("%s | Erreur, type d'id de flux invalide: %s", self.addr, type(stream_id))
            self.log.debug("Client asked to stop stream id that is not int: %s", type(stream_id))
            continue
            
          if stream_id not in self.server.streams:
            self.server.stlog.info("%s | Erreur, flux non-existant: %d", self.addr, stream_id)
            self.log.debug("Client asked to stop nonexistent stream %d", stream_id)
            continue

          self.server.stlog.info("%s | Désabonnement du flux %d.", self.addr, stream_id)
          stream = self.server.streams[stream_id]
          stream.unsubscribe(self)
          self.current_streams.pop(stream_id, None)
          self.current_streams_stats.pop(stream_id, None)
          
      else:
        self.server.stlog.info("%s | Erreur, commande invalide: %s", self.addr, cmd)
        raise Exception("Invalid cmd: " + str(cmd))
    except Exception, e:
      self.log.debug("Error while processing request: " + repr(e))

  def sendWelcomeMessage(self):
    msg = {}
    msg['version-maj'] = 1
    msg['version-min'] = 1
    msg['nom'] = 'Le serveur de Jerome'
    msg['flux'] = {}
    
    for stream_id in self.server.streams:
      stream = self.server.streams[stream_id]
      msg['flux'][stream_id] = stream.stream_info
    
    json_msg = simplejson.dumps(msg, sort_keys = True)
    
    self.transport.write(json_msg)
    
'''
Classe qui permet de creer des RTAVSP.
'''
class RTAVSPFactory(protocol.Factory):
  def __init__(self, server):
    self.server = server

  def buildProtocol(self, addr):
    return RTAVSP(self.server.log, addr, self.server)
