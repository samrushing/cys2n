# -*- Mode: Python -*-

import socket
import unittest

from cys2n import *

class s2n_socket:

    def __init__ (self, cfg, pysock, conn=None):
        self.cfg = cfg
        self.sock = pysock
        self.fd = pysock.fileno()
        self.conn = conn
        self.negotiated = False

    def __repr__ (self):
        return '<s2n sock=%r conn=%r @%x>' % (self.sock, self.conn, id (self))

    def bind (self, *args, **kwargs):
        return self.sock.bind (*args, **kwargs)

    def listen (self, *args, **kwargs):
        return self.sock.listen (*args, **kwargs)

    def accept (self):
        sock, addr = self.sock.accept()
        conn = Connection (MODE.SERVER)
        conn.set_config (self.cfg)
        conn.set_fd (sock.fileno())
        # XXX verify
        new = self.__class__ (self.cfg, sock, conn)
        return new, addr

    # XXX client mode as yet untested.
    def connect (self, addr):
        self.sock.connect (addr)
        self.conn = Connection (MODE.CLIENT)
        self.conn.set_config (self.cfg)
        self.conn.set_fd (self.fd)

    def _check_negotiated (self):
        if not self.negotiated:
            while 1:
                blocked = self.conn.negotiate()
                if not blocked:
                    break
            self.negotiated = True

    def recv (self, block_size):
        self._check_negotiated()
        r = []
        left = block_size
        while left:
            b, more = self.conn.recv (left)
            r.append (b)
            if not more:
                break
            else:
                left -= len(b)
                #self.wait_for_read()
        return ''.join (r)

    def send (self, data):
        self._check_negotiated()
        pos = 0
        left = len(data)
        while left:
            n, more = self.conn.send (data, pos)
            pos += n
            if not more:
                break
            else:
                #self.wait_for_write()
                pass
            left -= n
        return pos

    def shutdown (self, how=None):
        more = 1
        while more:
            more = self.conn.shutdown()

    def close (self):
        try:
            self.shutdown()
        finally:
            self.sock.close()

