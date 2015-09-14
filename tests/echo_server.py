# -*- Mode: Python -*-

import socket
import threading
import logging

import sys
W = sys.stderr.write

from cys2n import PROTOCOL, s2n_socket, Config, Error as S2N_Error

# XXX EC not available in s2n yet?

key = b"""-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQDbXarRaFWNbH7zt7qNLoTV02lEv5FyF0cOFuLXp2uSTpvlfQje
6CCJ4KvEE3cbRr3XReWn9TOLCidvnrIUZ61EpzJ0hNpRoAOb9zzHAxmxrvwRP+xz
KvR57bgsq44p7mZ97N453HFz54mIaLTsAR93qPP5Ao4z3kQi8IOKLP9UHQIDAQAB
AoGAJ4phsO9ShHRrCbkzWiFpdjVuQyMYr2z8tNBxQRf/btbWiO4ZvDwxKUkjDOvJ
S1RcAcKqm7S5/rTs2NTNGpp5g5HfqaqfnRvRTSUwrY9Y7qoouPn61KiDcBgghTL9
GH0v7pOvF0pOpaL/Q5jVv8tWjWXahtpmgHwsBIE44cavyc0CQQD7TfEvG+s17m+e
x0BZV98VpZ6mtP2oC0scgCn+GQ1ZNnhEfFawpY1gYxcQ2H7YP1xCNX0mHg52daum
+pdzXG/bAkEA33b0RzfUJa4Vu2QmuZD50lL6M13u1w60NkHtwQUghVC1BzNLktJs
uQRzHjrxHNy13RzpMWyYND1+Y+DpMwDpZwJAWyG6stC3DUm4JKYxCbU56wmybNX5
nnTp+h3oHINNOers1jkY3tpKWIfWl39LEHR5qnDnP2lq6T5mzxjUzzrYPQJBALjF
VfRxMCQ7zlJU3ERBoJ+M5r6EY9FEojPezaT1BU/WTOj4O/vZq/ZLvJf5apZP1LxQ
hGzOewdu9UvGk2wNy+8CQQDRsF/US06+PrSsWn0uiu+1Fy80PO5SoQmqNDL/olHw
61trvDaDJPIWzqxXuFwhVXZlTFlnaLxg3gAG+bMEqtSg
-----END RSA PRIVATE KEY-----
"""

crt = b"""-----BEGIN CERTIFICATE-----
MIICjzCCAfigAwIBAgIJAOFA3myvL0dJMA0GCSqGSIb3DQEBBQUAMDoxFDASBgNV
BAMTC2V4YW1wbGUuY29tMRUwEwYDVQQKEwxFeGFtcGxlLCBJbmMxCzAJBgNVBAYT
AlVTMB4XDTE1MDcxMTIxMjExOVoXDTE2MDcxMDIxMjExOVowOjEUMBIGA1UEAxML
ZXhhbXBsZS5jb20xFTATBgNVBAoTDEV4YW1wbGUsIEluYzELMAkGA1UEBhMCVVMw
gZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBANtdqtFoVY1sfvO3uo0uhNXTaUS/
kXIXRw4W4tena5JOm+V9CN7oIIngq8QTdxtGvddF5af1M4sKJ2+eshRnrUSnMnSE
2lGgA5v3PMcDGbGu/BE/7HMq9HntuCyrjinuZn3s3jnccXPniYhotOwBH3eo8/kC
jjPeRCLwg4os/1QdAgMBAAGjgZwwgZkwHQYDVR0OBBYEFIj+uemrlTyRZdHTwx8c
dvw6lXj+MGoGA1UdIwRjMGGAFIj+uemrlTyRZdHTwx8cdvw6lXj+oT6kPDA6MRQw
EgYDVQQDEwtleGFtcGxlLmNvbTEVMBMGA1UEChMMRXhhbXBsZSwgSW5jMQswCQYD
VQQGEwJVU4IJAOFA3myvL0dJMAwGA1UdEwQFMAMBAf8wDQYJKoZIhvcNAQEFBQAD
gYEAIxmqzFn2JD4+Yp+wr2P+KiqCeP1NeNuDUsfqbx4p5xgM9fEMX3lnZsWeiCkX
2uv5idrZoUfBAkt1ao4xRAlRjc2TClwK7pNj3JKQQ0PdHVmPsJRQwxafcB1taXFS
14bcAwcAimx5zqYfMZho7tBUxpRd5vp6UVi1nR/9pIlZ7wE=
-----END CERTIFICATE-----
"""

cfg = Config()
cfg.add_cert_chain_and_key (crt, key)

def unproto (n):
    return PROTOCOL.reverse_map.get (n, "unknown")

def echo (conn):
    # force negotiation here (rather than letting it happen transparently)
    #   so we can log all this nice information...
    conn.negotiate()
    s2n = conn.conn
    logging.info ('client_hello_version: %s', unproto (s2n.get_client_hello_version()))
    logging.info ('client_protocol_version: %s', unproto (s2n.get_client_protocol_version()))
    logging.info ('server_protocol_version: %s', unproto (s2n.get_server_protocol_version()))
    logging.info ('actual_protocol_version: %s', unproto (s2n.get_actual_protocol_version()))
    logging.info ('application_protocol: %r', s2n.get_application_protocol())
    logging.info ('cipher: %s', s2n.get_cipher())
    try:
        while 1:
            block = conn.recv (1024)
            if not block:
                break
            else:
                conn.send (block)
    except S2N_Error:
        logging.error ('error in echo session')

def serve (port):
    try:
        s0 = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
        s0.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s1 = s2n_socket (cfg, s0)
        s1.bind (('', port))
        s1.listen (10)
        logging.info ('echo server listening on port %d' % (port,))
        while 1:
            conn, addr = s1.accept()
            t0 = threading.Thread (target=echo, args=(conn,))
            t0.daemon = True
            t0.start()
    except S2N_Error:
        logging.error ('error in echo server')

if __name__ == '__main__':
    logging.basicConfig (level=logging.INFO)
    serve (7777)
