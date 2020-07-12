from __future__ import print_function

import json
import webbrowser
import time
import datetime as dt
import pandas as pd
import numpy as np
import re
import gspread
import os
from oauth2client.service_account import ServiceAccountCredentials
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from dataclasses import dataclass
import cv2
import pytesseract


sleepFilename = 'sleep_data.csv'
url = 'http://localhost:8080/'

#remove old data to check that it comes back again
try:
    os.remove("results_heart.json")
except Exception:
    pass

webbrowser.open(url, new=0, autoraise=True)

# wait until file is created from php script
counter1 = 0
while not os.path.exists('results_heart.json'):
    time.sleep(1)
    counter1 = counter1 +1
    if counter1 > 20:
        print("Failed to load fitbit data... exiting")
        exit()
time.sleep(1)    # pause 1 second after file is created

## download daylio updated csv ##
#do auth
gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

# Search for Daylio, order by date
DaylioFilename = 'daylio_downloaded.csv'
# get file list
DriveDaylioFile_list = drive.ListFile({'q': "title contains 'daylio' and trashed=false", 'orderBy': 'createdDate'})
DaylioFile_list = DriveDaylioFile_list.GetList()
# download file
DaylioFile_list[-1].GetContentFile(DaylioFilename, mimetype=None)
##########################

# Search for HRV, order by date
# HRV_filename = 'HRV.png'
# # get file list
# DriveHRVFile_list = drive.ListFile({'q': "title contains 'ReactNative-snapshot-image' and trashed=false", 'orderBy': 'createdDate'})
# HRVFile_list = DriveHRVFile_list.GetList()
# # download file
# HRVFile_list[-1].GetContentFile(HRV_filename, mimetype=None)
##########################


# use creds to create a client to interact with the Google Drive API
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('creds/TrainingDiary-e0ecebfc1b5d.json', scope)
client = gspread.authorize(creds)
drive = GoogleDrive()

# Find a workbook by name and open the first sheet
# Make sure you use the right name here.
sheet = client.open("TraingDiaryRassool2020").sheet1

# Extract and print all of the values
list_of_hashes = sheet.get_all_records()

# print(list_of_hashes)
def main():
    # Find header rows, return struct
    headers = google_sheets_headers(sheet)

    #####################
    ## fitbit fn calls ##
    #####################
    extract_fitbit_data()
    #update sleep/hr on gsheets
    dataframes_update(headers)

    ################
    ## Mood stuff ##
    ## ## ## ## ## ## #

    # #### pull existing sleep data from google sheets
    mood_list = sheet.col_values(headers.MOOD)
    # find next required mood index
    req_mood_index = len(mood_list) + 1  # plus one is to move to the _next_ day

    # import daylio moods
    daylio_df = read_daylio_csv(DaylioFilename)

    # Update mood cells on gsheets
    update_moods(daylio_df,req_mood_index,headers)

    # Anaysle Readiness image
    # HRVdata = read_in_HRV(HRV_filename)




###############################################################
###############################################################
##################### Extra Functions #########################
###############################################################
###############################################################

def extract_fitbit_data():
    # initialise vectors/lists
    bedtimes = []
    efficiency = []

    with open('results_sleep.json', 'r') as fp:
        obj = json.load(fp)

    for sleep_event in obj['sleep']:
        bedtimes.append((sleep_event['startTime'],
                         sleep_event['timeInBed'] / 60.0,
                         sleep_event['endTime']))
        efficiency.append((sleep_event['efficiency']))

    durations = []
    bed_times = []
    wake_times = []
    date_sleep = []

    for sleepday in bedtimes:
        # for entry in sleepday[sleepday]:
        # gone to sleep data
        date_string_sleep = re.split('T', sleepday[0])
        time_string_sleep = re.split(':\d\d\.', date_string_sleep[1])

        # wake data
        date_string_wake = re.split('T', sleepday[2])
        time_string_wake = re.split(':\d\d\.', date_string_wake[1])

        # duration_sleep = re.split('9',sleepday[1])
        duration_sleep = round(sleepday[1], 2)

        # append to vectors
        durations.append(duration_sleep)
        bed_times.append(time_string_sleep[0])
        wake_times.append(time_string_wake[0])
        date_sleep.append(date_string_wake[0])

    #### Heart Rate
    heartrates = []

    with open('results_heart.json', 'r') as fp:
        obj = json.load(fp)

    # print(obj)

    for p in obj['activities-heart']:
        try:
            heartrates.append((p['dateTime'], p['value']['restingHeartRate']))
        except KeyError:
            heartrates.append((p['dateTime'])), -1

    heartrates.reverse()

    hr_date = []
    hr_resting = []

    for hr_day in heartrates:
        hr_date.append(hr_day[0])
        hr_resting.append(hr_day[1])

    # make pandas data frame and rearrange lists to columns
    df = pd.DataFrame(list(zip(*[date_sleep, bed_times, wake_times, durations, efficiency, hr_resting]))).add_prefix(
        'Col')

    # reverse the order so it goes from old data at the top to current data at the bottom
    df = df[::-1]

    # save data frame to csv
    df.to_csv(sleepFilename, index=False)

