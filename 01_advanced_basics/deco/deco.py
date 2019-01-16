#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import update_wrapper


def disable(func):
    """
    Disable a decorator by re-assigning the decorator's name
    to this function. For example, to turn off memoization:
    >>> memo = disable
    """

    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
        pass

    return update_wrapper(wrapper, func)


def decorator(deco, func):
    """
    Decorate a decorator so that it inherits the docstrings
    and stuff from the function it's decorating.
    """
    ret = update_wrapper(deco, func)
    if hasattr(func, 'calls'):
        ret.calls = func.calls
    return ret


def countcalls(func):
    """Decorator that counts calls made to the function decorated."""

    def countcalls_wrapper(*args, **kwargs):
        countcalls_wrapper.calls[0] += 1
        return func(*args, **kwargs)

    countcalls_wrapper.calls = [0]
    return decorator(countcalls_wrapper, func)


def memo(func):
    """
    Memoize a function so that it caches all return values for
    faster future lookups.
    """

    def memo_wrapper(*args, **kwargs):
        if args in memo_wrapper.mem:
            # print('recover from memo[', args, ']=', wrapper.mem[args])
            return memo_wrapper.mem[args]
        else:
            memo_wrapper.mem[args] = func(*args, **kwargs)
            # print('save to memo[',args,']=', memo_wrapper.mem[args])
            return memo_wrapper.mem[args]

    memo_wrapper.mem = dict()
    return decorator(memo_wrapper, func)


def n_ary(func):
    """
    Given binary function f(x, y), return an n_ary function such
    that f(x, y, z) = f(x, f(y,z)), etc. Also allow f(x) = x.
    """

    def nary_wrapper(*args):
        if len(args) == 1:
            return args[0]
        elif len(args) == 2:
            return func(args[0], args[1])
        else:
            return func(args[0], nary_wrapper(*args[1:]))

    return decorator(nary_wrapper, func)


def trace(trace_symbols):
    """Trace calls made to function decorated.
    @trace("____")
    def fib(n):
        ....

    >>> fib(3)
     --> fib(3)
    ____ --> fib(2)
    ________ --> fib(1)
    ________ <-- fib(1) == 1
    ________ --> fib(0)
    ________ <-- fib(0) == 1
    ____ <-- fib(2) == 2
    ____ --> fib(1)
    ____ <-- fib(1) == 1
     <-- fib(3) == 3

    """

    def decorate(func):
        def wrapper(*args):
            print(trace_symbols * wrapper.count, ' --> ', func.__name__, '(', *args, ')', sep='')
            wrapper.count += 1
            res = func(*args)
            wrapper.count -= 1
            print(trace_symbols * wrapper.count, ' <-- ', func.__name__, '(', *args, ')', ' == ', res, sep='')
            return res

        wrapper.count = 0
        return decorator(wrapper, func)

    return decorate


# memo = disable

@memo
@countcalls
@n_ary
def foo(a, b):
    return a + b


@countcalls
@memo
@n_ary
def bar(a, b):
    return a * b


@countcalls
@trace("####")
@memo
def fib(n):
    """Some doc"""
    return 1 if n <= 1 else fib(n - 1) + fib(n - 2)


def main():
    print(foo(4, 3))
    print(foo(4, 3, 2))
    print(foo(4, 3))
    print("foo was called", foo.calls, "times")

    print(bar(4, 3))
    print(bar(4, 3, 2))
    print(bar(4, 3, 2, 1))
    print("bar was called", bar.calls, "times")

    print(fib.__doc__)
    fib(3)
    print(fib.calls, 'calls made')


if __name__ == '__main__':
    main()
