#!/usr/bin/env python

import json
import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler
import scoring

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


# ------------ Fields ------------

class Field:
    """Field, used in request"""
    def __init__(self, required, nullable):
        self.required = required
        self.nullable = nullable
        self.name = self.__class__.__name__
    
    def __repr__(self):
        return "<Field: name: %s" % self.name

    def is_null(self, content):
        """Returns true, if content haven't any data"""
        return len(content) == 0
    
    def check_type(self, content):
        """Returns None if OK, or str with how it must be. Content is not None"""
        pass
    
    def check_content(self, content):
        """"Returns None if OK, or str with how it must be. Content isn't  None and isn't Null"""
        pass

    def validate(self, content):
        """Returns None if OK, or str with how it must be"""
        if content is None:
            return  'is required' if self.required else None
        
        type_check_result = self.check_type(content)
        if type_check_result is not None:
            return type_check_result

        if self.is_null(content):
            return None if self.nullable else 'mustnt\'t be empty'
        return self.check_content(content)


class CharField(Field):
    """Cтрока"""
    def check_type(self, content):
        if type(content) != str:
            return 'must be a string'


class ArgumentsField(Field):
    """Объект в терминах JSON"""
    def check_type(self, content):
        if type(content) != dict:
            return 'must be dictionary'


class EmailField(Field):
    """Cтрока, в которой есть @"""
    def check_type(self, content):
        if type(content) != str:
            return 'must be string'
    
    def check_content(self, contnet):
        if not '@' in contnet:
            return "must contain '@'" 


class PhoneField(Field):
    """Cтрока или число, длиной 11, начинается с 7"""
    def check_type(self, content):
        if type(content) not in (str, int):
            return 'must be a string or an integer'
    
    def is_null(self, content):
        return len(str(content)) == 0

    def check_content(self, content):
        if type(content)==int:
            content=str(content)
        if len(content)!=11:
            return 'must have 11 symbols'
        if not content.startswith('7'):
            return 'must started with "7"'


class DateField(Field):
    """Дата в формате DD.MM.YYYY"""
    def check_type(self, content):
        if type(content) not in (str, int):
            return 'must be a string or an integer'

    def check_content(self, content):
        try:
            datetime.datetime.strptime(content, "%d.%m.%Y")
        except ValueError:
            return 'must have DD.MM.YYYY format'


class BirthDayField(Field):
    """Дата в формате DD.MM.YYYY, с которой прошло не больше 70 лет, опционально, может быть пустым"""
    def check_type(self, content):
        if type(content) !=  str:
            return 'must be a stringr'

    def check_content(self, content):
        try:
            birthday = datetime.datetime.strptime(content, "%d.%m.%Y")
            years_70_ahead = datetime.datetime(birthday.year+70,birthday.month,birthday.day)
            if years_70_ahead < datetime.datetime.now():
                return 'must be later then 70 years ago'
        except ValueError:
            return 'must have DD.MM.YYYY format'


class GenderField(Field):
    "число 0, 1 или 2 (GENDERS.keys())" 
    def check_type(self, content):
        if type(content) != int:
            return 'must be an integer'

    def is_null(self, content):
        # Если число существует, то оно имеет данные
        return False

    def check_content(self, content):
        if content not in GENDERS.keys():
            return "must be from "+str(GENDERS.keys())


class ClientIDsField(Field):
    """"массив чисел"""
    def check_type(self, content):
        if type(content) != list:
            return 'must be an array of integers'
    
    def check_content(self, content):
        for client_id in content:
            if type(client_id) != int:
                return 'must be an array of integers'


# ------------ Requests handlers ------------

class Request:
    """Request base class"""
    def validate_fields(self, request_dict):
        """"Validating all Field's objects of class scope """
        code = OK
        response = {}
        for field_name, obj in self.__class__.__dict__.items():
            if isinstance(obj, Field):
                invalid_msg = obj.validate(request_dict.get(field_name))
                if invalid_msg:
                    if code == OK:
                        response['error'] = ERRORS[INVALID_REQUEST] + ': \'' + field_name + "\' - " + invalid_msg
                        code = INVALID_REQUEST
                    else:
                        response['error'] += ';  ' + field_name + " - " + invalid_msg
        return response, code
    
    def check_fields_actual(self, request_dict, field_names):
        """"Returns True if all specified fields are present in request_dict, not null and validated"""
        for name in field_names:
            fclass = self.__class__.__dict__[name].__class__
            fdata = request_dict.get(name)
            if fclass(True, False).validate(fdata) is not None:
                return False
        return True

    def handle(self, request_dict, *extra):
        """handle request : validating and processing. """
        raise NotImplementedError('Handle method not implemented')


class ClientsInterestsRequest(Request):
    """ clients_interests method request """

    # fields in arguments
    client_ids = ClientIDsField(required=True, nullable=False)
    date = DateField(required=False, nullable=True)
    
    def handle(self, request_dict, *extra):
        ctx = extra[1]
        store = extra[2]

        # fields validations
        response, code = self.validate_fields(request_dict)

        if code == OK:
            ctx['nclients'] = len(request_dict['client_ids'])
            for id in request_dict['client_ids']:
                response[id] = scoring.get_interests(store, id)

        return response, code


class OnlineScoreRequest(Request):
    """ online_score method request """

    # fields in arguments
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def handle(self, request_dict, *extra):
        admin_role= extra[0] is True
        ctx=extra[1]
        store=extra[2]

        # basic validations
        response, code = self.validate_fields(request_dict)

        # extra validation
        if code == OK:
            if not self.check_fields_actual(request_dict, ('phone','email')) and \
            not self.check_fields_actual(request_dict,('first_name','last_name')) and \
            not self.check_fields_actual(request_dict,('gender','birthday')):
                return {'error': "not enough arguments for 'online_score' method"}, INVALID_REQUEST
        
        # processing
        if code == OK:
            scoring_params = ('phone', 'email', 'birthday', 'gender', 'first_name', 'last_name')
            ctx['has'] = [x for x in scoring_params if self.check_fields_actual(request_dict, (x,))]

            if admin_role:
                response = {'score': int(ADMIN_SALT)}
            else:
                args = (request_dict.get(x) for x in scoring_params)
                response = {'score': scoring.get_score(store, *args)}

        return response, code


class MethodRequest(Request):

    # Fields of Method Requests
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    # Methods, that could be asked in Request
    online_score = OnlineScoreRequest()
    clients_interests = ClientsInterestsRequest()

    def __init__(self, request, ctx, store):
        self.request_dict = request.get('body')
        self.ctx = ctx
        self.store = store
        self.login = self.request_dict.get('login', '')
        self.account = self.request_dict.get('account', '')
         
    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN

    @property
    def method_token(self):
        return self.request_dict.get('token')

    def handle(self):
        # Checking request fields
        (response, code) = super().validate_fields(self.request_dict)
        if code != OK:
            return response, code
        
        # Checking auth
        if check_auth(self) is False:
            return {'error': ERRORS[FORBIDDEN]}, FORBIDDEN
        
        # Checking fields for specific method request
        for method_name, obj in self.__class__.__dict__.items():
            if isinstance(obj, Request) and method_name == self.request_dict.get('method'):
                (response, code) = obj.handle(self.request_dict.get('arguments'), self.is_admin, self.ctx, self.store)

        return response, code


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512((datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode()).hexdigest()
    else:
        digest = hashlib.sha512((request.account + request.login + SALT).encode()).hexdigest()
    if digest == request.method_token:
        return True
    return False


def method_handler(request, ctx, store):
    mr = MethodRequest(request, ctx, store)
    responce, code = mr.handle()
    return responce, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r))
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