def dataframes_update(headers):
    """Shows basic usage of the Sheets API.
     Prints values from a sample spreadsheet.
     """
    sheets_date = google_sheets_date_and_index()

    # sleep data
    sleep_dataframe = pd.read_csv(sleepFilename,
                                  names=["full_date", "Start", "End", "Duration", "Efficiency", "HeartRate"])
    sleep_dataframe = sleep_dataframe.iloc[1:]  # remove first line
    # convert to date time and then to ISO
    sleep_dataframe['full_date'] = pd.to_datetime(sleep_dataframe['full_date'], format='%Y-%m-%d')
    sleep_dataframe['full_date'] = sleep_dataframe['full_date'].dt.strftime('%Y%m%d')

    # FINAL DATA FRAMES
    # convert all dates to int
    sleep_dataframe['full_date'] = sleep_dataframe['full_date'].str.replace('\D', '').astype(int)
    # subtract one day from the sleep dates because for some reason they are a day ahead from fitbit.
    # sleep_dataframe['full_date'] = sleep_dataframe['full_date'] - 1

    # remove any duplicate date entries. This indicates a nap was had. Remove the second entry, this is the nap.
    sleep_dataframe = sleep_dataframe.drop_duplicates('full_date', keep='first')

    # join the data frames
    join_df = sheets_date.merge(sleep_dataframe, on='full_date', how='left')
    # add the row index relevant to google sheets
    sheets_sleep_ready = join_df.set_index("sheetindex", drop=True, append=False, inplace=False, verify_integrity=False)
    sheets_sleep_ready.dropna(inplace=True)
    # ### #### #### #### #### #### #### #### ####

    # find the index where the new sleep data stops
    new_sleep_index = sheets_sleep_ready.index[-1]

    # #### pull existing sleep data from google sheets

    sleep_list = sheet.col_values(headers.START)
    # find next required sleep index
    req_sleep_index = len(sleep_list) + 1  # plus one is to move to the _next_ day

    update_sleep_cells_from_dataframe(req_sleep_index, new_sleep_index, sheets_sleep_ready, headers)


def update_sleep_cells_from_dataframe(current_index, new_sleep_index, sheets_sleep_ready, headers):
    while current_index <= new_sleep_index:
        if sheets_sleep_ready.index.isin([(current_index)]).any():
            # new test, attempt to update cell, only if there is a value to update with. Should save on the requests to google per 100 seconds
            if sheets_sleep_ready['Start'].loc[current_index] != '':
                sheet.update_cell(current_index, headers.START, sheets_sleep_ready['Start'].loc[current_index])
            if sheets_sleep_ready['End'].loc[current_index] != '':
                sheet.update_cell(current_index, headers.END, sheets_sleep_ready['End'].loc[current_index])
            if sheets_sleep_ready['Duration'].loc[current_index] != '':
                sheet.update_cell(current_index, headers.TIMEINBED, sheets_sleep_ready['Duration'].loc[current_index])
            if sheets_sleep_ready['Efficiency'].loc[current_index] != '':
                sheet.update_cell(current_index, headers.SLPEEQUAL, sheets_sleep_ready['Efficiency'].loc[current_index])
            if sheets_sleep_ready['HeartRate'].loc[current_index] != '':
                sheet.update_cell(current_index, headers.MORNHR, sheets_sleep_ready['HeartRate'].loc[current_index])
            #
            # sheet.update_cell(current_index, 9, sheets_sleep_ready['Start'].loc[current_index])
            # sheet.update_cell(current_index, 10, sheets_sleep_ready['End'].loc[current_index])
            # sheet.update_cell(current_index, 11, sheets_sleep_ready['Duration'].loc[current_index])
            # sheet.update_cell(current_index, 12, sheets_sleep_ready['Efficiency'].loc[current_index])
            # sheet.update_cell(current_index, 13, sheets_sleep_ready['HeartRate'].loc[current_index])
        current_index = current_index + 1

