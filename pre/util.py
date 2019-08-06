from __future__ import division

import os
import math
import binascii
# from hashlib import sha256
# from . import der
# from .curves import orderlen
# from .six import PY3, int2byte, b, next
# import der
# from curves import orderlen
from six import PY3, int2byte, b, next

# RFC5480:
#   The "unrestricted" algorithm identifier is:
#     id-ecPublicKey OBJECT IDENTIFIER ::= {
#       iso(1) member-body(2) us(840) ansi-X9-62(10045) keyType(2) 1 }

def orderlen(order):
    return (1+len("%x"%order))//2 # bytes

def randrange(order, entropy=None):
    """Return a random integer k such that 1 <= k < order, uniformly
    distributed across that range. For simplicity, this only behaves well if
    'order' is fairly close (but below) a power of 256. The try-try-again
    algorithm we use takes longer and longer time (on average) to complete as
    'order' falls, rising to a maximum of avg=512 loops for the worst-case
    (256**k)+1 . All of the standard curves behave well. There is a cutoff at
    10k loops (which raises RuntimeError) to prevent an infinite loop when
    something is really broken like the entropy function not working.

    Note that this function is not declared to be forwards-compatible: we may
    change the behavior in future releases. The entropy= argument (which
    should get a callable that behaves like os.urandom) can be used to
    achieve stability within a given release (for repeatable unit tests), but
    should not be used as a long-term-compatible key generation algorithm.
    """
    # we could handle arbitrary orders (even 256**k+1) better if we created
    # candidates bit-wise instead of byte-wise, which would reduce the
    # worst-case behavior to avg=2 loops, but that would be more complex. The
    # change would be to round the order up to a power of 256, subtract one
    # (to get 0xffff..), use that to get a byte-long mask for the top byte,
    # generate the len-1 entropy bytes, generate one extra byte and mask off
    # the top bits, then combine it with the rest. Requires jumping back and
    # forth between strings and integers a lot.

    if entropy is None:
        entropy = os.urandom
    assert order > 1
    bytes = orderlen(order)
    dont_try_forever = 10000 # gives about 2**-60 failures for worst case
    while dont_try_forever > 0:
        dont_try_forever -= 1
        candidate = string_to_number(entropy(bytes)) + 1
        if 1 <= candidate < order:
            return candidate
        continue
    raise RuntimeError("randrange() tried hard but gave up, either something"
                       " is very wrong or you got realllly unlucky. Order was"
                       " %x" % order)

def number_to_string(num, order):
    l = orderlen(order)
    fmt_str = "%0" + str(2*l) + "x"
    string = binascii.unhexlify((fmt_str % num).encode())
    assert len(string) == l, (len(string), l)
    return string

def number_to_string_crop(num, order):
    l = orderlen(order)
    fmt_str = "%0" + str(2*l) + "x"
    string = binascii.unhexlify((fmt_str % num).encode())
    return string[:l]

def string_to_number(string):
    return int(binascii.hexlify(string), 16)

def string_to_number_fixedlen(string, order):
    l = orderlen(order)
    assert len(string) == l, (len(string), l)
    return int(binascii.hexlify(string), 16)
