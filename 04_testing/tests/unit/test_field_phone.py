import unittest
from server import api
from tests.cases import cases


class TestPhoneField(unittest.TestCase):

    # valid and not empty
    valid_values = ['72345678901', '79269161234',
                    '70007000700', '7          ', 72345678901]
    # invalid values any types and not empty for correct type
    invalid_values = ['89260000000', '71212', ' 7-123-45-67',
                     '+79161234567', '+1234567890', 732112, 82345678901,
                     b'72345678901', ['72345678901'], {}, 7.2345678901]
    # empty values of correct types
    null_values = ['']
    valid_types = [str, int]
    invalid_types = [list, tuple, bytearray, bytes, float, dict]

    def setUp(self):
        self.fields = [api.PhoneField(False, False), api.PhoneField(False, True),
                       api.PhoneField(True, False),  api.PhoneField(True, True)]

    def test_validate_on_correct_content(self):
        for f in self.fields:
            for val in self.valid_values:
                self.assertIsNone(f.validate(val),
                                  msg=" on content %s (type %s)" % (val, type(val)))
        # unreqired fields
        for f in (api.PhoneField(False, False), api.PhoneField(False, True)):
            self.assertIsNone(f.validate(None), msg="on None")
        # could be empty fields
        for f in (api.PhoneField(False, True), api.PhoneField(True, True)):
            for val in self.null_values:
                self.assertIsNone(f.validate(val), msg="on empty(null) values")

    def test_validate_on_incorrect_content(self):
        for f in self.fields:
            for val in self.invalid_values:
                with self.assertRaises(api.ValidationError,
                                       msg=" on content %s (type %s)" % (val, type(val))):
                    f.validate(val)
        # required fields
        for f in (api.PhoneField(True, False), api.PhoneField(True, True)):
            with self.assertRaises(api.ValidationError, msg=" on None"):
                f.validate(None)
        # empty fields
        for f in (api.PhoneField(False, False), api.PhoneField(True, False)):
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
