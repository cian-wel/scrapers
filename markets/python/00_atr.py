# -*- coding: utf-8 -*-
"""
Created on Sun Apr 17 21:05:49 2022

@author: weldo

00_atr.py

this file scrapes price data from atr for today's races

"""

#%% proform function
def proform_import() :
    pf_db_con = pyodbc.connect(
        r'''Driver={SQL Server};
        Server=localhost\PROFORM_RACING;
        Database=PRODB;
        Trusted_Connection=yes;''')
        
    date = pd.Timestamp.now().normalize()

    runners = pd.read_sql_query(
            '''SELECT RH_RNo, HIR_HNo FROM vw_Races''', pf_db_con)
    runners = runners.rename(columns={
        "RH_RNo" : "race_id",
        "HIR_HNo" : "horse_id"
        })

    races = pd.read_sql_query(
            '''SELECT RH_RNo, RH_DateTime, RH_CNo FROM NEW_RH''', pf_db_con)

    races = races.rename(columns={
        "RH_RNo" : "race_id",
        "RH_DateTime" : "race_datetime",
        "RH_CNo" : "course_id"
        })

    course_lkup = pd.read_sql_query('''SELECT C_ID, C_Name FROM NEW_C''', pf_db_con)
    races = pd.merge(races, course_lkup[['C_ID', 'C_Name']],
                       left_on = 'course_id',
                       right_on = 'C_ID',
                       how = 'left')
    races = races.rename(columns={'C_Name' : 'crse_name'})
    races.drop(['C_ID', 'course_id'], inplace=True, axis=1)

    runners = pd.merge(runners, races, on='race_id', how = 'left')
    runners['race_datetime'] = pd.to_datetime(runners['race_datetime'])
    runners = runners[runners.race_datetime >= date]

    horses = pd.read_sql_query('''SELECT H_No, H_Name FROM NEW_H''', pf_db_con)

    horses = horses.rename(columns={
        'H_No' : 'horse_id',
        'H_Name' : 'horse_name'
        })
    runners = pd.merge(runners, horses, on = 'horse_id', how = 'left')

    runners.sort_values(['crse_name', 'race_datetime'], ascending=[True, True], inplace=True)
    
    return runners

