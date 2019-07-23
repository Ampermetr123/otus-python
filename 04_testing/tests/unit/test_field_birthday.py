import unittest
from server import api 
from tests.cases import cases
import datetime


class TestBirthDayField(unittest.TestCase):

    # valid and not empty
    valid_values = ['01.01.1980', '14.02.1950', '28.02.2019', '15.03.2045']
    # invalid values any types and not empty for correct type
    invalid_values = ['00.01.1980', '12.01.1916', '02.28.2019', '2045.15.03',
                      12122017, [], {}, 12.122017, 1212.2017, 0, b'28.02.2019']
    # empty values of correct types
    null_values = ['']
    valid_types = [str]
    invalid_types = [int, dict, tuple, bytearray, bytes, float, list]

    def setUp(self):
        now = datetime.datetime.today()
        old_date = now.replace(year=now.year-70)
        self.invalid_values.append(old_date.strftime("%d.%m.%Y"))
        self.fields = [api.BirthDayField(False, False), api.BirthDayField(False, True),
                       api.BirthDayField(True, False),  api.BirthDayField(True, True)]

    def test_validate_on_correct_content(self):
        for f in self.fields:
            for val in self.valid_values:
                self.assertIsNone(f.validate(val),
                                  msg=" on content %s (type %s)" % (val, type(val)))
        # unreqired fields
        for f in (api.BirthDayField(False, False), api.BirthDayField(False, True)):
            self.assertIsNone(f.validate(None), msg="on None")

        # could be empty fields
        for f in (api.BirthDayField(False, True), api.BirthDayField(True, True)):
            for val in self.null_values:
                self.assertIsNone(f.validate(val), msg="on empty(null) values")

    def test_validate_on_incorrect_content(self):
        for f in self.fields:
            for val in self.invalid_values:
                with self.assertRaises(api.ValidationError,
                                       msg=" on content %s (type %s)" % (val, type(val))):
                    f.validate(val)

        # required fields
        for f in (api.BirthDayField(True, False), api.BirthDayField(True, True)):
            with self.assertRaises(api.ValidationError, msg=" on None"):
                f.validate(None)

        # empty fields
        for f in (api.BirthDayField(False, False), api.BirthDayField(True, False)):
            for val in self.null_values:
                with self.assertRaises(api.ValidationError, msg=" on empty content"):
                    f.validate(val)

    @cases(valid_values)
    def test_check_null_on_nonull_content(self, val):
        for f in self.fields:
            self.assertFalse(f.check_null(val))
        pass

    @cases(null_values)
    def test_chek_null_on_null_content(self, val):
        for f in self.fields:
            self.assertTrue(f.check_null(val))

    @cases(valid_types)
    def test_check_type_on_valid_types(self, t):
        for f in self.fields:
            v = t()
            self.assertIsNone(f.check_type(v), msg=" on type %s" % t)

    @cases(invalid_types)
    def test_check_type_on_invalid_types(self, t):
        for f in self.fields:
            v = t()
            with self.assertRaises(api.ValidationError, msg=" on type %s" % t):
                f.check_type(v)

    @cases(valid_values)
    def test_check_content_on_valid_content(self, val):
        for f in self.fields:
            if type(val) in self.valid_types:
                self.assertIsNone(f.check_content(val),
                                  msg=" on content %s (type %s)" % (val, type(val)))

    @cases(invalid_values)
    def test_check_content_on_invalid_content(self, val):
        for f in self.fields:
            if type(val) in self.valid_types:
                with self.assertRaises(api.ValidationError,
                                       msg=" on content %s (type %s)" % (val, type(val))):
                    f.check_content(val)


if __name__ == "__main__":
    unittest.main()
