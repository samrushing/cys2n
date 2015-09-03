# -*- Mode: Python -*-

import logging
import os
import random
import socket
import ssl
import threading
import time

from hashlib import sha512

logger = logging.getLogger (__name__)

# use sha512 as a random-data generator.
# pre-generate 10MB of random data to iterate through

def gen_random_data (seed='fnord'):
    logger.info ('generate data: start')
    blocks = []
    h = sha512()
    data = seed
    nblocks = (1024 * 1024 * 10) / 64
    for i in range (nblocks):
        h.update (data)
        data = h.digest()
        blocks.append (data)
    logger.info ('generate data: stop')
    return blocks

random_blocks = gen_random_data()

class random_char_gen:

    def __init__ (self):
        self.index = 0
        self.blocks = random_blocks

    def next (self):
        result = self.blocks[self.index]
        self.index += 1
        if self.index == len(self.blocks):
            self.index = 0
        return result

class random_block:

    def __init__ (self, gen):
        self.gen = gen
        self.buffer = self.gen.next()
        self.random = random.Random (3141)

    def next (self, size):
        while 1:
            if size <= len(self.buffer):
                result, self.buffer = self.buffer[:size], self.buffer[size:]
                return result
            else:
                self.buffer += self.gen.next()

    def random_size (self):
        size = self.random.randrange (10, 500)
        return self.next (size)

rbytes = 0
wbytes = 0

def feed (s):
    global wbytes
    blockgen = random_block (random_char_gen())
    while 1:
        block = blockgen.random_size()
        s.send (block)
        wbytes += len (block)

def monitor (interval=10):
    global rbytes, wbytes
    while 1:
        r0, w0 = rbytes, wbytes
        time.sleep (interval)
        r = rbytes - r0
        w = wbytes - w0
        logger.info ('throughput read %d write %d', r / interval, w / interval)

def session (addr):
    logging.info ('pid: %d', os.getpid())
    global rbytes
    s = ssl.wrap_socket (socket.socket (socket.AF_INET, socket.SOCK_STREAM))
    s.connect (addr)
    t0 = threading.Thread (target=feed, args=(s,))
    t0.daemon = True
    t0.start()
    t1 = threading.Thread (target=monitor)
    t1.daemon = True
    t1.start()
    # generates the same stream of characters we sent
    blockgen = random_block (random_char_gen())
    while 1:
        data = s.recv (500)
        rbytes += len (data)
        assert (data == blockgen.next (len (data)))

if __name__ == '__main__':
    logging.basicConfig (level=logging.DEBUG)
    session (('127.0.0.1', 7777))
