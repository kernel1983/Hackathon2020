from __future__ import print_function

import random
# import os
import time
# import shutil
# import subprocess
# from binascii import hexlify, unhexlify
# from hashlib import sha1, sha256, sha512

import pyaes


# A 256 bit (32 byte) key
key = b"This_key_for_demo_purposes_only!"

# For some modes of operation we need a random initialization vector
# of 16 bytes
iv = "InitializationVe"
iv = "1234567890abcdef"



aes = pyaes.AESModeOfOperationCTR(key)
# plaintext = "Text may be any length you wish, no padding is required"
plaintext = 'This is the PRE!This is the PRE!This is the PRE!This is the PRE!'
plaintext = plaintext[:-16]
print(plaintext)
t0 = time.time()
for i in range(10):
    for i in range(100000):
        ciphertext = aes.encrypt(plaintext)
    t1 = time.time()
    # print(ciphertext)
    # print(len(plaintext), len(ciphertext))
    print(t1-t0)

# '''\xb6\x99\x10=\xa4\x96\x88\xd1\x89\x1co\xe6\x1d\xef;\x11\x03\xe3\xee
#    \xa9V?wY\xbfe\xcdO\xe3\xdf\x9dV\x19\xe5\x8dk\x9fh\xb87>\xdb\xa3\xd6
#    \x86\xf4\xbd\xb0\x97\xf1\t\x02\xe9 \xed'''
# print repr(ciphertext)

# The counter mode of operation maintains state, so decryption requires
# a new instance be created
# aes = pyaes.AESModeOfOperationCTR(key)
# decrypted = aes.decrypt(ciphertext)

# True
# print decrypted == plaintext
