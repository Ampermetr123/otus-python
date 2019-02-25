import unittest
from server import api
from tests.cases import cases


class TestClientIDsField(unittest.TestCase):

    #  base cases withput null-values and Nones
    valid_values = [[1, 2, 3], [1, 1, 1], [0, -1, -3]]
    invalid_values = [[1, '2', '3'], 123, {}, 1.23, [[1], [1]]]
    null_values = []

    @cases(valid_values + null_values)
    def test_good_valid_when_required_and_nullable(self, content):
        class TestRequest(api.Request):
            f = api.ClientIDsField(required=True, nullable=True) 
        req = TestRequest({'f': content})
        self.assertTrue(req.is_valid(), msg='with conetent = %s' % content)

    @cases(invalid_values + [None])
    def test_bad_valid_when_required_and_nullable(self, content):
        class TestRequest(api.Request):
            f = api.ClientIDsField(required=True, nullable=True) 
        req = TestRequest({'f': content})
        self.assertFalse(req.is_valid(), msg='with conetent = %s (type %s)' % (content, type(content)))

    @cases(valid_values + null_values + [None])
    def test_good_valid_when_unrequired_and_nullable(self, content):
        class TestRequest(api.Request):
            f = api.ClientIDsField(required=False, nullable=True) 
        req = TestRequest({'f': content})
        self.assertTrue(req.is_valid(), msg='with conetent = %s' % content)

    @cases(invalid_values)
    def test_bad_valid_when_unrequired_and_nullable(self, content):
        class TestRequest(api.Request):
            f = api.ClientIDsField(required=False, nullable=True) 
        req = TestRequest({'f': content})
        self.assertFalse(req.is_valid(), msg='with conetent = %s (type %s)' % (content, type(content)))

    @cases(valid_values)
    def test_good_valid_when_required_and_nonullable(self, content):
        class TestRequest(api.Request):
            f = api.ClientIDsField(required=True, nullable=False) 
        req = TestRequest({'f': content})
        self.assertTrue(req.is_valid(), msg='with conetent = %s' % content)

    @cases(invalid_values + null_values)
    def test_bad_valid_when_required_and_nonullable(self, content):
        class TestRequest(api.Request):
            f = api.ClientIDsField(required=True, nullable=False) 
        req = TestRequest({'f': content})
        self.assertFalse(req.is_valid(), msg='with conetent = %s (type %s)' % (content, type(content)))
                    
    @cases(valid_values + [None])
    def test_good_valid_when_unrequired_and_nonullable(self, content):
        class TestRequest(api.Request):
            f = api.ClientIDsField(required=False, nullable=False) 
        req = TestRequest({'f': content})
        self.assertTrue(req.is_valid(), msg='with conetent = %s' % content)

    @cases(invalid_values + null_values)
    def test_bad_valid_when_unrequired_and_nonullable(self, content):
        class TestRequest(api.Request):
            f = api.ClientIDsField(required=False, nullable=False) 
        req = TestRequest({'f': content})
        self.assertFalse(req.is_valid(), msg='with conetent = %s (type %s)' % (content, type(content)))


if __name__ == "__main__":
    unittest.main()
