
import sys
import base64
import hashlib
import json
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
    url = 'http://127.0.0.1:8001'
    print(local_filename)
    file_to_upload = open(local_filename, 'rb')
    chunks_list = []
    chunks_dict = {}
    nodes_dict = {}
    while True:
        file_chunk = file_to_upload.read(1024*1024)
        file_chunk_size = len(file_chunk)
        if file_chunk_size == 0:
            break
        print(file_chunk_size)
        file_chunk_hash = hashlib.sha256(file_chunk).hexdigest()
        file_chunk_hash_bin = bin(int(file_chunk_hash, 16))[2:].zfill(256)
        print(file_chunk_hash, file_chunk_hash_bin)

        while True:
            # print("fetch chain", block_hash)
            try:
                # response = yield http_client.fetch("http://%s:%s/get_node?nodeid=%s" % (host, port, blob_bin), request_timeout=300)
                response = requests.get('%s/get_node?nodeid=%s' % (url, file_chunk_hash_bin))
            except:
                # blob.append(prev_nodeid)
                break
            result = response.json()
            print(result)
            nodes_dict[result['nodeid']] = result['address']
            if result['nodeid'] == result['current_nodeid']:
                # blob.append(result['current_nodeid'])
                break
            # print('result >>>>>', result)
            # prev_nodeid = result['current_nodeid']
            host, port = result['address']
            url = 'http://%s:%s' % (host, port)

        chunks_list.append(file_chunk_hash)
        chunks_dict.setdefault(file_chunk_hash, set()) # this is the node path by chunk

        # file_size = file_to_upload.size()
        files = {'field1': file_chunk}
        response = requests.post('%s/fs/new_file_blob' % url, files=files)

    # blockchain select 3 nodes for you
    # 1.accessable
    # 2.available/enough space
    # 3.speed ok
    # keep calling /get_node?nodeid=NODE_ID with chunk hash
    # upload the nodes

    # chunks [["0100111 chunk hash", ["0100111", "010011", "0100"]], ...]
    # meta {"filename": [chunks, [permission1, permission2]], 
    #       "folder"  : 
    #            {"filename1": [chunks, [permission1, permission2, ...]],
    #             "filename2": [chunks, [permission1, permission2, ...]], ...},
    #        "meta"    : ""
    #       }

if __name__ == "__main__":
    # print(sys.argv[1])
    cmd = sys.argv[1]

    if cmd == 'add':
        local_filename = sys.argv[2]
        cmd_add(local_filename)

