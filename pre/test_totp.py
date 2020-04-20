from __future__ import print_function

import random
import time

import numbertheory
import util

l = 2**8-1
# q = util.randrange(l*2)
p = numbertheory.next_prime(2**38)
# print(hex(q), q)
print(hex(p), p)

g = random.randrange(1, p)
s = random.randrange(1, p)

print('s', s, 's % p', s % p)

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

# print(numbertheory.lcm2(((p-1)*r+s), t))
# print(numbertheory.phi(p))

k = (numbertheory.modular_exp(t, numbertheory.phi(p-1)-1, (p-1)) *s) % (p-1)
print('s', s, 'kt%(p-1)', (k*t)%(p-1), s == (k*t)%(p-1))
print('g^s', numbertheory.modular_exp(g, s, p), 'g^(kt)', numbertheory.modular_exp(g, k*t, p))

k = (numbertheory.modular_exp(t, numbertheory.phi(p)-1, p) *s) % p
print('s', s, 'kt%p', (k*t)%p)
print('g^s', numbertheory.modular_exp(g, s, p), 'g^(kt)', numbertheory.modular_exp(g, k*t, p))

# r = 0
# while True:
#     r += 1
#     # print((p*r+s)%t, t)
#     # if (p*r+s)%t == 0:
#     if ((p-1)*r+s)%t == 0:
#         break
# print('r', r)
# k = int((p*r+s)/t)
# print('k', k)
# print(numbertheory.modular_exp(g, k*t, p), numbertheory.modular_exp(g, s, p))

t2 = time.time()
print('t2', t2 - t1)
