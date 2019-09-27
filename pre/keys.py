import binascii

# from . import ecdsa
from ecdsa import der
from ecdsa import rfc6979
from ecdsa.curves import NIST192p, find_curve
from util import string_to_number, number_to_string, randrange
from ecdsa.util import sigencode_string, sigdecode_string
from ecdsa.util import oid_ecPublicKey, encoded_oid_ecPublicKey
from six import PY3, b
from hashlib import sha1
import ellipticcurve

class BadSignatureError(Exception):
    pass
class BadDigestError(Exception):
    pass

class VerifyingKey:
    def __init__(self, _error__please_use_generate=None):
        if not _error__please_use_generate:
            raise TypeError("Please use SigningKey.generate() to construct me")

    @classmethod
    def from_public_point(klass, point, curve=NIST192p, hashfunc=sha1):
        self = klass(_error__please_use_generate=True)
        self.curve = curve
        self.default_hashfunc = hashfunc
        self.pubkey = Public_key(curve.generator, point)
        self.pubkey.order = curve.order
        return self

    @classmethod
    def from_string(klass, string, curve=NIST192p, hashfunc=sha1,
                    validate_point=True):
        order = curve.order
        assert len(string) == curve.verifying_key_length, \
               (len(string), curve.verifying_key_length)
        xs = string[:curve.baselen]
        ys = string[curve.baselen:]
        assert len(xs) == curve.baselen, (len(xs), curve.baselen)
        assert len(ys) == curve.baselen, (len(ys), curve.baselen)
        x = string_to_number(xs)
        y = string_to_number(ys)
        if validate_point:
            assert point_is_valid(curve.generator, x, y)
        from . import ellipticcurve
        point = ellipticcurve.Point(curve.curve, x, y, order)
        return klass.from_public_point(point, curve, hashfunc)

    @classmethod
    def from_pem(klass, string):
        return klass.from_der(der.unpem(string))

    @classmethod
    def from_der(klass, string):
        # [[oid_ecPublicKey,oid_curve], point_str_bitstring]
        s1,empty = der.remove_sequence(string)
        if empty != b(""):
            raise der.UnexpectedDER("trailing junk after DER pubkey: %s" %
                                    binascii.hexlify(empty))
        s2,point_str_bitstring = der.remove_sequence(s1)
        # s2 = oid_ecPublicKey,oid_curve
        oid_pk, rest = der.remove_object(s2)
        oid_curve, empty = der.remove_object(rest)
        if empty != b(""):
            raise der.UnexpectedDER("trailing junk after DER pubkey objects: %s" %
                                    binascii.hexlify(empty))
        assert oid_pk == oid_ecPublicKey, (oid_pk, oid_ecPublicKey)
        curve = find_curve(oid_curve)
        point_str, empty = der.remove_bitstring(point_str_bitstring)
        if empty != b(""):
            raise der.UnexpectedDER("trailing junk after pubkey pointstring: %s" %
                                    binascii.hexlify(empty))
        assert point_str.startswith(b("\x00\x04"))
        return klass.from_string(point_str[2:], curve)

    def to_string(self):
        # VerifyingKey.from_string(vk.to_string()) == vk as long as the
        # curves are the same: the curve itself is not included in the
        # serialized form
        order = self.pubkey.order
        x_str = number_to_string(self.pubkey.point.x(), order)
        y_str = number_to_string(self.pubkey.point.y(), order)
        return x_str + y_str

    def to_pem(self):
        return der.topem(self.to_der(), "PUBLIC KEY")

    def to_der(self):
        order = self.pubkey.order
        x_str = number_to_string(self.pubkey.point.x(), order)
        y_str = number_to_string(self.pubkey.point.y(), order)
        point_str = b("\x00\x04") + x_str + y_str
        return der.encode_sequence(der.encode_sequence(encoded_oid_ecPublicKey,
                                                       self.curve.encoded_oid),
                                   der.encode_bitstring(point_str))

    def verify(self, signature, data, hashfunc=None, sigdecode=sigdecode_string):
        hashfunc = hashfunc or self.default_hashfunc
        digest = hashfunc(data).digest()
        return self.verify_digest(signature, digest, sigdecode)

    def verify_digest(self, signature, digest, sigdecode=sigdecode_string):
        if len(digest) > self.curve.baselen:
            raise BadDigestError("this curve (%s) is too short "
                                 "for your digest (%d)" % (self.curve.name,
                                                           8*len(digest)))
        number = string_to_number(digest)
        r, s = sigdecode(signature, self.pubkey.order)
        sig = Signature(r, s)
        if self.pubkey.verifies(number, sig):
            return True
        raise BadSignatureError

