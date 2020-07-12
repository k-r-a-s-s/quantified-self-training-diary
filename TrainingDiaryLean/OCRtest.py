import cv2
import pytesseract
import numpy as np
from dataclasses import dataclass
from oauth2client.service_account import ServiceAccountCredentials
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

## download daylio updated csv ##
#do auth
gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)


# Search for Daylio, order by date
DriveHRVfile_list = drive.ListFile({'q': "title contains 'ReactNative-snapshot-image' and trashed=false", 'orderBy': 'createdDate'})
file_list = DriveHRVfile_list.GetList()
# download file
file_list[-1].GetContentFile('HRV.png', mimetype=None)
##########################


def main():

    p = read_in_HRV()
    print(p.READINESS)

def read_in_HRV():
    # Read in Image
    img = cv2.imread('ReactNative-snapshot-image2148816711250379566.png')
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

    @dataclass
    class HRV_data:
        READINESS: int
        HRV: int
        RHR: int

    HRV_output = HRV_data(int(ocr_Rea), int(ocr_HRV), int(ocr_RHR))

    return HRV_output





if __name__ == '__main__':
    main()