def update_moods(daylio_df,req_mood_index,headers):

    sheets_date = google_sheets_date_and_index()

    # merge
    daylio_indexed = sheets_date.merge(daylio_df, on='full_date', how='left')
    # add the row index relevant to google sheets
    daylio_indexed = daylio_indexed.set_index("sheetindex", drop=True, append=False, inplace=False,
                                              verify_integrity=False)
    # for some reason, google sheets doens't like int64s. Convert mood to float
    daylio_indexed['mood'] = daylio_indexed['mood'].astype(float)
    daylio_indexed.fillna('', inplace=True)  # replace all nans with blank strings

    # update cells
    new_mood_index = daylio_indexed.index[-1]
    current_index = req_mood_index

    while current_index <= new_mood_index:
        if daylio_indexed.index.isin([(current_index)]).any():
            sheet.update_cell(current_index, headers.MOOD, daylio_indexed['mood'].loc[current_index])
            sheet.update_cell(current_index, headers.COMPUTERFUNCTION, daylio_indexed['computer_fn'].loc[current_index])
            sheet.update_cell(current_index, headers.TIREDNESS, daylio_indexed['tiredness'].loc[current_index])
            sheet.update_cell(current_index, headers.READINESS, daylio_indexed['readiness'].loc[current_index])
            sheet.update_cell(current_index, headers.NAP, daylio_indexed['napmins'].loc[current_index])
            sheet.update_cell(current_index, headers.HEALTHNOTES, daylio_indexed['note'].loc[current_index])
        current_index = current_index + 1

def read_daylio_csv(DaylioFilename):
    df = pd.read_csv(
        DaylioFilename)  # read the csv file (put 'r' before the path string to address any special characters, such as '\'). Don't forget to put the file name at the end of the path + ".csv"
    num_of_days = 40  # number of days to scan on the dataframe

    df = df[::-1]  # reverse the dataframe so old is at top, new at the bottom
    df = df.tail(num_of_days)  # take the last days of the dataframe
    df['full_date'] = df['full_date'].str.replace("-", '').astype(int)  # reformat date to ISO
    df.fillna('', inplace=True)  # replace all nans with blank strings

    activities = df['activities']  # take just the activities
    # health_notes = df['note']
    mood = df['mood']
    date_list = df['full_date']

    # # # # # # # # # # # # # # # # #
    ## Extract Data From Activities ##
    # # # # # # # # # # # # # # # # #

    computer_fn = []
    tiredness = []
    readiness = []
    napmins = []
    for act_day in activities:
        re_day = re.findall(r'\dr', act_day)
        cf_day = re.findall(r'\dc', act_day)
        ti_day = re.findall(r'\dt', act_day)
        nap_day = re.findall(r'.\dn', act_day)

        # append to vectors, remove non-numeric digits and check if it's empty.
        # if empty, put a NaN in it's place. Nan's are good here because they work well with groupby (merging) later
        if cf_day:
            cf_day = re.sub(r"\D", "", cf_day[0])
            computer_fn.append(float(cf_day))
        else:
            computer_fn.append(np.nan)
        if ti_day:
            ti_day = re.sub(r"\D", "", ti_day[0])
            tiredness.append(float(ti_day))
        else:
            tiredness.append(np.nan)
        if re_day:
            re_day = re.sub(r"\D", "", re_day[0])
            readiness.append(float(re_day))
        else:
            readiness.append(np.nan)
        if nap_day:
            nap_day = re.sub(r"\D", "", nap_day[0])
            napmins.append(float(nap_day))
        else:
            napmins.append(np.nan)

    # # # # # # # # # # # # # # #
    ## Extract Data From Moods ##
    # # # # # # # # # # # # # # #
    mood_num = []
    for mood_day in mood:
        mood_day = re.sub('awful', '1', mood_day)
        mood_day = re.sub('bad', '2', mood_day)
        mood_day = re.sub('meh', '3', mood_day)
        mood_day = re.sub('good', '4', mood_day)
        mood_day = re.sub('rad', '5', mood_day)
        mood_day = re.sub('nothing', '-1', mood_day)
        mood_num.append(mood_day)

    ## Create master dataframe ##
    df1 = pd.DataFrame(list(zip(*[date_list, mood_num, readiness, computer_fn, tiredness, napmins])),
                       columns=["full_date", "mood", "readiness", "computer_fn", "tiredness", "napmins"])
    df1['mood'] = df1['mood'].str.replace('\D', '').astype(int)  # convert mood to ints from string
    df1_mean = df1.groupby('full_date').mean().reset_index()  # merged dataframe. TO DO. This probably screws with -1 moods
    df2 = df[['full_date', 'note']].copy()
    df2_mean = df2.groupby('full_date')['note'].apply(','.join)
    df_daylio_out = df1_mean.merge(df2_mean, on='full_date', how='left')

    df_daylio_out.to_csv('daylio_indexed.csv', index=False)
    return df_daylio_out

