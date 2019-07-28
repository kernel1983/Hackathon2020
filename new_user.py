
import base64
from ecdsa import SigningKey, NIST256p
# from umbral import pre, keys, signing
# import umbral.config


for i in range(10):
    sk_filename = "pk%s" % i
    # sk = keys.UmbralPrivateKey.gen_key()
    # open("data/pk/"+sk_filename, "w").write(sk.to_bytes().hex())
    sk = SigningKey.generate(curve=NIST256p)
    open("data/pk/"+sk_filename, "w").write(bytes.decode(sk.to_pem()))