#%% today function
def atr_today() :
    base_url = 'https://www.attheraces.com/racecard/'
    left_books = ['bet365', 'will_hill', 'lads', 'pp', 'coral', 'unibet', 'sport888', 'betfairsb', 'sts', 'tote']
    right_books = ['betfred', 'betvictor', 'boylesports', 'sportnation', 'parimatch', 'betway', 'fansbet', 'grosvenor', 'spreadex', 'skybet', 'quinnbet', 'matchbook', 'smarkets', 'bfex']

    runners = proform_import()
    horse_columns = ['crse_name', 'race_datetime', 'horse_name']
    grid_columns = []
    grid_columns.extend(horse_columns)
    grid_columns.extend(left_books)
    grid_columns.extend(right_books)
    race_grid = pd.DataFrame(columns=grid_columns)
    horse_grid = pd.DataFrame(columns=horse_columns)
    odds_grid = pd.DataFrame(columns=horse_columns)

    driver = webdriver.Chrome()
    first = True

    date = pd.Timestamp.now()
    
    fut_runners = runners
    fut_runners.crse_name.replace('Epsom', 'Epsom Downs', inplace=True)
    fut_runners = fut_runners[(fut_runners.race_datetime > date) & (fut_runners.race_datetime < (date.normalize() + pd.DateOffset(days=1)))]
    fut_crses = fut_runners.drop_duplicates(subset='crse_name').drop(columns=['race_id', 'horse_id', 'horse_name']).reset_index(drop=True)
    fut_crses['adj_crse_name'] = fut_crses.crse_name.replace(' ', '-', regex=True)
    fut_crses['date'] = fut_crses.race_datetime.dt.date

    # scrape
    if len(fut_crses) > 0 :
        crses = fut_crses.reset_index(drop=True)
        for j in crses.index :
            driver.close()
            driver = webdriver.Chrome()
            first = True
            crse_races = fut_runners[fut_runners.crse_name == crses.crse_name[j]].drop_duplicates(subset='race_id').reset_index(drop=True)
            for k in crse_races.index :
                horse_grid = pd.DataFrame(columns=horse_columns)
                
                url = base_url + crses.adj_crse_name[j] + '/' + crses.date[j].strftime(format='%d-%B-%Y') + '/' + crse_races.race_datetime[k].strftime(format='%H%M')
                print(url)
                driver.get(url)
                
                if first :
                    driver.maximize_window()
                    driver.find_element_by_xpath('//*/div[1]/div/div/div[2]/div/button[2]').click()
                    driver.find_element_by_xpath('//*/div[4]/div[1]/aside/div/ul/li[1]/label').click()
                    driver.find_element_by_xpath('//*/div[4]/div[1]/aside/div/ul/li[3]/label').click()
                    first = False
                
                # get horse names (may not be in order)
                try:
                    try :
                        horse_grid=pd.DataFrame(columns = ['crse_name', 'race_datetime', 'horse_name'])
                        for horse in driver.find_elements_by_class_name('odds-grid-horse__name'):
                            res = horse.text
                            horse_odds = {'crse_name':crse_races.crse_name[k],
                                      'race_datetime':crse_races.race_datetime[k],
                                      'horse_name':res}
                            horse_grid = horse_grid.append(horse_odds, ignore_index=True)
                            #print(res)
                    except StaleElementReferenceException:
                        driver.get(url)
                        horse_grid=pd.DataFrame(columns = ['crse_name', 'race_datetime', 'horse_name'])
                        for horse in driver.find_elements_by_class_name('odds-grid-horse__name'):
                            res = horse.text
                            horse_odds = {'crse_name':crse_races.crse_name[k],
                                      'race_datetime':crse_races.race_datetime[k],
                                      'horse_name':res}
                            horse_grid = horse_grid.append(horse_odds, ignore_index=True)
                            #print(res)
                except StaleElementReferenceException:
                    driver.get(url)
                    horse_grid=pd.DataFrame(columns = ['crse_name', 'race_datetime', 'horse_name'])
                    for horse in driver.find_elements_by_class_name('odds-grid-horse__name'):
                        res = horse.text
                        horse_odds = {'crse_name':crse_races.crse_name[k],
                                  'race_datetime':crse_races.race_datetime[k],
                                  'horse_name':res}
                        horse_grid = horse_grid.append(horse_odds, ignore_index=True)
                        #print(res)
                
                # get odds
                try:
                    try :
                        race_odds = pd.DataFrame(columns=['odds'])
                        for bookie in driver.find_elements_by_class_name('odds-grid__cell--odds') :
                            res = bookie.text
                            odds = {'odds' : res}
                            race_odds = race_odds.append(odds, ignore_index=True)
                            #print(res)
                    except StaleElementReferenceException:
                        driver.get(url)
                        race_odds = pd.DataFrame(columns=['odds'])
                        for bookie in driver.find_elements_by_class_name('odds-grid__cell--odds') :
                            res = bookie.text
                            odds = {'odds' : res}
                            race_odds = race_odds.append(odds, ignore_index=True)
                            #print(res)
                except StaleElementReferenceException:
                    driver.get(url)
                    race_odds = pd.DataFrame(columns=['odds'])
                    for bookie in driver.find_elements_by_class_name('odds-grid__cell--odds') :
                        res = bookie.text
                        odds = {'odds' : res}
                        race_odds = race_odds.append(odds, ignore_index=True)
                        #print(res)
                
                # clean odds and add to odds grid
                race_odds.odds.replace(to_replace='-',value = np.nan, inplace=True)
                race_odds.odds.replace(to_replace='odds',value = np.nan, inplace=True)
                race_odds.odds.replace(to_replace='N/A',value = np.nan, inplace=True)
                race_odds.odds.replace(to_replace='SP',value = np.nan, inplace=True)
                race_odds['odds'] = pd.to_numeric(race_odds.odds)
                
                left_grid = pd.DataFrame(race_odds[race_odds.index < (len(horse_grid)*len(left_books))])
                left_grid = pd.DataFrame(np.reshape(left_grid.values, (len(horse_grid),len(left_books))))
                left_grid.columns = left_books
                
                right_grid = pd.DataFrame(race_odds[race_odds.index >= (len(horse_grid)*len(left_books))])
                right_grid = pd.DataFrame(np.reshape(right_grid.values, (len(horse_grid),len(right_books))))
                right_grid.columns = right_books
                
                race_grid = pd.DataFrame()
                race_grid[horse_columns] = horse_grid
                race_grid[left_books] = left_grid
                race_grid[right_books] = right_grid
                
                odds_grid = odds_grid.append(race_grid, ignore_index=True)
                
        
        odds_grid['med_odds'] = odds_grid.median(axis = 1)
        odds_grid.crse_name.replace('Epsom Downs', 'Epsom', inplace=True)
        feather.write_feather(odds_grid, '../output/' + date.strftime('%Y-%m-%d') + '_atr_odds' + pd.Timestamp.now().strftime('%d-%H-%M') + '.ftr')
    
    driver.close()
    
    print("today scraped")
    print(pd.Timestamp.now())
    return
    
