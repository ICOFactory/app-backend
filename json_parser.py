from database import Database
import unittest
import uuid


def errorCodeObj(errorCode, errorMessage):
            if errorCode:
                return {"success": False, "errorCode": errorCode, "error": errorMessage}
            return {"success": False, "error": errorMessage}


class APIAction:
    AUTH_LEVEL_ALL = 0
    AUTH_LEVEL_MEMBER = 1
    AUTH_LEVEL_ADMIN = 2

    def __init__(self, name, required_arguments, auth_level):
        self.name = name
        self.required_arguments = required_arguments
        self.auth_level = auth_level

    def all_required_arguments(self, args):
        required_args = list(self.required_arguments)
        # all actions require a name and session id
        required_args.append("action")
        required_args.append("session_id")
        found = True
        for each in args:
            if each not in required_args:
                found = False
                break
        return found

    def requires_login(self):
        if self.auth_level > 0:
            return True
        return False

    def requires_admin(self):
        if self.auth_level > 1:
            return True
        return False


class JSONProcessor:
    ERROR_VIEWING_WALLET =17
    ERROR_INVALID_SESSION = 4,"Invalid session"
    ERROR_REQUIRED_ARGUMENTS_NOT_FOUND = 5,"Required arguments not found."

    def __init__(self, jsonData,request_data=None):
        self.error = None
        self.response = None
        self.db = Database()
        self.logger = None
        if type(jsonData) is dict:
            if 'action' in jsonData:
                action = jsonData['action']
                if action == "login":
                    if 'email_address' in jsonData and 'password' in jsonData:
                        self.login(jsonData['email_address'],jsonData['password'], request_data['ip_address'])
                    else:
                        self.error = errorCodeObj(5,"Required arguments not found.")
                elif action == "create_user":
                    required_args = ["email_address",
                                     "password",
                                     "full_name",
                                     "action"]
                    not_found = False
                    for each in jsonData.keys():
                        if each not in required_args:
                            not_found = True
                            break

                    if not not_found:
                        self.create_user(jsonData['full_name'],jsonData['email_address'],jsonData['password'], request_data['ip_address'])
                    else:
                        self.error = errorCodeObj(5,"Required arguments not found.")
                elif action == "add_device":
                    if 'session_id' in jsonData and 'user_id' in jsonData:
                        valid_session = self.db.verify_session(jsonData['user_id'],jsonData['session_id'])
                        if valid_session:
                            if 'user_id' in jsonData and 'uuid' in jsonData:
                               self.add_device(jsonData['user_id'],jsonData['uuid'])
                            else:
                                self.error = errorCodeObj(5,"Required arguments not found.")
                        else:
                            self.error = errorCodeObj(4,"Invalid session")
                    else:
                        self.error = errorCodeObj(5,"Required arguments not found.")
                elif action == "list_devices":
                    if 'user_id' in jsonData and 'session_id' in jsonData:
                        valid_session = self.db.verify_session(jsonData['user_id'],jsonData['session_id'])
                        if valid_session:
                            response = self.db.list_devices(jsonData['user_id'])
                            if type(response) is list:
                                self.response = {"success":True,"devices":response}
                            else:
                                self.error = errorCodeObj(300,"Unknown error retrieving device list for user id: {0}".format(jsonData['userId']))
                        else:
                            self.error = errorCodeObj(4,"Invalid session")
                    else:
                        self.error = errorCodeObj(5,"Required arguments not found.")
                elif action == "frame_count":
                    if 'device_id' in jsonData and 'session_id' in jsonData and 'user_id' in jsonData:
                        valid_session = self.db.verify_session(jsonData['user_id'],jsonData['session_id'])
                        if valid_session:
                            frame_count(jsonData['device_id'])
                        else:
                            self.error = errorCodeObj(4,"Invalid session")
                    else:
                        self.error = errorCodeObj(5,"Required arguments not found.")
                elif action == "last_frame":
                    if 'device_id' in jsonData and 'session_id' in jsonData and 'user_id' in jsonData:
                        valid_session = self.db.verify_session(jsonData['user_id'],jsonData['session_id'])
                        if valid_session:
                            self.last_frame(jsonData['device_id'])
                        else:
                            self.error = errorCodeObj(4,"Invalid session")
                    else:
                        self.error = errorCodeObj(5,"Required arguments not found.")
                elif action == "post_command":
                    if 'device_id' in jsonData and 'session_id' in jsonData and 'user_id' in jsonData and 'command' in jsonData:
                        valid_session = self.db.verify_session(jsonData['user_id'],jsonData['session_id'])
                        if valid_session:
                            self.post_command(jsonData['user_id'],jsonData['command'])
                        else:
                            self.error = errorCodeObj(4,"Invalid session")
                    else:
                        self.error = errorCodeObj(5,"Required arguments not found.")
                elif action == "view_wallet":
                    validator = APIAction("view_wallet",["user_id"],APIAction.AUTH_LEVEL_MEMBER)
                    if validator.all_required_arguments(jsonData.keys()):
                        if validator.requires_login():
                            if self.db.verify_session(jsonData['user_id'],jsonData['session_id']):
                               self.view_wallet(jsonData['user_id'])
                            else:
                                self.fail(("Not logged in",self.ERROR_INVALID_SESSION))
                    else:
                        self.error = errorCodeObj(5,"Required arguments not found.")
                else:
                    self.error = errorCodeObj(300,"Unknown action.")
            else:
                self.fail(("Required arguments not found",self.ERROR_REQUIRED_ARGUMENTS_NOT_FOUND))
        else:
            self.error = {"success":False,"errorCode":1,"error":"Invalid JSON request object."}

    def fail(self,error_tuple):
        self.error = {"success":False,"errorCode":error_tuple[0],"error":error_tuple[1]}

    def view_wallet(self,user_id):
        self.db.logger = self.logger
        owned_tokens = self.db.view_wallet(user_id)
        if owned_tokens:
            self.response = {"success":True,
                            "owned_tokens":owned_tokens}
        else:
            self.fail(self.ERROR_VIEWING_WALLET,"Error viewing wallet")

    def create_user(self,full_name,username,password,ip_address):
        self.db.logger = self.logger
        response = self.db.create_user(full_name,username,password,ip_address)
        if response:
            user_id = response[0]
            if user_id > 0:
                self.db.add_device(user_id, str(uuid.uuid4()))
                devices = self.db.list_devices(user_id)
                user_info = self.db.get_user_info(user_id)
                user_info["last_logged_in"] = user_info["last_logged_in"].isoformat()
                user_info["created"] = user_info["created"].isoformat()
                default_device = None
                if len(devices) > 0:
                    default_device = devices[0]
                self.response = {"success": True,
                                 "user_id": user_id,
                                 "session_id": response[1],
                                 "user_info": user_info,
                                 "default_device": default_device}
            else:
                self.error = errorCodeObj(response[0],response[1]) # bubble up error from db layer
        else:
            self.error = (-200,"DB: Could not create user")

    def login(self,username,password,ip_address):
        self.db.logger = self.logger
        response = self.db.login(username,password,ip_address)
        if response:
            user_id = response[0]
            devices = self.db.list_devices(user_id)
            default_device = None
            if len(devices) > 0:
                default_device = devices[0]
            self.response = dict(success=True,
                                 session_id=response[1],
                                 user_id=user_id,
                                 default_device=default_device)
        else:
            self.error = errorCodeObj(-155,"Invalid username/password")

    def add_device(self,user_id,uuid):
        self.db.logger = self.logger
        result = self.db.add_device(user_id,uuid)
        if result < 0:
            if result == -3:
                self.error = errorCodeObj(-3,"devices table db issue")
            elif result == -2:
                self.error = errorCodeObj(-2,"UUID doesn't match regex")
        else:
            self.response = {"success":True,"device_id":result}

    def list_devices(self,user_id):
        self.db.logger = self.logger
        result = self.db.list_devices(user_id)
        if result:
            self.response = {"success":True,"devices":result}
        else:
            self.error = errorCodeObj(-4,"Error table devices list_devices")

    def add_frame(self,device_id,json_string):
        self.db.logger = self.logger
        result = 1
        if result > 0:
            self.response = {"success":True,"device_id":device_id,"frame_id":result}
        else:
            self.error = errorCodeObj(-5,"Error adding frame to database")

    def frame_count(self,device_id):
        self.db.logger = self.logger
        count = 0
        response = self.db.frame_count(device_id)
        self.response = {"success":True,"frame_count":count}

    def last_frame(self,device_id):
        self.db.logger = self.logger
        frame = self.db.last_frame(device_id)
        if frame:
            self.response = {"success":True,"frame_id":frame[0],"created":frame[1].isoformat(),"json_string":frame[2]}
        else:
            self.error = errorCodeObj(100,"Couldn't retrieve last frame for device_id: {0}".format(device_id))

    def post_command(self,device_id,command_data):
        response = self.db.post_command(device_id,command_data)
        if response > 0:
            self.response = {"success":True,"command_id":response}
        else:
            self.error = errorCodeObj(105,"Could not post command to queue for device id: {0}".format(device_id))

    def get_frame(self,device_id,offset):
        frame = self.db.get_frame(device_id,offset)
        if frame:
            self.response = {"success":True,"frame_id":frame[0],"created":frame[1],"json_string":frame[2]}
        else:
            self.error = errorCodeObj(101,"Couldn't retrieve last frame for device_id: {0} at offset: {1}".format(device_id,offset))


