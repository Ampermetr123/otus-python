import api

class MyRequestA(api.Request):
    first_name = api.CharField(required=False, nullable=True)
    last_name = api.CharField(required=False, nullable=True)

class MyRequestB(api.Request):
    first_name = api.CharField(required=False, nullable=True)
    last_name = api.CharField(required=False, nullable=True)

class SomeClass():
    field_1= api.CharField(required=False, nullable=True)
    field_2= api.CharField(required=True, nullable=True)

if __name__ == '__main__':

    reqA_inst = MyRequestA({'first_name':"A_first", "last_name":"A_last"})
    reqB_inst = MyRequestB({'first_name':"B_first", "last_name":"B_last"})
    print (reqA_inst.first_name, reqA_inst.last_name, reqB_inst.first_name, reqB_inst.last_name)

    try:
        someclass_inst = SomeClass()
        print(someclass_inst.field_1) 
        print(someclass_inst.field_2) 
    except api.ValidationError as err:
        print(str(err))
      