class SigningKey:
    def __init__(self, _error__please_use_generate=None):
        if not _error__please_use_generate:
            raise TypeError("Please use SigningKey.generate() to construct me")

    @classmethod
    def generate(klass, curve=NIST192p, entropy=None, hashfunc=sha1):
        secexp = randrange(curve.order, entropy)
        return klass.from_secret_exponent(secexp, curve, hashfunc)

    # to create a signing key from a short (arbitrary-length) seed, convert
    # that seed into an integer with something like
    # secexp=util.randrange_from_seed__X(seed, curve.order), and then pass
    # that integer into SigningKey.from_secret_exponent(secexp, curve)

    @classmethod
    def from_secret_exponent(klass, secexp, curve=NIST192p, hashfunc=sha1):
        self = klass(_error__please_use_generate=True)
        self.curve = curve
        self.default_hashfunc = hashfunc
        self.baselen = curve.baselen
        n = curve.order
        assert 1 <= secexp < n
        pubkey_point = curve.generator*secexp
        pubkey = Public_key(curve.generator, pubkey_point)
        pubkey.order = n
        self.verifying_key = VerifyingKey.from_public_point(pubkey_point, curve,
                                                            hashfunc)
        self.privkey = Private_key(pubkey, secexp)
        self.privkey.order = n
        return self

    @classmethod
    def from_string(klass, string, curve=NIST192p, hashfunc=sha1):
        assert len(string) == curve.baselen, (len(string), curve.baselen)
        secexp = string_to_number(string)
        return klass.from_secret_exponent(secexp, curve, hashfunc)

    @classmethod
    def from_pem(klass, string, hashfunc=sha1):
        # the privkey pem file has two sections: "EC PARAMETERS" and "EC
        # PRIVATE KEY". The first is redundant.
        if PY3 and isinstance(string, str):
            string = string.encode()
        privkey_pem = string[string.index(b("-----BEGIN EC PRIVATE KEY-----")):]
        return klass.from_der(der.unpem(privkey_pem), hashfunc)
    @classmethod
    def from_der(klass, string, hashfunc=sha1):
        # SEQ([int(1), octetstring(privkey),cont[0], oid(secp224r1),
        #      cont[1],bitstring])
        s, empty = der.remove_sequence(string)
        if empty != b(""):
            raise der.UnexpectedDER("trailing junk after DER privkey: %s" %
                                    binascii.hexlify(empty))
        one, s = der.remove_integer(s)
        if one != 1:
            raise der.UnexpectedDER("expected '1' at start of DER privkey,"
                                    " got %d" % one)
        privkey_str, s = der.remove_octet_string(s)
        tag, curve_oid_str, s = der.remove_constructed(s)
        if tag != 0:
            raise der.UnexpectedDER("expected tag 0 in DER privkey,"
                                    " got %d" % tag)
        curve_oid, empty = der.remove_object(curve_oid_str)
        if empty != b(""):
            raise der.UnexpectedDER("trailing junk after DER privkey "
                                    "curve_oid: %s" % binascii.hexlify(empty))
        curve = find_curve(curve_oid)

        # we don't actually care about the following fields
        #
        #tag, pubkey_bitstring, s = der.remove_constructed(s)
        #if tag != 1:
        #    raise der.UnexpectedDER("expected tag 1 in DER privkey, got %d"
        #                            % tag)
        #pubkey_str = der.remove_bitstring(pubkey_bitstring)
        #if empty != "":
        #    raise der.UnexpectedDER("trailing junk after DER privkey "
        #                            "pubkeystr: %s" % binascii.hexlify(empty))

        # our from_string method likes fixed-length privkey strings
        if len(privkey_str) < curve.baselen:
            privkey_str = b("\x00")*(curve.baselen-len(privkey_str)) + privkey_str
        return klass.from_string(privkey_str, curve, hashfunc)

    def to_string(self):
        secexp = self.privkey.secret_multiplier
        s = number_to_string(secexp, self.privkey.order)
        return s

    def to_pem(self):
        # TODO: "BEGIN ECPARAMETERS"
        return der.topem(self.to_der(), "EC PRIVATE KEY")

    def to_der(self):
        # SEQ([int(1), octetstring(privkey),cont[0], oid(secp224r1),
        #      cont[1],bitstring])
        encoded_vk = b("\x00\x04") + self.get_verifying_key().to_string()
        return der.encode_sequence(der.encode_integer(1),
                                   der.encode_octet_string(self.to_string()),
                                   der.encode_constructed(0, self.curve.encoded_oid),
                                   der.encode_constructed(1, der.encode_bitstring(encoded_vk)),
                                   )

    def get_verifying_key(self):
        return self.verifying_key

    def sign_deterministic(self, data, hashfunc=None, sigencode=sigencode_string):
        hashfunc = hashfunc or self.default_hashfunc
        digest = hashfunc(data).digest()

        return self.sign_digest_deterministic(digest, hashfunc=hashfunc, sigencode=sigencode)

    def sign_digest_deterministic(self, digest, hashfunc=None, sigencode=sigencode_string):
        """
        Calculates 'k' from data itself, removing the need for strong
        random generator and producing deterministic (reproducible) signatures.
        See RFC 6979 for more details.
        """
        secexp = self.privkey.secret_multiplier
        k = rfc6979.generate_k(
            self.curve.generator.order(), secexp, hashfunc, digest)

        return self.sign_digest(digest, sigencode=sigencode, k=k)

    def sign(self, data, entropy=None, hashfunc=None, sigencode=sigencode_string, k=None):
        """
        hashfunc= should behave like hashlib.sha1 . The output length of the
        hash (in bytes) must not be longer than the length of the curve order
        (rounded up to the nearest byte), so using SHA256 with nist256p is
        ok, but SHA256 with nist192p is not. (In the 2**-96ish unlikely event
        of a hash output larger than the curve order, the hash will
        effectively be wrapped mod n).

        Use hashfunc=hashlib.sha1 to match openssl's -ecdsa-with-SHA1 mode,
        or hashfunc=hashlib.sha256 for openssl-1.0.0's -ecdsa-with-SHA256.
        """

        hashfunc = hashfunc or self.default_hashfunc
        h = hashfunc(data).digest()
        return self.sign_digest(h, entropy, sigencode, k)

    def sign_digest(self, digest, entropy=None, sigencode=sigencode_string, k=None):
        if len(digest) > self.curve.baselen:
            raise BadDigestError("this curve (%s) is too short "
                                 "for your digest (%d)" % (self.curve.name,
                                                           8*len(digest)))
        number = string_to_number(digest)
        r, s = self.sign_number(number, entropy, k)
        return sigencode(r, s, self.privkey.order)

    def sign_number(self, number, entropy=None, k=None):
        # returns a pair of numbers
        order = self.privkey.order
        # privkey.sign() may raise RuntimeError in the amazingly unlikely
        # (2**-192) event that r=0 or s=0, because that would leak the key.
        # We could re-try with a different 'k', but we couldn't test that
        # code, so I choose to allow the signature to fail instead.

        # If k is set, it is used directly. In other cases
        # it is generated using entropy function
        if k is not None:
            _k = k
        else:
            _k = randrange(order, entropy)

        assert 1 <= _k < order
        sig = self.privkey.sign(number, _k)
        return sig.r, sig.s