class ProcessUnitTests(unittest.TestCase):
    def test_login(self):
        testData = {"action":"login","username":"john_hill","password":"esposito"}
        jp = JSONProcessor(testData)
        self.assertIsNotNone(jp.response)
        self.assertIsNone(jp.error)
        testData['username'] = "test_fail"
        jp = JSONProcessor(testData)
        self.assertIsNone(jp.response)
        self.assertIsNotNone(jp.error)

    def test_add_device(self):
        testData = {"action":"add_device","session_id":"test","user_id":1,"uuid":"test"}
        jp = JSONProcessor(testData)
        self.assertIsNotNone(jp.response)
        self.assertIsNone(jp.error)
        testData['user_id'] = -1
        # test invalid session
        jp = JSONProcessor(testData)
        self.assertIsNone(jp.response)
        self.assertIsNotNone(jp.error)

    def test_list_devices(self):
        testData = {"action":"list_devices","session_id":"test","user_id":1}
        jp = JSONProcessor(testData)
        self.assertIsNotNone(jp.response)
        self.assertIsNone(jp.error)
        self.assertEqual(jp.response['success'],True)

    def test_last_frame(self):
        testData = {"action":"last_frame","user_id":1,"session_id":"test","device_id":1}
        jp = JSONProcessor(testData)
        self.assertIsNotNone(jp.response)
        self.assertIsNone(jp.error)
        self.assertEqual(jp.response['success'],True)


if __name__ == "__main__":
    unittest.main()
