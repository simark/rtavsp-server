# -*- coding: utf-8 -*-
import threading
import os
import select
import errno
import time
import simplejson
from twisted.internet import reactor

def wrapInJpegSegment(data):
  l = len(data) + 2
  l_high = (l >> 8) & 0xff;
  l_low = l & 0xff
  
  ret = '\xFF\xE3'
  ret += chr(l_high)
  ret += chr(l_low)
  ret += data
  
  return ret

def injectJpegSegment(image, data):
  segment = wrapInJpegSegment(data)

  # The app0 segment has to be the first after SOI
  idx = 4
  app0_size = (ord(image[idx]) << 8) | (ord(image[idx+1]))
  idx += app0_size
  ret = image[:idx] + segment + image[idx:]

  f = open("bob.jpg", "w")
  f.write(ret)
  f.close()

  return ret

'''
Methode un peu louche pour lire jusqu'a la fin du pipe non bloquant.
'''
def safe_read(fd, size = 4096):
  while True:
    try:
      part = os.read(fd, size)
      return part
    except OSError, e:
      if e.errno != errno.EAGAIN:
        raise

''' Broadcast un stream, et oui. '''
class Stream:
  def __init__(self, log, stream_id, shortname, name, description):
    ''' Liste de clients connectes, instances de RTAVSP.'''
    self.log = log
    self.clients = set()
    self.stream_id = stream_id
    self.name = name
    self.shortname = shortname
    self.description = description
    self.last_image = None
    self.last_image_size = 0
    self.last_metadata = None
    self.stream_info = dict()
    self.stream_info['id'] = stream_id
    self.stream_info['nom'] = name
    self.stream_info['desc'] = description
    
  def __str__(self):
    return "%s<%d>" % (self.shortname, self.stream_id)
    
  def subscribe(self, protocol_instance):
    if protocol_instance not in self.clients:
      self.log.info("Client %s subscribed to %s", protocol_instance.transport.getPeer(), self)
      self.clients.add(protocol_instance)
    else:
      self.log.info("Client %s wants to subscribe to %s but he already is.", protocol_instance.transport.getPeer(), self)

  def unsubscribe(self, protocol_instance):
    if protocol_instance in self.clients:
      self.log.info("Client %s unsubscribed from %s", protocol_instance.transport.getPeer(), self)
      self.clients.remove(protocol_instance)
    else:
      self.log.info("Client %s wants to unsubscribe to %s but he already is.", protocol_instance.transport.getPeer(), self)

  def pipePath(self):
    return "stream-%s/current.jpg" % (self.shortname)

  def broadcast(self, image):
    def writeToClients(clients, stream_id, data):
      for client in clients:
        client.sendFrame(stream_id, data)

    self.log.info("Broadcast %d bytes on stream %s." % (len(image), self.stream_id))

    data = ""

    metadata = {}
    metadata['id'] = self.stream_id
    metadata['date'] = time.strftime("%Y-%m-%d")
    metadata['heure'] = time.strftime("%H:%M:%S")
    metadata['soustitre'] = "Telecran - " + metadata['heure']
    metadata_json = simplejson.dumps(metadata)
    image = injectJpegSegment(image, metadata_json)
    
    clients = list(self.clients)
    reactor.callFromThread(writeToClients, clients, self.stream_id, image)

    self.last_metadata = metadata_json
    self.last_image = image
    self.last_image_size = len(image)

'''
Thread qui attend des donnees sur les pipes de chaque stream.
'''
class SelectThread(threading.Thread):
  def __init__(self, streams, log):
    threading.Thread.__init__(self)
    self.daemon = True
    self.log = log
    self.streams = streams

  def run(self):
    def createFifo(path):
      if os.path.exists(path):
        os.unlink(path)
      os.mkfifo(path)

    self.log.info('Select thread started.')
    rlist = []
    fd_to_stream = {}

    for stream_id in self.streams:
      stream = self.streams[stream_id]
      fifo_path = stream.pipePath()
      createFifo(fifo_path)
      fd = os.open(fifo_path, os.O_RDONLY | os.O_NONBLOCK)
      rlist.append(fd)
      fd_to_stream[fd] = stream
      self.log.info("Opened %s" %(fifo_path))


    self.log.info("Entering select loop")
    while True:
      self.log.info("Entering select call")
      (ready_r, ready_w, ready_x) = select.select(rlist, [], [])

      for fd in ready_r:
        stream = fd_to_stream[fd]
        fifo_path = stream.pipePath()
        self.log.debug("Data available to read on fd = %d (%s)." % (fd, fifo_path))

        # Lire tout jusqu'a EOF
        content = ""
        part = safe_read(fd)
        while len(part) > 0:
          content += part
          part = safe_read(fd)

        # Ferme egalement le fd sous-jacent
        os.close(fd)

        self.log.debug("Read %d bytes from it." % (len(content)))
        stream.broadcast(content)

        # On doit fermer le pipe et le reouvrir
        rlist.remove(fd)
        del fd_to_stream[fd]

        newfd = os.open(fifo_path, os.O_RDONLY | os.O_NONBLOCK)

        rlist.append(newfd)
        fd_to_stream[newfd] = stream