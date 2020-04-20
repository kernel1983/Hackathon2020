
import sys
import base64
import hashlib
# from urllib3 import encode_multipart_formdata

import requests
from ecdsa import SigningKey, NIST256p

# for i in range(10):
#     sk_filename = "pk%s" % i
#     # sk = keys.UmbralPrivateKey.gen_key()
#     # open("data/pk/"+sk_filename, "w").write(sk.to_bytes().hex())
#     sk = SigningKey.generate(curve=NIST256p)
#     open("data/pk/"+sk_filename, "w").write(bytes.decode(sk.to_pem()))

# login with sk
# first file to upload
# split into blobs
# query nodes and get response
# create meta
# upload meta
# write on chain


def cmd_login(sk_filename):
    pass

def cmd_logout():
    pass


def cmd_add(local_filename):
    url = 'http://127.0.0.1:8001/fs/new_file_blob'
    print(local_filename)
    file_to_upload = open(local_filename, 'rb')
    while True:
        file_chunk = file_to_upload.read(1024*1024)
        file_chunk_size = len(file_chunk)
        if file_chunk_size == 0:
            break
        print(file_chunk_size)
        file_chunk_hash = hashlib.sha256(file_chunk).hexdigest()
        print(file_chunk_hash)

        # file_size = file_to_upload.size()
        files = {'field1': file_chunk}
        response = requests.post(url, files=files)

if __name__ == "__main__":
    # print(sys.argv[1])
    cmd = sys.argv[1]

    if cmd == 'add':
        local_filename = sys.argv[2]
        cmd_add(local_filename)