class Signature( object ):
  """ECDSA signature.
  """
  def __init__( self, r, s ):
    self.r = r
    self.s = s



class Public_key( object ):
  """Public key for ECDSA.
  """

  def __init__( self, generator, point ):
    """generator is the Point that generates the group,
    point is the Point that defines the public key.
    """

    self.curve = generator.curve()
    self.generator = generator
    self.point = point
    n = generator.order()
    if not n:
      raise RuntimeError("Generator point must have order.")
    if not n * point == ellipticcurve.INFINITY:
      raise RuntimeError("Generator point order is bad.")
    if point.x() < 0 or n <= point.x() or point.y() < 0 or n <= point.y():
      raise RuntimeError("Generator point has x or y out of range.")


  def verifies( self, hash, signature ):
    """Verify that signature is a valid signature of hash.
    Return True if the signature is valid.
    """

    # From X9.62 J.3.1.

    G = self.generator
    n = G.order()
    r = signature.r
    s = signature.s
    if r < 1 or r > n-1: return False
    if s < 1 or s > n-1: return False
    c = numbertheory.inverse_mod( s, n )
    u1 = ( hash * c ) % n
    u2 = ( r * c ) % n
    xy = u1 * G + u2 * self.point
    v = xy.x() % n
    return v == r



class Private_key( object ):
  """Private key for ECDSA.
  """

  def __init__( self, public_key, secret_multiplier ):
    """public_key is of class Public_key;
    secret_multiplier is a large integer.
    """

    self.public_key = public_key
    self.secret_multiplier = secret_multiplier

  def sign( self, hash, random_k ):
    """Return a signature for the provided hash, using the provided
    random nonce.  It is absolutely vital that random_k be an unpredictable
    number in the range [1, self.public_key.point.order()-1].  If
    an attacker can guess random_k, he can compute our private key from a
    single signature.  Also, if an attacker knows a few high-order
    bits (or a few low-order bits) of random_k, he can compute our private
    key from many signatures.  The generation of nonces with adequate
    cryptographic strength is very difficult and far beyond the scope
    of this comment.

    May raise RuntimeError, in which case retrying with a new
    random value k is in order.
    """

    G = self.public_key.generator
    n = G.order()
    k = random_k % n
    p1 = k * G
    r = p1.x()
    if r == 0: raise RuntimeError("amazingly unlucky random number r")
    s = ( numbertheory.inverse_mod( k, n ) * \
          ( hash + ( self.secret_multiplier * r ) % n ) ) % n
    if s == 0: raise RuntimeError("amazingly unlucky random number s")
    return Signature( r, s )



