# -*- Mode: Cython -*-

from cpython.bytes cimport PyBytes_FromStringAndSize
from libc.stdint cimport uint64_t, uint32_t, uint16_t, uint8_t
from libc.errno cimport errno, EAGAIN as EWOULDBLOCK

import sys
W = sys.stderr.write

class MODE:
    SERVER = S2N_SERVER
    CLIENT = S2N_CLIENT

class Error (Exception):
    pass

class Want (Exception):
    pass

class WantRead (Want):
    pass

class WantWrite (Want):
    pass

cdef raise_s2n_error():
    raise Error (s2n_strerror (s2n_errno, "EN"))

cdef check (int n):
    if n != 0:
        raise_s2n_error()

def init():
    check (s2n_init())

def cleanup():
    check (s2n_cleanup())

init()

cdef class Config:

    #cdef s2n_config * c

    def __init__ (self):
        self.c = s2n_config_new()
        if not self.c:
            raise_s2n_error()

    def __del__ (self):
        if self.c:
            check (s2n_config_free (self.c))

    def set_cipher_preferences (self, bytes version):
        check (s2n_config_set_cipher_preferences (self.c, version))

    def add_cert_chain_and_key (self, bytes chain_pem, bytes skey_pem):
        check (s2n_config_add_cert_chain_and_key (self.c, chain_pem, skey_pem))

    def add_cert_chain_and_key_with_status (self, bytes chain_pem, bytes skey_pem):
        cdef uint8_t status[512]
        check (s2n_config_add_cert_chain_and_key_with_status (self.c, chain_pem, skey_pem, &status[0], sizeof(status)))
        return <char*>status

    def add_dhparams (self, bytes dhparams_pem):
        check (s2n_config_add_dhparams (self.c, dhparams_pem))

    def set_protocol_preferences (self, protocols):
        cdef char * protos[50]
        cdef int count = 0
        assert (len(protocols) < 50)
        for i, proto in enumerate (protocols):
            protos[i] = proto
            count += 1
        check (s2n_config_set_protocol_preferences (self.c, <const char **> protos, count))

    def set_status_request_type (self, s2n_status_request_type stype):
        check (s2n_config_set_status_request_type (self.c, stype))

cdef maybe_string (char * s):
    if s:
        return s
    else:
        return None

cdef class Connection:

    #cdef s2n_connection * conn

    def __init__ (self, s2n_mode mode):
        self.conn = s2n_connection_new (mode)
        if not self.conn:
            raise_s2n_error()

    def __del__ (self):
        if self.conn:
            check (s2n_connection_free (self.conn))

    def set_config (self, Config cfg):
        check (s2n_connection_set_config (self.conn, cfg.c))

    def set_fd (self, int readfd):
        check (s2n_connection_set_fd (self.conn, readfd))

    def set_read_fd (self, int readfd):
        check (s2n_connection_set_read_fd (self.conn, readfd))

    def set_write_fd (self, int readfd):
        check (s2n_connection_set_write_fd (self.conn, readfd))

    def set_server_name (self, bytes server_name):
        check (s2n_set_server_name (self.conn, server_name))

    def get_server_name (self):
        return maybe_string (s2n_get_server_name (self.conn))

    def set_blinding (self, s2n_blinding blinding):
        check (s2n_connection_set_blinding (self.conn, blinding))

    def get_delay (self):
        return s2n_connection_get_delay (self.conn)

    def get_wire_bytes (self):
        return (
            s2n_connection_get_wire_bytes_in (self.conn),
            s2n_connection_get_wire_bytes_out (self.conn),
        )

    def get_client_hello_version (self):
        return s2n_connection_get_client_hello_version (self.conn)

    def get_client_protocol_version (self):
        return s2n_connection_get_client_protocol_version (self.conn)

    def get_server_protocol_version (self):
        return s2n_connection_get_server_protocol_version (self.conn)

    def get_actual_protocol_version (self):
        return s2n_connection_get_actual_protocol_version (self.conn)

    def get_application_protocol (self):
        return maybe_string (s2n_get_application_protocol (self.conn))

    def get_ocsp_response (self):
        cdef const uint8_t * r
        cdef uint32_t length
        r = s2n_connection_get_ocsp_response (self.conn, &length)
        return r[:length]

    def get_alert (self):
        return s2n_connection_get_alert (self.conn)

    def get_cipher (self):
        return maybe_string (s2n_connection_get_cipher (self.conn))

    # I/O

    # override these if you're using an event-driven system.
    cdef want_read (self):
        raise WantRead

    cdef want_write (self):
        raise WantWrite

    cdef bint _check_blocked (self, int r, s2n_blocked_status blocked, int errno) except -1:
        if r < 0:
            if errno == EWOULDBLOCK:
                if blocked == S2N_BLOCKED_ON_READ:
                    self.want_read()
                    return True
                elif blocked == S2N_BLOCKED_ON_WRITE:
                    self.want_write()
                    return True
                else:
                    raise_s2n_error()
            else:
                raise OSError (errno)
        else:
            return False

    cpdef negotiate (self):
        cdef s2n_blocked_status blocked = S2N_NOT_BLOCKED
        cdef int r = 0
        cdef int saved_errno = 0
        while 1:
            with nogil:
                r = s2n_negotiate (self.conn, &blocked)
                saved_errno = errno
            if not self._check_blocked (r, blocked, saved_errno):
                break

    cpdef send (self, bytes data, int pos=0):
        cdef s2n_blocked_status blocked = S2N_NOT_BLOCKED
        cdef ssize_t n
        cdef const char * p = <const char *>(data) + pos
        cdef ssize_t dlen = len(data)
        assert (pos < len(data))
        while 1:
            with nogil:
                n = s2n_send (self.conn, p, dlen - pos, &blocked)
            if not self._check_blocked (n, blocked, errno):
                break
        return n, blocked

    cpdef recv (self, ssize_t size):
        cdef s2n_blocked_status blocked = S2N_NOT_BLOCKED
        cdef bytes result = PyBytes_FromStringAndSize (NULL, size)
        cdef char * p = <char*>result
        cdef ssize_t n = 0
        cdef int saved_errno = 0
        while 1:
            with nogil:
                n = s2n_recv (self.conn, p, size, &blocked)
                saved_errno = errno
            if n < 0 and saved_errno == 0 and s2n_errno == 0:
                return '', 0
            elif not self._check_blocked (n, blocked, saved_errno):
                break
        return result[:n], blocked

    cpdef shutdown (self):
        cdef s2n_blocked_status blocked = S2N_NOT_BLOCKED
        cdef int r = 0
        while 1:
            with nogil:
                r = s2n_shutdown (self.conn, &blocked)
            if not self._check_blocked (r, blocked, errno):
                break
        return blocked
