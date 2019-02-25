import json
import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler

# adding this allow to run api like this  >python.exe server/api.py
# this way server module on next lines will be possible to import
import sys
sys.path.insert(0, '')

from server import scoring
from server import store

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


class ValidationError(BaseException):
    pass


class Field:
    """Field descriptor, used in request
       For validated and no-None values creates fields in request instance
       For invalid values creates record in errors dict in request instance 
    """
    def __init__(self, required, nullable):
        self.required = required
        self.nullable = nullable
        self.name = self.__class__.__name__
        self.label = ''

    def __repr__(self):
        return "< %s=%s>" % (self.label, self.name)

    def __set__(self, instance, value):
        """Set and validate. Updates instance __dict__ and errors
        None - values not setted to __dict__"""
        try:
            self.validate(value)
        except ValidationError as err:
            instance.__dict__['errors'][self.label] = str(err)
            instance.__dict__.pop(self.label, None)
        else:
            if value is not None:
                instance.__dict__[self.label] = value
            instance.__dict__['errors'].pop(self.label, None)

    def __get__(self, instance,  value):
        """Returns content if valid or throw AttributeError
           So you can check for not None and valid with hasattr function
        """
        if self.label in instance.__dict__['errors']:
            raise AttributeError(instance.__dict__['errors'][self.label])
        if self.label not in instance.__dict__: 
            raise AttributeError(self.label)
        return instance.__dict__[self.label]

    def validate(self, content):
        """Returns None if content is valid.
        Else throws ValidationError with description how it must be."""
        if content is None:
            if self.required:
                raise ValidationError(self.label + ' is required')
            else:
                return
        self.check_type(content)
        if self.check_null(content):
            if not self.nullable:
                raise ValidationError(self.label + " mustn't be empty")
            return
        return self.check_content(content)

    # functions below should be redefined in subclasses
    def check_null(self, content):
        """Returns true, if content haven't any data"""
        return len(content) == 0

    def check_type(self, content):
        """Returns None if OK. Throw ValidationError  with str how it must be.
         Colled while content is not None"""
        raise NotImplementedError()

    def check_content(self, content):
        """"Returns None if OK. Throw ValidationError  with str how it must be.
        Called while content isn't  None and isn't Null"""
        # any content is OK
        pass


class CharField(Field):
    """Строка"""
    def check_type(self, content):
        if type(content) != str:
            raise ValidationError(self.label + ' must be a string')


class ArgumentsField(Field):
    """Объект в терминах JSON"""
    def check_type(self, content):
        if type(content) != dict:
            raise ValidationError(self.label + ' must be JSON dictionary')
        if len ([x for x in content if type(x) != str]):
            raise ValidationError(self.label + ' JSON dict must have string keys')


class EmailField(Field):
    """Cтрока, в которой есть @"""
    def check_type(self, content):
        if type(content) != str:
            raise ValidationError(self.label + ' must be string')

    def check_content(self, content):
        if '@' not in content:
            raise ValidationError(self.label + ' must contain @')


class PhoneField(Field):
    """Строка или число, длиной 11, начинается с 7"""
    def check_type(self, content):
        if type(content) not in (str, int):
            raise ValidationError(self.label +
                                  ' must be a string or an integer')

    def check_null(self, content):
        return len(str(content)) == 0

    def check_content(self, content):
        if type(content) == int:
            content = str(content)
        if len(content) != 11:
            raise ValidationError(self.label + ' must have 11 symbols')
        if not content.startswith('7'):
            raise ValidationError(self.label + ' must started with "7"')


class DateField(Field):
    """Дата в формате DD.MM.YYYY"""
    def check_type(self, content):
        if type(content) is not str:
            raise ValidationError(self.label +
                                  ' must be a string')

    def check_content(self, content):
        try:
            datetime.datetime.strptime(content, "%d.%m.%Y")
        except ValueError:
            raise ValidationError(self.label + ' must have DD.MM.YYYY format')


class BirthDayField(Field):
    """Дата в формате DD.MM.YYYY, с которой прошло не больше 70 лет"""
    def check_type(self, content):
        if type(content) != str:
            raise ValidationError(self.label + ' must be a string')

    def check_content(self, content):
        try:
            birthday = datetime.datetime.strptime(content, "%d.%m.%Y")
            years_70_ahead = datetime.datetime(birthday.year+70,
                                               birthday.month, birthday.day)
            if years_70_ahead < datetime.datetime.now():
                raise ValidationError(self.label +
                                      ' must be later then 70 years ago')
        except ValueError:
            raise ValidationError(self.label + ' must have DD.MM.YYYY format')


class GenderField(Field):
    "число 0, 1 или 2 (GENDERS.keys())"
    def check_type(self, content):
        if type(content) != int:
            raise ValidationError(self.label + ' must be an integer')

    def check_null(self, content):
        # Если число существует, то оно имеет данные
        return False

    def check_content(self, content):
        if content not in GENDERS.keys():
            raise ValidationError(self.label +
                                  " must be from " + str(GENDERS.keys()))


class ClientIDsField(Field):
    """"массив чисел"""
    def check_type(self, content):
        if type(content) != list:
            raise ValidationError(self.label + ' must be an array of integers')

    def check_content(self, content):
        for client_id in content:
            if type(client_id) != int:
                raise ValidationError(self.label +
                                      ' must be an array of integers')