def int_to_string( x ):
  """Convert integer x into a string of bytes, as per X9.62."""
  assert x >= 0
  if x == 0: return b('\0')
  result = []
  while x:
    ordinal = x & 0xFF
    result.append(int2byte(ordinal))
    x >>= 8

  result.reverse()
  return b('').join(result)


def string_to_int( s ):
  """Convert a string of bytes into an integer, as per X9.62."""
  result = 0
  for c in s:
    if not isinstance(c, int): c = ord( c )
    result = 256 * result + c
  return result


def digest_integer( m ):
  """Convert an integer into a string of bytes, compute
     its SHA-1 hash, and convert the result to an integer."""
  #
  # I don't expect this function to be used much. I wrote
  # it in order to be able to duplicate the examples
  # in ECDSAVS.
  #
  from hashlib import sha1
  return string_to_int( sha1( int_to_string( m ) ).digest() )


def point_is_valid( generator, x, y ):
  """Is (x,y) a valid public key based on the specified generator?"""

  # These are the tests specified in X9.62.

  n = generator.order()
  curve = generator.curve()
  if x < 0 or n <= x or y < 0 or n <= y:
    return False
  if not curve.contains_point( x, y ):
    return False
  if not n*ellipticcurve.Point( curve, x, y ) == \
     ellipticcurve.INFINITY:
    return False
  return True



# NIST Curve P-192:
_p = 6277101735386680763835789423207666416083908700390324961279
_r = 6277101735386680763835789423176059013767194773182842284081
# s = 0x3045ae6fc8422f64ed579528d38120eae12196d5L
# c = 0x3099d2bbbfcb2538542dcd5fb078b6ef5f3d6fe2c745de65L
_b = 0x64210519e59c80e70fa7e9ab72243049feb8deecc146b9b1
_Gx = 0x188da80eb03090f67cbf20eb43a18800f4ff0afd82ff1012
_Gy = 0x07192b95ffc8da78631011ed6b24cdd573f977a11e794811

curve_192 = ellipticcurve.CurveFp( _p, -3, _b )
generator_192 = ellipticcurve.Point( curve_192, _Gx, _Gy, _r )


# NIST Curve P-224:
_p = 26959946667150639794667015087019630673557916260026308143510066298881
_r = 26959946667150639794667015087019625940457807714424391721682722368061
# s = 0xbd71344799d5c7fcdc45b59fa3b9ab8f6a948bc5L
# c = 0x5b056c7e11dd68f40469ee7f3c7a7d74f7d121116506d031218291fbL
_b = 0xb4050a850c04b3abf54132565044b0b7d7bfd8ba270b39432355ffb4
_Gx =0xb70e0cbd6bb4bf7f321390b94a03c1d356c21122343280d6115c1d21
_Gy = 0xbd376388b5f723fb4c22dfe6cd4375a05a07476444d5819985007e34

