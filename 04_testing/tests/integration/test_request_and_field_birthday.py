import unittest
from server import api 
from tests.cases import cases
import datetime


class TestBirthdayFieldInRequest(unittest.TestCase):
    #  base cases withput null-values and Nones
    valid_values = ['01.01.1980', '14.02.1950', '28.02.2019', '15.03.2045']
    invalid_values = ['00.01.1980', '12.01.1916', '02.28.2019', '2045.15.03',
                      12122017, [], {}, 12.122017, 1212.2017, 0, b'28.02.2019']
    null_values = ['']

    def setUp(self):
        now = datetime.datetime.today()
        old_date = now.replace(year=now.year-70)
        self.invalid_values.append(old_date.strftime("%d.%m.%Y"))

    @cases(valid_values + null_values)
    def test_good_valid_when_required_and_nullable(self, content):
        class TestRequest(api.Request):
            f = api.BirthDayField(required=True, nullable=True) 
        req = TestRequest({'f': content})
        self.assertTrue(req.is_valid(), msg='with conetent = %s' % content)

    @cases(invalid_values + [None])
    def test_bad_valid_when_required_and_nullable(self, content):
        class TestRequest(api.Request):
            f = api.BirthDayField(required=True, nullable=True) 
        req = TestRequest({'f': content})
        self.assertFalse(req.is_valid(), msg='with conetent = %s (type %s)' % (content, type(content) ))

    @cases(valid_values + null_values + [None])
    def test_good_valid_when_unrequired_and_nullable(self, content):
        class TestRequest(api.Request):
            f = api.BirthDayField(required=False, nullable=True) 
        req = TestRequest({'f': content})
        self.assertTrue(req.is_valid(), msg='with conetent = %s' % content)

    @cases(invalid_values)
    def test_bad_valid_when_unrequired_and_nullable(self, content):
        class TestRequest(api.Request):
            f = api.BirthDayField(required=False, nullable=True) 
        req = TestRequest({'f': content})
        self.assertFalse(req.is_valid(), msg='with conetent = %s (type %s)' % (content, type(content)))

    @cases(valid_values)
    def test_good_valid_when_required_and_nonullable(self, content):
        class TestRequest(api.Request):
            f = api.BirthDayField(required=True, nullable=False) 
        req = TestRequest({'f': content})
        self.assertTrue(req.is_valid(), msg= 'with conetent = %s' % content)

    @cases(invalid_values + null_values)
    def test_bad_valid_when_required_and_nonullable(self, content):
        class TestRequest(api.Request):
            f = api.BirthDayField(required=True, nullable=False) 
        req = TestRequest({'f': content})
        self.assertFalse(req.is_valid(), msg='with conetent = %s (type %s)' % (content, type(content)))

    @cases(valid_values + [None])
    def test_good_valid_when_unrequired_and_nonullable(self, content):
        class TestRequest(api.Request):
            f = api.BirthDayField(required=False, nullable=False) 
        req = TestRequest({'f': content})
        self.assertTrue(req.is_valid(), msg='with conetent = %s' % content)

    @cases(invalid_values + null_values)
    def test_bad_valid_when_unrequired_and_nonullable(self, content):
        class TestRequest(api.Request):
            f = api.BirthDayField(required=False, nullable=False) 
        req = TestRequest({'f': content})
        self.assertFalse(req.is_valid(), msg= 'with conetent = %s (type %s)' % (content, type(content)))


if __name__ == "__main__":
    unittest.main()