class _MetaRequest(type):
    """Makes dicts of fields in class, updatea labels in fields"""
    def __init__(Class, classname, supers, classdict):

        # The practice of calling the base-class constructor first in the\
        # derived-class constructor should be followed with metaclasses as well
        super(_MetaRequest, Class).__init__(classname, supers, classdict)
        
        Class.fields = {}
        for name, obj in classdict.items():
            if isinstance(obj, Field):
                obj.label = name
                Class.fields[name] = obj


class Request(metaclass=_MetaRequest):
    def __init__(self, request_dict):
        self.errors = {}
        for field_name in self.fields:
            setattr(self, field_name, request_dict.get(field_name))

    def is_valid(self):
        """Returns True if all fields in class are valid"""
        return len(self.errors) == 0


class ClientsInterestsRequest(Request):
    # Field declaration
    client_ids = ClientIDsField(required=True, nullable=False)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(Request):
    # Field declaration
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def is_valid(self):
        """
        Validates fields and fields combinations

        Returns True if request is valid.
        If combination  of field in request is wrong then 
        sets 'extra_valid_error' string in instance
        """
        self.extra_valid_error = None
        valid = False
        if not super().is_valid():
            return False

        elif hasattr(self, 'phone') and hasattr(self, 'email'):
            if not self.fields['phone'].check_null(self.phone) \
               and not self.fields['email'].check_null(self.email):
                valid = True
        elif hasattr(self, 'first_name') and hasattr(self, 'last_name'):
            if not self.fields['first_name'].check_null(self.first_name) \
               and not self.fields['last_name'].check_null(self.last_name):
                valid = True
        elif hasattr(self, 'gender') and hasattr(self, 'birthday'):
            if not self.fields['gender'].check_null(self.gender) \
               and not self.fields['birthday'].check_null(self.birthday):
                valid = True

        if not valid:
            self.extra_valid_error = "not enough arguments"

        return valid


class MethodRequest(Request):
    # Field declaration
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return getattr(self, 'login') == ADMIN_LOGIN

    @property
    def method_token(self):
        return getattr(self, 'token')

    @property
    def handler(self):
        """Return handler according 'method' field content"""
        return self.handlers.get(getattr(self, 'method'))


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512((datetime.datetime.now().strftime("%Y%m%d%H") +
                                ADMIN_SALT).encode()).hexdigest()
    else:
        digest = hashlib.sha512((request.account +
                                 request.login + SALT).encode()).hexdigest()
    if digest == request.method_token:
        return True
    return False


def onine_score_handler(arguments, **extra):
    ctx = extra['ctx']
    store = extra['store']
    is_admin = extra['is_admin']

    request = OnlineScoreRequest(arguments)  
    # basic validations
    if not request.is_valid():
        response = {'error': ERRORS[INVALID_REQUEST]+': '}
        if request.extra_valid_error:
            response['error'] += request.extra_valid_error+'.'
        elif request.errors:
            response['error'] += '; '.join(request.errors.values())+'.' 
       
        return response, INVALID_REQUEST

    # processing
    ctx['has'] = [x for x in request.fields
                  if hasattr(request, x)
                  and not request.fields[x].check_null(getattr(request, x))]
    if is_admin:
        response = {'score': int(ADMIN_SALT)}
    else:
        args = (getattr(request, x, None) for x in ('phone', 'email',
                'birthday', 'gender', 'first_name', 'last_name'))
        try:
            response = {'score': scoring.get_score(store, *args)}
        except Exception as ex:
            response = {'error': ERRORS[INTERNAL_ERROR]+': '+str(ex) }
            return response, INTERNAL_ERROR
    
    return response, OK


def clients_inerests_handler(arguments, **extra):
    ctx = extra['ctx']
    store = extra['store']
    request = ClientsInterestsRequest(arguments)
    # basic validations
    if not request.is_valid():
        response = {'error': ERRORS[INVALID_REQUEST]+': ' +
                    '; '.join(request.errors.values())+'.'}
        return response, INVALID_REQUEST

    # processing
    ctx['nclients'] = len(request.client_ids)
    response = {}
    try:
        for id in request.client_ids:
            response[id] = scoring.get_interests(store, id)
    except Exception as ex:
        response = {'error': ERRORS[INTERNAL_ERROR]+': '+str(ex) }
        return response, INTERNAL_ERROR

    return response, OK


def method_handler(request, ctx, store):

    method_request = MethodRequest(request.get('body'))

    # basic validation
    if not method_request.is_valid():
        code = INVALID_REQUEST
        response = {'error': ERRORS[INVALID_REQUEST]+': ' +
                    '; '.join(method_request.errors.values())+'.'}
        return response, code

    # Checking auth
    if check_auth(method_request) is False:
        return {'error': ERRORS[FORBIDDEN]}, FORBIDDEN

    if method_request.method == 'online_score':
        response, code = onine_score_handler(method_request.arguments,
                                             ctx=ctx, store=store,
                                             is_admin=method_request.is_admin)
    elif method_request.method == 'clients_interests':
        response, code = clients_inerests_handler(method_request.arguments,
                                                  ctx=ctx, store=store,
                                                  is_admin=method_request.is_admin) 
    else:
        response, code = {'errors': 'Method not supported ' +
                          method_request.method}, INVALID_REQUEST

    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = store.Store()

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except Exception as ex:
            logging.info(str(ex))
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, 
                                                       context, self.store)
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
        
        logging.info("r="+str(r))

        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode())
        return


if __name__ == "__main__":

    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8082)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        logging.info("Server stopped %s" % opts.port)
        logging.shutdown()
        sys.exit(0)
