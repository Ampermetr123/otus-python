import unittest
import subprocess
import hashlib
import signal
import datetime

import requests
import docker

from server import api
from server import store
from tests.cases import cases


class TestIntegral(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # starting scoring server
        cls.port = 8085
        cls.server_proc = subprocess.Popen(['python.exe', 'server/api.py', '-p', str(cls.port), '-l', 'tests/server.log'],
                                           shell=False, creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP))
        print('http server started on port ', str(cls.port), ' pid=', cls.server_proc.pid)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.server_proc.send_signal(signal.CTRL_C_EVENT)
        try:
            cls.server_proc.wait(1)
        except subprocess.TimeoutExpired:
            cls.server_proc.kill()

        # On Win10 host even kill doens't work ! - So control again
        if cls.server_proc.returncode is None:
            cls.server_proc.terminate()
            print('http server terminated')
        else:
            print('http server stopped with code ', cls.server_proc.returncode)
        # Check again
        if cls.server_proc.returncode is None:
            print('Was not able to shut down server please do it manualy!!! ')

        super().tearDownClass()

    def start_redis_server(self):
        if not hasattr(self, 'redis_cont'):
            self.docker = docker.from_env()
            self.redis_cont = self.docker.containers.run('redis', detach=True,
                                                         ports={6379: 6379})
            print('redis server started')
            self.addCleanup(self.stop_redis_server)  

    def stop_redis_server(self):
        if hasattr(self, 'redis_cont'):
            self.redis_cont.stop()
            self.redis_cont.remove()
            del self.redis_cont
            print('redis server stopped')

    def set_valid_auth(self, request):
        if request.get("login") == api.ADMIN_LOGIN:
            request["token"] = hashlib.sha512((datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT).encode()).hexdigest()
        else:
            msg = request.get("account", "") + request.get("login", "") + api.SALT
            request["token"] = hashlib.sha512(msg.encode()).hexdigest()

    def get_response(self, request):
        url = 'http://127.0.0.1:'+str(self.port)+'/method'
        headers = {'Content-Type': 'application/json'}
        resp = requests.post(url, json=request, headers=headers, timeout=5)
        return resp.json()

    @cases([
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "", "arguments": {}},
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "sdd", "arguments": {}},
        {"account": "horns&hoofs", "login": "admin", "method": "online_score", "token": "", "arguments": {}}
    ])
    def test_bad_auth(self, request):
        answ = self.get_response(request)
        code = answ.get('code')
        self.assertEqual(api.FORBIDDEN, code)

    @cases([
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score"},
        {"account": "horns&hoofs", "login": "h&f", "arguments": {}},
        {"account": "horns&hoofs", "method": "online_score", "arguments": {}},
    ])
    def test_invalid_method_request(self, request):
        self.set_valid_auth(request)
        answ = self.get_response(request)
        code = answ.get('code')
        response = answ.get('response')
        error = answ.get('error')
        self.assertEqual(api.INVALID_REQUEST, code)
        self.assertIsNone(response)
        self.assertIsNotNone(error)

    @cases([
        {},
        {"phone": "79175002040"},
        {"phone": "89175002040", "email": "stupnikov@otus.ru"},
        {"phone": "79175002040", "email": "stupnikovotus.ru"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": -1},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": "1"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.1890"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "XXX"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000", "first_name": 1},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000",
         "first_name": "s", "last_name": 2},
        {"phone": "79175002040", "birthday": "01.01.2000", "first_name": "s"},
        {"email": "stupnikov@otus.ru", "gender": 1, "last_name": 2},
    ])
    def test_invalid_score_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        answ = self.get_response(request)
        code = answ.get('code')
        response = answ.get('response')
        error = answ.get('error')
        self.assertEqual(api.INVALID_REQUEST, code, arguments)
        self.assertIsNone(response)
        self.assertIsNotNone(error)

    @cases([
        {"phone": "79175002040", "email": "stupnikov@otus.ru"},
        {"phone": 79175002040, "email": "stupnikov@otus.ru"},
        {"gender": 1, "birthday": "01.01.2000", "first_name": "a", "last_name": "b"},
        {"gender": 0, "birthday": "01.01.2000"},
        {"gender": 2, "birthday": "01.01.2000"},
        {"first_name": "a", "last_name": "b"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000",
         "first_name": "a", "last_name": "b"},
    ])
    def test_ok_score_request(self, arguments):
        self.start_redis_server()
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        answ = self.get_response(request)
        code = answ.get('code')
        response = answ.get('response')
        error = answ.get('error')
        self.assertEqual(api.OK, code, arguments)
        self.assertIsNone(error)
        score = response.get("score")
        self.assertTrue(isinstance(score, (int, float)) and score >= 0, arguments)

    def test_ok_score_admin_request(self):
        self.start_redis_server()
        arguments = {"phone": "79175002040", "email": "stupnikov@otus.ru"}
        request = {"account": "horns&hoofs", "login": "admin", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        answ = self.get_response(request)
        code = answ.get('code')
        response = answ.get('response')
        error = answ.get('error')
        self.assertEqual(api.OK, code)
        self.assertIsNone(error)
        score = response.get("score")
        self.assertEqual(score, 42)

    @cases([{"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000", "first_name": "a", "last_name": "b"}])
    def test_ok_score_when_used_cache(self, arguments):
        self.start_redis_server()
        # get socore with redis, and it should be cached
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        answ = self.get_response(request)
        code = answ.get('code')
        response = answ.get('response')
        error = answ.get('error')
        self.assertEqual(api.OK, code, arguments)
        self.assertIsNone(error)
        score = response.get("score")
        self.assertTrue(isinstance(score, (int, float)) and score >= 0, arguments)

        # get socore wihout redis, and it should be success
        self.stop_redis_server()
        self.set_valid_auth(request)
        answ = self.get_response(request)
        code = answ.get('code')
        response = answ.get('response')
        error = answ.get('error')
        self.assertEqual(api.OK, code, arguments)
        self.assertIsNone(error)
        score2 = response.get("score")
        self.assertAlmostEqual(score, score2, arguments)

    @cases([{"phone": "79175002040", "email": "test_ok_score_when_noredis_and_nocahe@otus.ru", 
             "gender": 1, "birthday": "01.01.2000", "first_name": "test_ok_score_when_noredis_and_nocahe",
             "last_name": "uniq_for_this_case_to_be_sure_that_is_not_in_cache"}])
    def test_ok_score_when_noredis_and_nocahe(self, arguments):
        self.stop_redis_server()
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        answ = self.get_response(request)
        code = answ.get('code')
        response = answ.get('response')
        error = answ.get('error')
        self.assertEqual(api.OK, code, arguments)
        self.assertIsNone(error)
        score = response.get("score")
        self.assertTrue(isinstance(score, (int, float)) and score >= 0, arguments)

    @cases([
        {},
        {"date": "20.07.2017"},
        {"client_ids": [], "date": "20.07.2017"},
        {"client_ids": {1: 2}, "date": "20.07.2017"},
        {"client_ids": ["1", "2"], "date": "20.07.2017"},
        {"client_ids": [1, 2], "date": "XXX"},
    ])
    def test_invalid_interests_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        answ = self.get_response(request)
        code = answ.get('code')
        response = answ.get('response')
        error = answ.get('error')
        self.assertEqual(api.INVALID_REQUEST, code, arguments)
        self.assertIsNone(response)
        self.assertIsNotNone(error)

    @cases([
        {"client_ids": [1, 2, 3], "date": datetime.datetime.today().strftime("%d.%m.%Y")},
        {"client_ids": [1, 2], "date": "19.07.2017"},
        {"client_ids": [0]},
    ])
    def test_ok_interests_request(self, arguments):
        self.start_redis_server()

        st = store.Store()
        for cid in arguments['client_ids']:
            st.set("i:%s" % cid, str([cid+1, cid+2]) )

        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        answ = self.get_response(request)
        code = answ.get('code')
        response = answ.get('response')
        error = answ.get('error')
        self.assertIsNone(error)
        self.assertEqual(api.OK, code, arguments)
        self.assertEqual(len(arguments["client_ids"]), len(response))
        self.assertTrue(all(v and isinstance(v, list)) and
                        all(len(v) == 2 and v[0] == k+1 and v[1] == k+2) for k, v in response.items())


    @cases([{"client_ids": [1, 2, 3], "date": datetime.datetime.today().strftime("%d.%m.%Y")}])
    def test_fail_interests_request_when_store_fails(self, arguments):
        self.start_redis_server()

        st = store.Store()
        for cid in arguments['client_ids']:
            st.set("i:%s" % cid, str([cid+1, cid+2]) )

        self.stop_redis_server()

        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        answ = self.get_response(request)
        code = answ.get('code')
        response = answ.get('response')
        error = answ.get('error')
        self.assertIsNone(response)
        self.assertIsNotNone(error)
        self.assertEqual(api.INTERNAL_ERROR, code, arguments)


if __name__ == "__main__":
    unittest.main()
