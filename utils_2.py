import json
import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
from Spreadsheet import Spreadsheet
from typing import List, Dict, Any
from pprint import pprint


# Файл, полученный в Google Developer Console
CREDENTIALS_FILE = 'project-fa0cf409504d.json'

def init():
    # Авторизуемся и получаем service — экземпляр доступа к API
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIALS_FILE,
        ['https://www.googleapis.com/auth/spreadsheets',
         'https://www.googleapis.com/auth/drive'])
    httpAuth = credentials.authorize(httplib2.Http())
    service = apiclient.discovery.build('sheets', 'v4', http=httpAuth)
    return  service



def _read_M(idSpreadheet, addr='A1:RO10000'):
    service = init()
    spreadsheet = service.spreadsheets().get(spreadsheetId=idSpreadheet).execute()
    sheetList = spreadsheet.get('sheets')
    all = []
    for sheet in sheetList:
        title = sheet['properties']['title']
        # print(title)
        s = service.spreadsheets().values().get(
            spreadsheetId=idSpreadheet,
            range='\''+title + '\'!' + addr,
            majorDimension='ROWS'
        ).execute()
        s = s['values']
        r = []
        h = []
        res = {}
        for i, x in enumerate(s):
            if i == 0:
                h.append(x)
            else:
                if len(x) > 0:
                    r.append(x)

        res['templFile'] = title
        res['header'] = h
        res['data'] = r
        all.append(res)
    return all

def getmultiblock(idSSheet):
    data = _read_M(idSSheet)
    r = json.dumps(data)
    return data

if __name__ == "__main__":
    # Приклад використання:
    pprint(getmultiblock('1vWepnObCCI_61Ubt4Dlh6nWBjOUICCCrn8MyG-od9Sg'))
