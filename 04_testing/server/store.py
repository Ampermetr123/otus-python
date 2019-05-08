import redis
import time
import logging
from functools import wraps


def attempts(max_attempts, timeout):
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            counter = max_attempts
            while counter > 0:
                try:
                    return func(*args, **kwargs)
                except BaseException as ex:
                    counter = counter-1
                    if counter > 0:
                        logging.debug("Function {0}({1}) call failed with '{2}'  // Repeat again ({3}/{4})".format(func.__name__, str(args[1:]), str(ex), str(counter), str(max_attempts)))
                        time.sleep(timeout)
                        continue
                    else:
                        raise
        return wrapper
    return decorate


class Store():
    """ Обеспечивает чтение/запись данных изхранилища и/или кэша
        Алгоритм кэша LRU с ограничением - таким образом ограничивается потребление памяти.
        Используется в Python 3.7+ , где гарантируется LIFO для dict
    """
    def __init__(self, host="localhost", port="6379", db=0, cache_size=1000):
        self.r = redis.Redis(host, port, db, socket_timeout=0.5, socket_connect_timeout=0.5)
        self.cache = {}
        self.cache_size = cache_size

    @attempts(3, 0.3)
    def set(self, key, val):
        self.r.set(key,val)

    @attempts(3, 0.3)
    def get(self, key):
        val = self.r.get(key)
        return val

    def cache_get(self, key):
        """ Getting from cache or storage - No throws errors"""
        # В данном случае, внутри можно реализовать это и как хождение в одно и тоже хранилище.
        # Важно то, как это будет протестировано с учетом разных требований для разных функций
        try:
            self.cache[key] = self.cache.pop(key)
            return self.cache[key]
        except KeyError:
            try:
                self.cache[key] = self.r.get(key)
                return self.cache[key]
            except redis.RedisError:
                return None

    def cache_set(self, key, val, timeout):
        """ Setting value to cache and storage -  No throws errors"""

        # if key exists - moving it to the end
        try:
            self.cache.pop(key)
        except KeyError:
            pass

        self.cache[key] = val

        while len(self.cache) > self.cache_size:
            self.cache.popitem(last=False)

        try:
            return self.r.set(key, val)
        except redis.RedisError:
            pass


if __name__ == "__main__":
    pass