curve_224 = ellipticcurve.CurveFp( _p, -3, _b )
generator_224 = ellipticcurve.Point( curve_224, _Gx, _Gy, _r )

# NIST Curve P-256:
_p = 115792089210356248762697446949407573530086143415290314195533631308867097853951
_r = 115792089210356248762697446949407573529996955224135760342422259061068512044369
# s = 0xc49d360886e704936a6678e1139d26b7819f7e90L
# c = 0x7efba1662985be9403cb055c75d4f7e0ce8d84a9c5114abcaf3177680104fa0dL
_b = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b
_Gx = 0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296
_Gy = 0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5

curve_256 = ellipticcurve.CurveFp( _p, -3, _b )
generator_256 = ellipticcurve.Point( curve_256, _Gx, _Gy, _r )

# NIST Curve P-384:
_p = 39402006196394479212279040100143613805079739270465446667948293404245721771496870329047266088258938001861606973112319
_r = 39402006196394479212279040100143613805079739270465446667946905279627659399113263569398956308152294913554433653942643
# s = 0xa335926aa319a27a1d00896a6773a4827acdac73L
# c = 0x79d1e655f868f02fff48dcdee14151ddb80643c1406d0ca10dfe6fc52009540a495e8042ea5f744f6e184667cc722483L
_b = 0xb3312fa7e23ee7e4988e056be3f82d19181d9c6efe8141120314088f5013875ac656398d8a2ed19d2a85c8edd3ec2aef
_Gx = 0xaa87ca22be8b05378eb1c71ef320ad746e1d3b628ba79b9859f741e082542a385502f25dbf55296c3a545e3872760ab7
_Gy = 0x3617de4a96262c6f5d9e98bf9292dc29f8f41dbd289a147ce9da3113b5f0b8c00a60b1ce1d7e819d7a431d7c90ea0e5f

curve_384 = ellipticcurve.CurveFp( _p, -3, _b )
generator_384 = ellipticcurve.Point( curve_384, _Gx, _Gy, _r )

# NIST Curve P-521:
_p = 6864797660130609714981900799081393217269435300143305409394463459185543183397656052122559640661454554977296311391480858037121987999716643812574028291115057151
_r = 6864797660130609714981900799081393217269435300143305409394463459185543183397655394245057746333217197532963996371363321113864768612440380340372808892707005449
# s = 0xd09e8800291cb85396cc6717393284aaa0da64baL
# c = 0x0b48bfa5f420a34949539d2bdfc264eeeeb077688e44fbf0ad8f6d0edb37bd6b533281000518e19f1b9ffbe0fe9ed8a3c2200b8f875e523868c70c1e5bf55bad637L
_b = 0x051953eb9618e1c9a1f929a21a0b68540eea2da725b99b315f3b8b489918ef109e156193951ec7e937b1652c0bd3bb1bf073573df883d2c34f1ef451fd46b503f00
_Gx = 0xc6858e06b70404e9cd9e3ecb662395b4429c648139053fb521f828af606b4d3dbaa14b5e77efe75928fe1dc127a2ffa8de3348b3c1856a429bf97e7e31c2e5bd66
_Gy = 0x11839296a789a3bc0045c8a5fb42c7d1bd998f54449579b446817afbd17273e662c97ee72995ef42640c550b9013fad0761353c7086a272c24088be94769fd16650

curve_521 = ellipticcurve.CurveFp( _p, -3, _b )
generator_521 = ellipticcurve.Point( curve_521, _Gx, _Gy, _r )

# Certicom secp256-k1
_a  = 0x0000000000000000000000000000000000000000000000000000000000000000
_b  = 0x0000000000000000000000000000000000000000000000000000000000000007
_p  = 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f
_Gx = 0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798
_Gy = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8
_r  = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141

curve_secp256k1 = ellipticcurve.CurveFp( _p, _a, _b)
generator_secp256k1 = ellipticcurve.Point( curve_secp256k1, _Gx, _Gy, _r)

