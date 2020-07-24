
def price(summary, value):
    total = sum([l*a for l, a in summary.items()])
    print(total)
    # weights = [total/l/a for l, a in summary.items()]
    # print(weights)
    weight = sum([total/l for l, a in summary.items()])
    return {l:total/l/a/weight*value for l, a in summary.items()}


print(price({1:2, 2:10, 7:60}, 100*12*7))

