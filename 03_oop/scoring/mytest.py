import api

class MyRequestA(api.Request):
    first_name = api.CharField(required=False, nullable=True)
    last_name = api.CharField(required=False, nullable=True)

class MyRequestB(api.Request):
    first_name = api.CharField(required=False, nullable=True)
    last_name = api.CharField(required=False, nullable=True)

if __name__ == '__main__':

    reqA_inst = MyRequestA({'first_name':"A_first", "last_name":"A_last"})
    reqB_inst = MyRequestB({'first_name':"B_first", "last_name":"B_last"})

    print (reqA_inst.first_name, reqA_inst.last_name, reqB_inst.first_name, reqB_inst.last_name)