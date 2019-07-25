import unittest
from unittest.mock import patch
import redis
from server.store import Store
from tests.cases import cases



class TestStore(unittest.TestCase):

    @cases([(1, 2),
            (b'test', 'string '*100),
            (1, '3')])
    def test_cache_get_what_set(self, key, val):
        store = Store(host="localhost", port="6379", db='_not_exist_test_db_')
        store.cache_set(key, val)
        self.assertEqual(val, store.cache_get(key), "with key = %s and val = %s" % (key, val))

    def test_LRU_cache(self):
        size = 10  # cache size
        used_index = [2, 4, 5]  # these keys are used frequently
        lost_index = [3, 6, 7]
        store = Store(host="localhost", port="6379", db='_not_exist_test_db_', cache_size=size)
        with patch('redis.Redis.get') as mock_get:
            mock_get.return_value = None
            with patch('redis.Redis.set') as mock_set:
                for i in range(size*50):
                    store.cache_set(i, i*i)
                    j = i % len(used_index)
                    if j < i:
                        self.assertEqual(j*j, store.cache_get(j))
            for j in lost_index:
                self.assertIsNone(store.cache_get(j))

    def test_cache_get_noraises_when_nodata(self):
        store = Store(host="localhost", port="6379", db='_not_exist_test_db_')
        try:
            val = store.cache_get('unknown_key')
        except Exception:
            self.fail('Store.cache_get() raised exception, but never must')

    def test_get_raises_when_disconnected(self):
        store = Store(host="localhost", port="6379", db='_not_exist_test_db_')
        with patch('redis.Redis.get') as mock:
            mock.side_effect = redis.RedisError('Test error')
            self.assertRaises(redis.RedisError, store.get, 'key')

    def test_get_attempts_when_errors(self):
        store = Store(host="localhost", port="6379", db='_not_exist_test_db_')
        with patch('redis.Redis.get') as mock:
            mock.side_effect = redis.RedisError('Test error')
            try:
                val = store.get('key')
            except redis.RedisError:
                pass
            self.assertGreater(mock.call_count, 1)

    def test_set_raises_when_disconnected(self):
        store = Store(host="localhost", port="6379", db='_not_exist_test_db_')
        with patch('redis.Redis.set') as mock:
            mock.side_effect = redis.RedisError('Test error')
            self.assertRaises(redis.RedisError, store.set, 'test_key', 'test_val')

    def test_set_attempts_when_errors(self):
        store = Store(host="localhost", port="6379", db='_not_exist_test_db_')
        with patch('redis.Redis.set') as mock:
            mock.side_effect = redis.RedisError('Test error')
            try:
                val = store.set('test_key', 'test_val')
            except redis.RedisError:
                pass
            self.assertGreater(mock.call_count, 1)
