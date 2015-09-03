
CyS2N
=====

This is a [Cython](http://cython.org/) interface to Amazon's [S2N](https://github.com/awslabs/s2n) Library.

See the ``tests`` directory for a simple multi-threaded echo server.
The echo client uses Python's SSLSocket to test it.  S2N client mode
has not been tested yet.

Installing
----------

Assuming you have the s2n library installed on your system:

```shell
$ python setup.py install
```
