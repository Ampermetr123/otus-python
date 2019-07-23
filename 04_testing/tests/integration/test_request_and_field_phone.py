import unittest
from server import api
from tests.cases import cases


class TestPhoneFieldInRequest(unittest.TestCase):

    #  base cases withput null-values and Nones
    valid_values = ['72345678901', '79269161234', '70007000700', '7          ', 72345678901]
    invalid_values = ['89260000000', '71212', ' 7-123-45-67',
                      '+79161234567', '+1234567890', 732112, 82345678901,
                      b'72345678901', ['72345678901'], {}, 7.2345678901]
    null_values = ['']

    @cases(valid_values + null_values)
    def test_good_valid_when_required_and_nullable(self, content):
        class TestRequest(api.Request):
            f = api.PhoneField(required=True, nullable=True) 
        req = TestRequest({'f': content})
        self.assertTrue(req.is_valid(), msg='with conetent = %s' % content)

    @cases(invalid_values + [None])
    def test_bad_valid_when_required_and_nullable(self, content):
        class TestRequest(api.Request):
            f = api.PhoneField(required=True, nullable=True) 
        req = TestRequest({'f': content})
        self.assertFalse(req.is_valid(), msg='with conetent = %s (type %s)' % (content, type(content)))

    @cases(valid_values + null_values + [None])
    def test_good_valid_when_unrequired_and_nullable(self, content):
        class TestRequest(api.Request):
            f = api.PhoneField(required=False, nullable=True) 
        req = TestRequest({'f': content})
        self.assertTrue(req.is_valid(), msg='with conetent = %s' % content)

    @cases(invalid_values)
    def test_bad_valid_when_unrequired_and_nullable(self, content):
        class TestRequest(api.Request):
            f = api.PhoneField(required=False, nullable=True) 
        req = TestRequest({'f': content})
        self.assertFalse(req.is_valid(), msg='with conetent = %s (type %s)' % (content, type(content)))

    @cases(valid_values)
    def test_good_valid_when_required_and_nonullable(self, content):
        class TestRequest(api.Request):
            f = api.PhoneField(required=True, nullable=False) 
        req = TestRequest({'f': content})
        self.assertTrue(req.is_valid(), msg='with conetent = %s' % content)

    @cases(invalid_values + null_values)
    def test_bad_valid_when_required_and_nonullable(self, content):
        class TestRequest(api.Request):
            f = api.PhoneField(required=True, nullable=False) 
        req = TestRequest({'f': content})
        self.assertFalse(req.is_valid(), msg='with conetent = %s (type %s)' % (content, type(content)))

    @cases(valid_values + [None])
    def test_good_valid_when_unrequired_and_nonullable(self, content):
        class TestRequest(api.Request):
            f = api.PhoneField(required=False, nullable=False) 
        req = TestRequest({'f': content})
        self.assertTrue(req.is_valid(), msg='with conetent = %s' % content)

    @cases(invalid_values + null_values)
    def test_bad_valid_when_unrequired_and_nonullable(self, content):
        class TestRequest(api.Request):
            f = api.PhoneField(required=False, nullable=False) 
        req = TestRequest({'f': content})
        self.assertFalse(req.is_valid(), msg='with conetent = %s (type %s)' % (content, type(content)))


if __name__ == "__main__":
    unittest.main()