#%% scrape tomorrow
def atr_tomorrow() :
    base_url = 'https://www.attheraces.com/racecard/'
# =============================================================================
#     left_books = ['bet365', 'will_hill', 'lads', 'pp', 'coral', 'unibet', 'sport888', 'betfairsb', 'sts', 'tote']
#     right_books = ['betfred', 'betvictor', 'boylesports', 'sportnation', 'parimatch', 'betway', 'fansbet', 'grosvenor', 'spreadex', 'skybet', 'quinnbet', 'matchbook', 'smarkets', 'bfex']
# 
#     runners = proform_import()
#     horse_columns = ['crse_name', 'race_datetime', 'horse_name']
#     grid_columns = []
#     grid_columns.extend(horse_columns)
#     grid_columns.extend(left_books)
#     grid_columns.extend(right_books)
#     race_grid = pd.DataFrame(columns=grid_columns)
#     horse_grid = pd.DataFrame(columns=horse_columns)
#     odds_grid = pd.DataFrame(columns=horse_columns)
# 
#     driver = webdriver.Chrome()
#     first = True
#     
#     date = (pd.Timestamp.now() + pd.DateOffset(days=1)).normalize()
# 
#     fut_runners = runners
#     fut_runners.crse_name.replace('Epsom', 'Epsom Downs', inplace=True)
#     fut_runners = fut_runners[(fut_runners.race_datetime > date) & (fut_runners.race_datetime < (date.normalize() + pd.DateOffset(days=1)))]
#     fut_crses = fut_runners.drop_duplicates(subset='crse_name').drop(columns=['race_id', 'horse_id', 'horse_name']).reset_index(drop=True)
#     fut_crses['adj_crse_name'] = fut_crses.crse_name.replace(' ', '-', regex=True)
#     fut_crses['date'] = fut_crses.race_datetime.dt.date
# 
#     # scrape
#     if len(fut_crses) > 0 :
#         crses = fut_crses.reset_index(drop=True)
#         for j in crses.index :
#             driver.close()
#             driver = webdriver.Chrome()
#             first = True
#             crse_races = fut_runners[fut_runners.crse_name == crses.crse_name[j]].drop_duplicates(subset='race_id').reset_index(drop=True)
#             for k in crse_races.index :
#                 horse_grid = pd.DataFrame(columns=horse_columns)
#                 
#                 url = base_url + crses.adj_crse_name[j] + '/' + crses.date[j].strftime(format='%d-%B-%Y') + '/' + crse_races.race_datetime[k].strftime(format='%H%M')
#                 print(url)
#                 driver.get(url)
#                 
#                 if first :
#                     driver.maximize_window()
#                     driver.find_element_by_xpath('//*/div[1]/div/div/div[2]/div/button[2]').click()
#                     driver.find_element_by_xpath('//*/div[4]/div[1]/aside/div/ul/li[1]/label').click()
#                     driver.find_element_by_xpath('//*/div[4]/div[1]/aside/div/ul/li[3]/label').click()
#                     first = False
#                 
#                 # get horse names (may not be in order)
#                 try:
#                     try :
#                         horse_grid=pd.DataFrame(columns = ['crse_name', 'race_datetime', 'horse_name'])
#                         for horse in driver.find_elements_by_class_name('odds-grid-horse__name'):
#                             res = horse.text
#                             horse_odds = {'crse_name':crse_races.crse_name[k],
#                                       'race_datetime':crse_races.race_datetime[k],
#                                       'horse_name':res}
#                             horse_grid = horse_grid.append(horse_odds, ignore_index=True)
#                             #print(res)
#                     except StaleElementReferenceException:
#                         driver.get(url)
#                         horse_grid=pd.DataFrame(columns = ['crse_name', 'race_datetime', 'horse_name'])
#                         for horse in driver.find_elements_by_class_name('odds-grid-horse__name'):
#                             res = horse.text
#                             horse_odds = {'crse_name':crse_races.crse_name[k],
#                                       'race_datetime':crse_races.race_datetime[k],
#                                       'horse_name':res}
#                             horse_grid = horse_grid.append(horse_odds, ignore_index=True)
#                             #print(res)
#                 except StaleElementReferenceException:
#                     driver.get(url)
#                     horse_grid=pd.DataFrame(columns = ['crse_name', 'race_datetime', 'horse_name'])
#                     for horse in driver.find_elements_by_class_name('odds-grid-horse__name'):
#                         res = horse.text
#                         horse_odds = {'crse_name':crse_races.crse_name[k],
#                                   'race_datetime':crse_races.race_datetime[k],
#                                   'horse_name':res}
#                         horse_grid = horse_grid.append(horse_odds, ignore_index=True)
#                         #print(res)
#                 
#                 # get odds
#                 try:
#                     try :
#                         race_odds = pd.DataFrame(columns=['odds'])
#                         for bookie in driver.find_elements_by_class_name('odds-grid__cell--odds') :
#                             res = bookie.text
#                             odds = {'odds' : res}
#                             race_odds = race_odds.append(odds, ignore_index=True)
#                             #print(res)
#                     except StaleElementReferenceException:
#                         driver.get(url)
#                         race_odds = pd.DataFrame(columns=['odds'])
#                         for bookie in driver.find_elements_by_class_name('odds-grid__cell--odds') :
#                             res = bookie.text
#                             odds = {'odds' : res}
#                             race_odds = race_odds.append(odds, ignore_index=True)
#                             #print(res)
#                 except StaleElementReferenceException:
#                     driver.get(url)
#                     race_odds = pd.DataFrame(columns=['odds'])
#                     for bookie in driver.find_elements_by_class_name('odds-grid__cell--odds') :
#                         res = bookie.text
#                         odds = {'odds' : res}
#                         race_odds = race_odds.append(odds, ignore_index=True)
#                         #print(res)
#                 
#                 # clean odds and add to odds grid
#                 race_odds.odds.replace(to_replace='-',value = np.nan, inplace=True)
#                 race_odds.odds.replace(to_replace='odds',value = np.nan, inplace=True)
#                 race_odds.odds.replace(to_replace='N/A',value = np.nan, inplace=True)
#                 race_odds.odds.replace(to_replace='SP',value = np.nan, inplace=True)
#                 race_odds['odds'] = pd.to_numeric(race_odds.odds)
#                 
#                 left_grid = pd.DataFrame(race_odds[race_odds.index < (len(horse_grid)*len(left_books))])
#                 left_grid = pd.DataFrame(np.reshape(left_grid.values, (len(horse_grid),len(left_books))))
#                 left_grid.columns = left_books
#                 
#                 right_grid = pd.DataFrame(race_odds[race_odds.index >= (len(horse_grid)*len(left_books))])
#                 right_grid = pd.DataFrame(np.reshape(right_grid.values, (len(horse_grid),len(right_books))))
#                 right_grid.columns = right_books
#                 
#                 race_grid = pd.DataFrame()
#                 race_grid[horse_columns] = horse_grid
#                 race_grid[left_books] = left_grid
#                 race_grid[right_books] = right_grid
#                 
#                 odds_grid = odds_grid.append(race_grid, ignore_index=True)
#                 
#         odds_grid['med_odds'] = odds_grid.median(axis = 1)
#         odds_grid.crse_name.replace('Epsom Downs', 'Epsom', inplace=True)
#         feather.write_feather(odds_grid, '../output/' + date.strftime('%Y-%m-%d') + '_atr_odds' + pd.Timestamp.now().strftime('%d-%H-%M') + '.ftr')
#              
#     driver.close()
#     
#     print("tomorrow scraped")
#     print(pd.Timestamp.now())
# =============================================================================
    return
    
