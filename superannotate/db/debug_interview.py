a = 5


def f():
    global a
    a = 4


f()

print(a)
