from __future__ import print_function

import random
import time

import numbertheory



def factorization( n ):
  """Decompose n into a list of (prime,exponent) pairs."""

  assert isinstance( n, numbertheory.integer_types )

  if n < 2: return []

  result = []
  d = 2

  # Test the small primes:

  for d in numbertheory.smallprimes:
    if d > n: break
    q, r = divmod( n, d )
    if r == 0:
      count = 1
      while d <= n:
        n = q
        q, r = divmod( n, d )
        if r != 0: break
        count = count + 1
      result.append( ( d, count ) )

  # If n is still greater than the last of our small primes,
  # it may require further work:

  if n > numbertheory.smallprimes[-1]:
    if numbertheory.is_prime( n ):   # If what's left is prime, it's easy:
      result.append( ( n, 1 ) )
    else:               # Ugh. Search stupidly for a divisor:
      d = numbertheory.smallprimes[-1]
      return
      while 1:
        d = d + 2               # Try the next divisor.
        print(d)
        q, r = divmod( n, d )
        if q < d: break         # n < d*d means we're done, n = 1 or prime.
        if r == 0:              # d divides n. How many times?
          count = 1
          n = q
          while d <= n:                 # As long as d might still divide n,
            q, r = divmod( n, d )       # see if it does.
            if r != 0: break
            n = q                       # It does. Reduce n, increase count.
            count = count + 1
          result.append( ( d, count ) )
      if n > 1: result.append( ( n, 1 ) )

  return result


def phi( n ):
  """Return the Euler totient function of n."""

  assert isinstance( n, numbertheory.integer_types )

  if n < 3: return 1

  result = 1
  ff = factorization( n )
  if ff is None:
      return
  for f in ff:
    e = f[1]
    if e > 1:
      result = result * f[0] ** (e-1) * ( f[0] - 1 )
    else:
      result = result * ( f[0] - 1 )
  return result


# l = 2**8-1
# q = util.randrange(l*2)
p = numbertheory.next_prime(2**2099+159100)
while True:
    phi_value = phi(p-1)
    if phi_value is not None:
        break
    p = numbertheory.next_prime(p)
    print('try next prime', p)

print('phi', phi_value)

# print(hex(q), q)
# print(hex(p), p)

g = random.randrange(1, p)
s = random.randrange(1, p)

print('s', s, 'p', p, 's%p', s % p)

current_time = time.time()
# t = int(current_time - current_time % 60)
t = int(current_time)
# t = 11
# print('t', t)

t0 = time.time()
# k = 0
# while True:
#     k += 1
#     # if numbertheory.modular_exp(g, k*t, p) == numbertheory.modular_exp(g, s, p):
#     if (k*t) % (p-1) == s:
#         break
# print('k', k)
# print(numbertheory.modular_exp(g, k*t, (p)), numbertheory.modular_exp(g, s, (p)))

# print(numbertheory.modular_exp(g, k*t+(p-1), (p)), numbertheory.modular_exp(g, s, (p)))
# print(numbertheory.modular_exp(g, (k*t) % (p-1), (p)), numbertheory.modular_exp(g, s, (p)))
t1 = time.time()
# print('t1', t1 - t0)

while numbertheory.gcd2(p-1, t) != 1:
    print('gcd(', p-1, t, ')', numbertheory.gcd2(p-1, t))
    t += 1
print('gcd(', p-1, t, ')', numbertheory.gcd2(p-1, t))
print('t', t)

exp_value = numbertheory.modular_exp(t, phi_value-1, (p-1))
print('exp', exp_value)
k = (exp_value *s) % (p-1)
print('s', s, 'kt%(p-1)', (k*t)%(p-1), s == (k*t)%(p-1), k)
print('g^s', numbertheory.modular_exp(g, s, p), 'g^(kt)', numbertheory.modular_exp(g, k*t, p))

# k = (numbertheory.modular_exp(t, numbertheory.phi(p)-1, p) *s) % p
# print('s', s, 'kt%p', (k*t)%p)
# print('g^s', numbertheory.modular_exp(g, s, p), 'g^(kt)', numbertheory.modular_exp(g, k*t, p))

t2 = time.time()
print('t2', t2 - t1)
