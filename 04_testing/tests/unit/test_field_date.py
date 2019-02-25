import unittest
from server import api
from tests.cases import cases


class TestDateField(unittest.TestCase):

    #  base cases withput null-values and Nones
    valid_values = ['01.01.1980', '14.02.1916', '28.02.2019', '15.03.2045']
    invalid_values = ['00.01.1980', '14.00.1916', '02.28.2019', '2045.15.03',\
                      12122017, [], {}, 12.122017, 1212.2017, 0, b'28.02.2019' ]
    null_values = ['']

    @cases(valid_values + null_values)
    def test_good_valid_when_required_and_nullable(self, content):
        class TestRequest(api.Request):
            f = api.DateField(required=True, nullable=True)
        req = TestRequest({'f': content})
        self.assertTrue(req.is_valid(), msg='with conetent = %s' % content)

    @cases(invalid_values + [None])
    def test_bad_valid_when_required_and_nullable(self, content):
        class TestRequest(api.Request):
            f = api.DateField(required=True, nullable=True)
        req = TestRequest({'f': content})
        self.assertFalse(req.is_valid(), msg='with conetent = %s (type %s)' % (content, type(content)))

    @cases(valid_values + null_values + [None])
    def test_good_valid_when_unrequired_and_nullable(self, content):
        class TestRequest(api.Request):
            f = api.DateField(required=False, nullable=True)
        req = TestRequest({'f': content})
        self.assertTrue(req.is_valid(), msg='with conetent = %s' % content)

    @cases(invalid_values)
    def test_bad_valid_when_unrequired_and_nullable(self, content):
        class TestRequest(api.Request):
            f = api.DateField(required=False, nullable=True)
        req = TestRequest({'f': content})
        self.assertFalse(req.is_valid(), msg='with conetent = %s (type %s)' % (content, type(content)))

    @cases(valid_values)
    def test_good_valid_when_required_and_nonullable(self, content):
        class TestRequest(api.Request):
            f = api.DateField(required=True, nullable=False)
        req = TestRequest({'f': content})
        self.assertTrue(req.is_valid(), msg='with conetent = %s' % content)

    @cases(invalid_values + null_values)
    def test_bad_valid_when_required_and_nonullable(self, content):
        class TestRequest(api.Request):
            f = api.DateField(required=True, nullable=False)
        req = TestRequest({'f': content})
        self.assertFalse(req.is_valid(), msg='with conetent = %s (type %s)' % (content, type(content)))

    @cases(valid_values + [None])
    def test_good_valid_when_unrequired_and_nonullable(self, content):
        class TestRequest(api.Request):
            f = api.DateField(required=False, nullable=False)
        req = TestRequest({'f': content})
        self.assertTrue(req.is_valid(), msg='with conetent = %s' % content)

    @cases(invalid_values + null_values)
    def test_bad_valid_when_unrequired_and_nonullable(self, content):
        class TestRequest(api.Request):
            f = api.DateField(required=False, nullable=False)
        req = TestRequest({'f': content})
        self.assertFalse(req.is_valid(), msg='with conetent = %s (type %s)' % (content, type(content)))


if __name__ == "__main__":
    unittest.main()
