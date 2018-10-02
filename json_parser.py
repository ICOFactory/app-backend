from database import Database
import unittest


def errorCodeObj(errorCode, errorMessage):
            if errorCode:
                return {"success": False, "errorCode": errorCode, "error": errorMessage}
            return {"success": False, "error": errorMessage}


class JSONProcessor():
    def __init__(self, jsonData):
        self.error = None
        self.response = None
        self.db = Database()
        if type(jsonData) is dict:
            if 'action' in jsonData:
                action = jsonData['action']
                if action == "login":
                    if 'username' in jsonData and 'password' in jsonData:
                        self.login(jsonData['username'],jsonData['password'])
                    else:
                        self.error = errorCodeObj(5,"Required arguments not found.")
                elif action == "create_user":
                    if 'username' in jsonData and 'password' in jsonData:
                        self.create_user(jsonData['username'],jsonData['password'])
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
                else:
                    self.error = errorCodeObj("Unknown action.")
            else:
                self.error = errorCodeObj(2,"Action not found")
        else:
            self.error = {"success":False,"errorCode":1,"error":"Invalid JSON request object."}

    def create_user(self,username,password):
        response = self.db.create_user(username,password)
        if response:
            if response[0] > 0:
                self.response = {"success":True,"user_id":response[0],"session_id":response[1]}
            else:
                self.error = errorCodeObj(response[0],response[1]) # bubble up error from db layer
        else:
            self.error = (-200,"DB: Could not create user")

    def login(self,username,password):
        response = self.db.login(username,password)
        if response:
            self.response = {"success":True,"session_id":response[1],"user_id":response[0]}
        else:
            self.error = errorCodeObj(-155,"Invalid username/password")

    def add_device(self,user_id,uuid):
        result = self.db.add_device(user_id,uuid)
        if result < 0:
            if result == -3:
                self.error = errorCodeObj(-3,"devices table db issue")
            elif result == -2:
                self.error = errorCodeObj(-2,"UUID doesn't match regex")
        else:
            self.response = {"success":True,"device_id":result}

    def list_devices(self,user_id):
        result = self.db.list_devices(user_id)
        if result:
            self.response = {"success":True,"devices":result}
        else:
            self.error = errorCodeObj(-4,"Error table devices list_devices")

    def add_frame(self,device_id,json_string):
        result = 1
        if result > 0:
            self.response = {"success":True,"device_id":device_id,"frame_id":result}
        else:
            self.error = errorCodeObj(-5,"Error adding frame to database")

    def frame_count(self,device_id):
        count = 0
        response = self.db.frame_count(device_id)
        self.response = {"success":True,"frame_count":count}

    def last_frame(self,device_id):
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
