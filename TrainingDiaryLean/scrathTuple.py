from __future__ import print_function

from typing import NamedTuple
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dataclasses import dataclass


# class User(NamedTuple):
#     name: str
#
#
# class MyStruct(NamedTuple):
#     foo: str
#     bar: int
#     baz: list
#     qux: User


# my_item = MyStruct('foo', 0, ['baz'], User('peter'))


# use creds to create a client to interact with the Google Drive API
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('creds/TrainingDiary-e0ecebfc1b5d.json', scope)
client = gspread.authorize(creds)

# Find a workbook by name and open the first sheet
# Make sure you use the right name here.
sheet = client.open("TraingDiaryRassool2020").sheet1

def main():

    p = google_sheets_headers(sheet)
    print(p)


def google_sheets_headers(sheet):
    READINESScell = sheet.find("READINESS")
    NAPcell= sheet.find("NAP")
    STARTcell= sheet.find("START")
    ENDcell= sheet.find("END")
    TIMEINBEDcell= sheet.find("TIMEINBED")
    SLEEPQUALcell= sheet.find("SLEEPQUAL")
    MORNHRcell= sheet.find("MORNHR")
    MOODcell= sheet.find("MOOD")
    COMPUTERFUNCTION_RATINGcell= sheet.find("COMPUTERFUNCTION_RATING")
    TIREDNESS_RATINGcell= sheet.find("TIREDNESS_RATING")
    HEALTHNOTEScell= sheet.find(" HEALTHNOTES")

    @dataclass
    class HeaderLocation:
        READINESS : int
        NAP : int
        START : int
        END : int
        TIMEINBED : int
        SLPEEQUAL : int
        MORNHR : int
        MOOD : int
        COMPUTERFUNCTION_RATING : int
        TIREDNESS_RATING : int
        HEALTHNOTES : int

    p = HeaderLocation(READINESScell.col, NAPcell.col, STARTcell.col, ENDcell.col, TIMEINBEDcell.col, SLEEPQUALcell.col, MORNHRcell.col, MOODcell.col, COMPUTERFUNCTION_RATINGcell.col, TIREDNESS_RATINGcell.col, HEALTHNOTEScell.col )

    return p



if __name__ == '__main__':
    main()