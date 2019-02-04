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


class ValidationError(BaseException):
    pass


class Field:
    """Field, used in request"""
    def __init__(self, required, nullable):
        self.required = required
        self.nullable = nullable
        self.name = self.__class__.__name__
        self.label = ''
        self.content = None
        self.validationResult = False
        try:
            self.validate(self.content)
        except ValidationError:
            pass

    def __repr__(self):
        return "< %s=%s(%s,%s) >" \
            % (self.label, self.name, self.content, self.validationResult)

    def __set__(self, instance, value):
        """Sets content and validate. No throws exception"""
        self.content = value
        try:
            self.validate(value)
        except ValidationError as err:
            instance.errors[self.label] = str(err)
            self.validationResult = False
        else:
            instance.errors.pop(self.label, None)
            self.validationResult = True

    def __get__(self, instance,  value):
        """Returns content if valid or throw ValidationError"""
        if self.validationResult is False:
            # repeat validation to raise Error with description again
            self.validate(self.content)
        return self.content

    def is_valuable(self):
        """Return True of content is valid and contains data"""
        return self.validationResult \
            and self.content is not None \
            and not self.check_null(self.content)

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
                raise ValidationError(self.label + ' mustnt\'t be empty')
        return self.check_content(content)

    # functions below should be refefined in subclasses
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
    """Cтрока"""
    def check_type(self, content):
        if type(content) != str:
            raise ValidationError(self.label + ' must be a string')


class ArgumentsField(Field):
    """Объект в терминах JSON"""
    def check_type(self, content):
        if type(content) != dict:
            raise ValidationError(self.label + ' must be dictionary')


class EmailField(Field):
    """Cтрока, в которой есть @"""
    def check_type(self, content):
        if type(content) != str:
            raise ValidationError(self.label + ' must be string')

    def check_content(self, content):
        if '@' not in content:
            raise ValidationError(self.label + ' must contain @')


class PhoneField(Field):
    """Cтрока или число, длиной 11, начинается с 7"""
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
        if type(content) not in (str, int):
            raise ValidationError(self.label +
                                  ' must be a string or an integer')

    def check_content(self, content):
        try:
            datetime.datetime.strptime(content, "%d.%m.%Y")
        except ValueError:
            raise ValidationError(self.label + ' must have DD.MM.YYYY format')


class BirthDayField(Field):
    """Дата в формате DD.MM.YYYY, с которой прошло не больше 70 лет"""
    def check_type(self, content):
        if type(content) != str:
            raise ValidationError(self.label + ' must be a stringr')

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
        Class.fields = {}
        for name, obj in classdict.items():
            if isinstance(obj, Field):
                obj.label = name
                Class.fields[name] = obj


class _MetaHandler(_MetaRequest):
    """Makes dict of handlrers in class"""
    def __init__(Class, classname, supers, classdict):
        Class.handlers = {}
        for name, obj in classdict.items():
            if isinstance(obj, MethodHandler):
                obj.label = name
                Class.handlers[name] = obj
        super().__init__(classname, supers, classdict)


class MethodHandler():
    """Base class for Request Handlers"""
    pass


class OnlineScoreRequestHandler(MethodHandler):
    def handle(self, arguments, **extra):
        ctx = extra['ctx']
        store = extra['store']
        is_admin = extra['is_admin']

        # basic validation
        request = OnlineScoreRequest(arguments)
        if not request.is_valid():
            code = INVALID_REQUEST
            response = {'error': ERRORS[INVALID_REQUEST] +
                        ': '+'; '.join(request.errors.values())+'.'}
            return response, code

        # extra validation
        if not request.are_fields_valuable(('phone', 'email')) and \
           not request.are_fields_valuable(('first_name', 'last_name')) and \
           not request.are_fields_valuable(('gender', 'birthday')):
            code = INVALID_REQUEST
            response = {'error': ERRORS[INVALID_REQUEST] +
                        ': ' "not enough arguments for 'online_score' method"}
            return response, code

        # processing
        ctx['has'] = [x for x in request.fields
                      if request.fields[x].is_valuable()]
        if is_admin:
            response = {'score': int(ADMIN_SALT)}
        else:
            args = (getattr(request, x) for x in ('phone', 'email',
                    'birthday', 'gender', 'first_name', 'last_name'))
            response = {'score': scoring.get_score(store, *args)}
        return response, OK


class ClientsInterestsRequestHandler(MethodHandler):
    # Field decloration
    def handle(self, arguments, **extra):
        ctx = extra['ctx']
        store = extra['store']
        request = ClientsInterestsRequest(arguments)
        # basic validations
        if not request.is_valid():
            code = INVALID_REQUEST
            response = {'error': ERRORS[INVALID_REQUEST]+': ' +
                        '; '.join(request.errors.values())+'.'}
            return response, code

        # processing
        ctx['nclients'] = len(request.client_ids)
        response = {}
        code = OK
        for id in request.client_ids:
            response[id] = scoring.get_interests(store, id)
        return response, code


class Request(MethodHandler, metaclass=_MetaRequest):
    def __init__(self, request_dict):
        self.errors = {}
        for field_name in self.fields:
            setattr(self, field_name, request_dict.get(field_name))

    def is_valid(self):
        """Returns True if all fields in class are valid"""
        return len(self.errors) == 0

    def are_fields_valuable(self, field_names):
        """"Returns True if all fields are present, not null and validated"""
        for fname in field_names:
            if not self.fields[fname].is_valuable():
                return False
        return True


class ClientsInterestsRequest(Request):
    # Field decloration
    client_ids = ClientIDsField(required=True, nullable=False)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(Request):
    # Field decloration
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)


class MethodRequest(Request, metaclass=_MetaHandler):
    # Field decloration
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    # Methods declaration, that could be asked in Request.method
    online_score = OnlineScoreRequestHandler()
    clients_interests = ClientsInterestsRequestHandler()

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


def method_handler(request, ctx, store):
    method_request = MethodRequest(request.get('body'))
    if not method_request.is_valid():
        code = INVALID_REQUEST
        response = {'error': ERRORS[INVALID_REQUEST]+': ' +
                    '; '.join(method_request.errors.values())+'.'}
        return response, code

    # Checking auth
    if check_auth(method_request) is False:
        return {'error': ERRORS[FORBIDDEN]}, FORBIDDEN

    if method_request.handler is None:
        # return OK according hometask,
        # thought it might not be well for unknown method
        return OK, {}
    admin_role = method_request.is_admin
    response, code = method_request.handler.handle(method_request.arguments,
                                                   ctx=ctx, store=store,
                                                   is_admin=admin_role)
    return response, code


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
