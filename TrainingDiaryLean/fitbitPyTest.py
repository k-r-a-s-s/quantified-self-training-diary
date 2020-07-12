# %matplotlib inline
import matplotlib.pyplot as plt
import fitbit
import datetime as dt

# gather_keys_oauth2.py file needs to be in the same directory.
# also needs to install cherrypy: https://pypi.org/project/CherryPy/
# pip install CherryPy
from gather_keys_oauth2 import OAuth2Server
import pandas as pd
import datetime


# YOU NEED TO PUT IN YOUR OWN CLIENT_ID AND CLIENT_SECRET
CLIENT_ID='22BMN8'
CLIENT_SECRET='5ea2ab7be1dd0a24836a7eb4f7e8a2aa'


server= OAuth2Server(CLIENT_ID, CLIENT_SECRET)
server.browser_authorize()
ACCESS_TOKEN=str(server.fitbit.client.session.token['access_token'])
REFRESH_TOKEN=str(server.fitbit.client.session.token['refresh_token'])
auth2_client=fitbit.Fitbit(CLIENT_ID,CLIENT_SECRET,oauth2=True,access_token=ACCESS_TOKEN,refresh_token=REFRESH_TOKEN)

# startTime is first date of data that I want.
# You will need to modify for the date you want your data to start
startTime = dt.datetime(year=2020, month=6, day=5)
endTime = dt.datetime.today().date() - datetime.timedelta(days=1)
date_list = []
resting_list = []
allDates = pd.date_range(start=startTime, end=endTime)
# for oneDate in allDates:
#     oneDate = oneDate.date().strftime("%Y-%m-%d")
#     oneDayData = auth2_client.intraday_time_series('activities/heart', base_date=oneDate, detail_level='1sec')
#     date_list.append(oneDate)
#     resting_list.append(
#         oneDayData['activities-heart'][0]['value']['restingHeartRate'])
#
# print(resting_list)

df_list = []
stages_df_list = []

for oneDate in allDates:
    oneDate = oneDate.date().strftime("%Y-%m-%d")
    oneDayData = auth2_client.sleep(date=oneDate)
    print(oneDayData)
    print(type(oneDayData))
    # get number of minutes for each stage of sleep and such.
    # stages_df = pd.DataFrame(oneDayData['sleep'][0])
    stages_df = pd.DataFrame(oneDayData['sleep'][0]['startTime'])
    df = pd.DataFrame(oneDayData['sleep'][0]['timeInBed'])

    date_list.append(oneDate)
    df_list.append(df)
    stages_df_list.append(stages_df)

final_df_list = []
final_stages_df_list = []

for date, df, stages_df in zip(date_list, df_list, stages_df_list):

    if len(df) == 0:
        continue
    df.loc[:, 'date'] = pd.to_datetime(date)
    stages_df.loc[:, 'date'] = pd.to_datetime(date)
    final_df_list.append(df)
    final_stages_df_list.append(stages_df)

final_df = pd.concat(final_df_list, axis=0)

final_stages_df = pd.concat(final_stages_df_list, axis=0)
columns = final_stages_df.columns[~final_stages_df.columns.isin(['date'])].values
pd.concat([final_stages_df[columns] + 2, final_stages_df[['date']]], axis = 1)

# Export file to csv
final_df.to_csv('minuteSleep' + '.csv', index = False)
final_stages_df.to_csv('minutesStagesSleep' + '.csv', index = True)