#%% body ==================================================
import pyodbc
import pandas as pd
import numpy as np
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
import pyarrow.feather as feather
import schedule
import time
import warnings 
warnings.filterwarnings("ignore") 

schedule.CancelJob

#schedule.every().day.at("11:14").do(atr_today)

schedule.every().day.at("08:00").do(atr_today)
schedule.every().day.at("09:00").do(atr_today)
schedule.every().day.at("10:00").do(atr_today)
schedule.every().day.at("11:00").do(atr_today)
schedule.every().day.at("12:00").do(atr_today)
schedule.every().day.at("13:00").do(atr_today)
schedule.every().day.at("14:00").do(atr_today)
schedule.every().day.at("15:00").do(atr_today)
schedule.every().day.at("16:00").do(atr_today)
schedule.every().day.at("17:00").do(atr_today)
schedule.every().day.at("18:00").do(atr_today)
schedule.every().day.at("19:00").do(atr_today)

schedule.every().day.at("16:00").do(atr_tomorrow)
schedule.every().day.at("17:00").do(atr_tomorrow)
schedule.every().day.at("18:00").do(atr_tomorrow)
schedule.every().day.at("19:00").do(atr_tomorrow)
schedule.every().day.at("20:00").do(atr_tomorrow)
schedule.every().day.at("21:00").do(atr_tomorrow)
schedule.every().day.at("22:00").do(atr_tomorrow)
schedule.every().day.at("23:00").do(atr_tomorrow)

while True :
    schedule.run_pending()
    time.sleep(30)