def google_sheets_date_and_index():
    # pull dates from google sheets
    date_start_index = 3
    # sheet.update_cell(1, 1, "Hell Tris!")
    date_list = sheet.col_values(1)
    # delete first few rows that contain header information
    del date_list[0:date_start_index]
    # print(date_list)

    # reformat date strings gathered from google sheets
    stripped_date = []
    row_num = []
    current_row = date_start_index + 1  # plus one here is for zero indexing in python compared to sheets
    for date in date_list:
        dtt = dt.datetime.strptime(date, "%d/%m/%Y").strftime('%Y%m%d')
        stripped_date.append(dtt)
        row_num.append(current_row)
        current_row = current_row + 1

    sheets_date = pd.DataFrame(list(zip(*[row_num, stripped_date])), columns=["sheetindex", "full_date"])
    sheets_date['full_date'] = sheets_date['full_date'].str.replace('\D', '').astype(int)

    return sheets_date

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
    HEALTHNOTEScell= sheet.find("HEALTHNOTES")
    HRVREADINESScell= sheet.find("HRVREADINESS")

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
        COMPUTERFUNCTION : int
        TIREDNESS : int
        HEALTHNOTES : int
        HRVREADINESS : int

    p = HeaderLocation(READINESScell.col, NAPcell.col, STARTcell.col, ENDcell.col, TIMEINBEDcell.col, SLEEPQUALcell.col, MORNHRcell.col, MOODcell.col, COMPUTERFUNCTION_RATINGcell.col, TIREDNESS_RATINGcell.col, HEALTHNOTEScell.col , HRVREADINESScell.col )

    return p




def read_in_HRV(file_path):
    # Read in Image
    img = cv2.imread(file_path)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = cv2.bitwise_not(gray)

    #### READINESS #####
    # Readiness Vars
    yRea = 175
    xRea = 380
    hRea = 274
    wRea = 320
    imgRea = gray[yRea:yRea + hRea, xRea:xRea + wRea].copy()
    imgRea = cv2.resize(imgRea, None, fx=.15, fy=.15)
    # cv2.imshow("cropped", imgRea)
    # cv2.waitKey(0)

    # Readiness OCR
    kernel = np.ones((2, 1), np.uint8)
    imgRea = cv2.erode(imgRea, kernel, iterations=1)
    imgRea = cv2.dilate(imgRea, kernel, iterations=1)
    imgRea = cv2.dilate(imgRea, kernel, iterations=1)
    ocr_Rea = pytesseract.image_to_string(imgRea, lang='eng', \
                                          config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789')
    #### HRV #####
    # HRV Vars
    yHRV = 603
    xHRV = 230
    hHRV = 135
    wHRV = 200
    imgHRV = gray[yHRV:yHRV + hHRV, xHRV:xHRV + wHRV].copy()
    imgHRV = cv2.resize(imgHRV, None, fx=.75, fy=.75)
    # cv2.imshow("cropped", imgHRV)
    # cv2.waitKey(0)

    # HRVOCR
    ocr_HRV = pytesseract.image_to_string(imgHRV, lang='eng', \
                                          config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789')

    #### RHR #####
    # RHR Vars
    yRHR = 603
    xRHR = 650
    hRHR = 135
    wRHR = 200
    imgRHR = gray[yRHR:yRHR + hRHR, xRHR:xRHR + wRHR].copy()
    imgRHR = cv2.resize(imgRHR, None, fx=.75, fy=.75)
    # cv2.imshow("cropped", imgRHR)
    # cv2.waitKey(0)

    # RHROCR
    ocr_RHR = pytesseract.image_to_string(imgRHR, lang='eng', \
                                          config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789')

    # Save and Return Data
    @dataclass
    class HRV_data:
        READINESS: int
        HRV: int
        RHR: int
    HRV_output = HRV_data(int(ocr_Rea), int(ocr_HRV), int(ocr_RHR))

    return HRV_output







if __name__ == '__main__':
    main()
