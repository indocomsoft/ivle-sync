#! /usr/bin/env python
import requests
import os.path
from os import makedirs
from getpass import getpass
from bs4 import BeautifulSoup

LAPI_KEY = "2urj280s9196lPJInBDNP"
USER_AGENT = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.120 Safari/537.36"

USERID = input("UserID: ")
PASSWORD = getpass("Password: ")

class Module:
    def __init__(self, moduleId, name, code):
        self.id = moduleId
        self.name = name
        self.code = code

class WorkbinFolder:
    def __init__(self, folderJson, path=""):
        self.name = folderJson["FolderName"]
        self.id = folderJson["ID"]
        self.path = path + "/" + self.name

        self.folders = []
        for fileJson in folderJson["Folders"]:
            self.folders.append(WorkbinFolder(fileJson, self.path))

        self.files = []
        for fileJson in folderJson["Files"]:
            self.files.append(WorkbinFile(fileJson, self.path))

    def printPath(self):
        print(self.path)

        for folder in self.folders:
            folder.printPath()

        for file in self.files:
            print(file.path)

    def print(self, indent=0):
        print("    " * indent + self.name + "/")

        for folder in self.folders:
            folder.print(indent+1)

        for file in self.files:
            print("    " * (indent+1) + file.name)

class WorkbinFile:
    def __init__(self, fileJson, path=""):
        self.name = fileJson["FileName"]
        self.id = fileJson["ID"]
        self.path = path + "/" + self.name

class IVLESession:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": USER_AGENT})

        self.token = self.get_token(USERID, PASSWORD)

    def get_token(self, userid, password):
        r = self.s.get("https://ivle.nus.edu.sg/api/login/?apikey=" + LAPI_KEY)
        soup = BeautifulSoup(r.content, "html.parser")

        VIEWSTATE = soup.find(id="__VIEWSTATE")['value']
        VIEWSTATEGENERATOR = soup.find(id="__VIEWSTATEGENERATOR")['value']

        data = {
                "__VIEWSTATE": VIEWSTATE,
                "__VIEWSTATEGENERATOR": VIEWSTATEGENERATOR,
                "userid": USERID,
                "password": PASSWORD
            }

        r = self.s.post("https://ivle.nus.edu.sg/api/login/?apikey=" + LAPI_KEY, data)
        return r.text

    def get_modules(self):
        result = self.lapi("Modules")

        modules = []
        for module in result["Results"]:
            modules.append(Module(
                    module["ID"],
                    module["CourseName"],
                    module["CourseCode"]
                ))
        return modules

    def get_workbin(self, module):
        result = self.lapi("Workbins", {"CourseID": module.id})

        folders = []
        for workbin in result["Results"]:
            for folder in workbin["Folders"]:
                folders.append(WorkbinFolder(folder, module.code))
        return folders

    def lapi(self, method, params={}):
        params["APIKey"] = LAPI_KEY
        params["AuthToken"] = self.token
        return self.s.get("https://ivle.nus.edu.sg/api/Lapi.svc/" + method,
            params=params).json()

    def download_file(self, file):
        params = {
                    "APIKey": LAPI_KEY,
                    "AuthToken": self.token,
                    "ID": file.id,
                    "target": "workbin"
                }

        r = self.s.get("https://ivle.nus.edu.sg/api/downloadfile.ashx",
                stream=True, params=params)

        makedirs(os.path.dirname(file.path), exist_ok=True)

        if os.path.isfile(file.path):
            print("Skipping " + file.path + ".")
            return

        print("Downloading " + file.path + ".")
        with open(file.path, 'wb') as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)

    def download_folder(self, target_folder):
        for folder in target_folder.folders:
            self.download_folder(folder)

        for file in target_folder.files:
            self.download_file(file)

def main():
    session = IVLESession()
    modules = session.get_modules()

    for module in modules:
        folders = session.get_workbin(module)
        for folder in folders:
            session.download_folder(folder)

if __name__ == "__main__":
    main()