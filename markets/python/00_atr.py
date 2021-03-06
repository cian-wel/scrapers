# -*- coding: utf-8 -*-
"""
Created on Sun Apr 17 21:05:49 2022

@author: weldo

00_atr.py

this file scrapes price data from atr for today's races

"""
#%% todo
# log exceptions


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

def get_horses(driver, crse_races, k) :
    horse_grid=pd.DataFrame(columns = ['crse_name', 'race_datetime', 'horse_name'])
    for horse in driver.find_elements_by_class_name('odds-grid-horse__name'):
        res = horse.text
        horse_odds = {'crse_name':crse_races.crse_name[k],
                  'race_datetime':crse_races.race_datetime[k],
                  'horse_name':res}
        horse_grid = horse_grid.append(horse_odds, ignore_index=True)
        
    return horse_grid

def get_odds(driver, crse_races) :
    race_odds = pd.DataFrame(columns=['odds'])
    for bookie in driver.find_elements_by_class_name('odds-grid__cell--odds') :
        res = bookie.text
        odds = {'odds' : res}
        race_odds = race_odds.append(odds, ignore_index=True)
        
    return race_odds

def atr_first(driver, slp) :
    driver.maximize_window()
    time.sleep(slp)
    try :
        driver.find_element_by_xpath("//span[text()='AGREE']").click()
    except :
        pass
    #driver.find_element_by_xpath('//*/div[4]/div[1]/aside/div/ul/li[1]/label').click()
    driver.find_element_by_xpath("//label[text()='Show all runners in odds grid']").click()
    driver.find_element_by_xpath('//*/div[4]/div[1]/aside/div/ul/li[3]/label').click()
    
    return driver

def get_horses_odds(driver, crse_races, k, horse_grid, url) :
    try:
        try :
            horse_grid = get_horses(driver, crse_races, k)
        except Exception:
            driver.get(url)
            horse_grid = get_horses(driver, crse_races, k)
    except Exception:
        driver.get(url)
        horse_grid = get_horses(driver, crse_races, k)
    
    # get odds
    try:
        try :
            race_odds = get_odds(driver, crse_races)
        except Exception:
            driver.get(url)
            race_odds = get_odds(driver, crse_races)
    except Exception:
        driver.get(url)
        race_odds = get_odds(driver, crse_races)
    
    return race_odds, horse_grid

def odds_grid_shape(race_odds, horse_grid, race_grid, left_books, right_books, horse_columns, odds_grid) :
    
    # clean odds and add to odds grid
    race_odds.odds.replace(to_replace='-',value = np.nan, inplace=True)
    race_odds.odds.replace(to_replace='odds',value = np.nan, inplace=True)
    race_odds.odds.replace(to_replace='N/A',value = np.nan, inplace=True)
    race_odds.odds.replace(to_replace='SP',value = np.nan, inplace=True)
    
    for i in range(len(race_odds.odds)) :
        if type(race_odds.odds[i]) == str :
            if '/' in race_odds.odds[i] :
                price = race_odds.odds[i].split('/')
                price = (int(price[0]) / int(price[1])) + 1
                race_odds.loc[i, 'odds'] = price
                
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
    
    return odds_grid

def gen_atr(fut_runners) :
    
    base_url = 'https://www.attheraces.com/racecard/'
    left_books = ['bet365', 'will_hill', 'lads', 'pp', 'coral', 'unibet', 'sport888', 'betfairsb', 'sts', 'tote']
    right_books = ['betfred', 'betvictor', 'bet10', 'boylesports', 'parimatch', 'betway', 'fansbet', 'grosvenor', 'spreadex', 'skybet', 'quinnbet', 'matchbook', 'smarkets', 'bfex']

    horse_columns = ['crse_name', 'race_datetime', 'horse_name']
    grid_columns = []
    grid_columns.extend(horse_columns)
    grid_columns.extend(left_books)
    grid_columns.extend(right_books)
    race_grid = pd.DataFrame(columns=grid_columns)
    horse_grid = pd.DataFrame(columns=horse_columns)
    odds_grid = pd.DataFrame(columns=horse_columns)
    
    ua = UserAgent()
    userAgent = ua.chrome
    op = webdriver.ChromeOptions()
    op.add_argument('--headless')
    op.add_argument('--window-size=1920x1080')
    op.add_argument(f'user-agent={userAgent}')
    driver = webdriver.Chrome(options=op)
    first = True
    
    fut_runners.crse_name.replace('Epsom', 'Epsom Downs', inplace=True)
    fut_crses = fut_runners.drop_duplicates(subset='crse_name').drop(columns=['race_id', 'horse_id', 'horse_name']).reset_index(drop=True)
    fut_crses['adj_crse_name'] = fut_crses.crse_name.replace(' ', '-', regex=True)
    fut_crses['date'] = fut_crses.race_datetime.dt.date

    # scrape
    crses = fut_crses.reset_index(drop=True)
    for j in crses.index :
        driver.close()
        driver = webdriver.Chrome(options=op)
        first = True
        crse_races = fut_runners[fut_runners.crse_name == crses.crse_name[j]].drop_duplicates(subset='race_id').reset_index(drop=True)
        for k in crse_races.index :
            horse_grid = pd.DataFrame(columns=horse_columns)
            
            url = base_url + crses.adj_crse_name[j] + '/' + crses.date[j].strftime(format='%d-%B-%Y') + '/' + crse_races.race_datetime[k].strftime(format='%H%M')
            print(url)
            try :
                driver.get(url)
            except :
                driver.get(url)
            
            if first :
                atr_first(driver, 5)
                first = False
            try :
                race_odds, horse_grid = get_horses_odds(driver, crse_races, k, horse_grid, url)
                odds_grid = odds_grid_shape(race_odds, horse_grid, race_grid, left_books, right_books, horse_columns, odds_grid)
            except :
                race_odds, horse_grid = get_horses_odds(driver, crse_races, k, horse_grid, url)
                odds_grid = odds_grid_shape(race_odds, horse_grid, race_grid, left_books, right_books, horse_columns, odds_grid)
                
    odds_grid['med_odds'] = odds_grid.median(axis = 1)
    odds_grid.crse_name.replace('Epsom Downs', 'Epsom', inplace=True)
    
    driver.close()
    
    globals()['i'] = 0
    
    return odds_grid
    
#%% today function
def atr_today() :
    
    date = pd.Timestamp.now()
    runners = proform_import()
    fut_runners = runners
    fut_runners = runners[(runners.race_datetime > date) & (runners.race_datetime < (date.normalize() + pd.DateOffset(days=1)))]
    if len(fut_runners) > 0 :
        
        odds_grid = gen_atr(fut_runners)
        odds_grid['scrape'] = 'today'
        odds_grid['timestamp'] = pd.Timestamp.now()
        feather.write_feather(odds_grid, '../output/' + date.strftime('%Y-%m-%d') + '_atr_odds' + pd.Timestamp.now().strftime('%d-%H-%M') + '.ftr')
    
    print("today scraped")
    print(pd.Timestamp.now())
    
    global sched_ran
    sched_ran = True
    return
    
#%% scrape tomorrow
def atr_tomorrow() :
    
    date = pd.Timestamp.now().normalize() + pd.DateOffset(days=1)
    runners = proform_import()
    fut_runners = runners
    fut_runners = runners[(runners.race_datetime > date) & (runners.race_datetime < (date.normalize() + pd.DateOffset(days=1)))]
    if len(fut_runners) > 0 :
        
        odds_grid = gen_atr(fut_runners)
        odds_grid['scrape'] = 'today'
        odds_grid['timestamp'] = pd.Timestamp.now()
        feather.write_feather(odds_grid, '../output/' + date.strftime('%Y-%m-%d') + '_atr_odds' + pd.Timestamp.now().strftime('%d-%H-%M') + '.ftr')
    
    print("tomorrow scraped")
    print(pd.Timestamp.now())
    
    global sched_ran 
    sched_ran = True
    return

def atr_180min(runners) :
    runners = runners[((runners.race_datetime - pd.DateOffset(minutes=180)) < (pd.Timestamp.now() + pd.DateOffset(minutes=1))) & ((runners.race_datetime - pd.DateOffset(minutes=180)) > (pd.Timestamp.now() - pd.DateOffset(minutes=1)))]
    if len(runners) > 0 :
        odds_grid = gen_atr(runners)
        odds_grid['scrape'] = '180 min'
        odds_grid['timestamp'] = pd.Timestamp.now()
        feather.write_feather(odds_grid, '../output/' + pd.Timestamp.now().strftime('%Y-%m-%d') + '_atr_180_odds' + pd.Timestamp.now().strftime('%d-%H-%M') + '.ftr')
        print("180 min scraped")
        print(pd.Timestamp.now())
        print()
        
    return

def atr_120min(runners) :
    runners = runners[((runners.race_datetime - pd.DateOffset(minutes=120)) < (pd.Timestamp.now() + pd.DateOffset(minutes=1))) & ((runners.race_datetime - pd.DateOffset(minutes=120)) > (pd.Timestamp.now() - pd.DateOffset(minutes=1)))]
    if len(runners) > 0 :
        odds_grid = gen_atr(runners)
        odds_grid['scrape'] = '120 min'
        odds_grid['timestamp'] = pd.Timestamp.now()
        feather.write_feather(odds_grid, '../output/' + pd.Timestamp.now().strftime('%Y-%m-%d') + '_atr_120_odds' + pd.Timestamp.now().strftime('%d-%H-%M') + '.ftr')
        print("120 min scraped")
        print(pd.Timestamp.now())
        print()
        
    return

def atr_090min(runners) :
    runners = runners[((runners.race_datetime - pd.DateOffset(minutes=90)) < (pd.Timestamp.now() + pd.DateOffset(minutes=1))) & ((runners.race_datetime - pd.DateOffset(minutes=90)) > (pd.Timestamp.now() - pd.DateOffset(minutes=1)))]
    if len(runners) > 0 :
        odds_grid = gen_atr(runners)
        odds_grid['scrape'] = '90 min'
        odds_grid['timestamp'] = pd.Timestamp.now()
        feather.write_feather(odds_grid, '../output/' + pd.Timestamp.now().strftime('%Y-%m-%d') + '_atr_090_odds' + pd.Timestamp.now().strftime('%d-%H-%M') + '.ftr')
        print("90 min scraped")
        print(pd.Timestamp.now())
        print()
        
    return

def atr_060min(runners) :
    runners = runners[((runners.race_datetime - pd.DateOffset(minutes=60)) < (pd.Timestamp.now() + pd.DateOffset(minutes=1))) & ((runners.race_datetime - pd.DateOffset(minutes=60)) > (pd.Timestamp.now() - pd.DateOffset(minutes=1)))]
    if len(runners) > 0 :
        odds_grid = gen_atr(runners)
        odds_grid['scrape'] = '60 min'
        odds_grid['timestamp'] = pd.Timestamp.now()
        feather.write_feather(odds_grid, '../output/' + pd.Timestamp.now().strftime('%Y-%m-%d') + '_atr_060_odds' + pd.Timestamp.now().strftime('%d-%H-%M') + '.ftr')
        print("60 min scraped")
        print(pd.Timestamp.now())
        print()
        
    return

def atr_030min(runners) :
    runners = runners[((runners.race_datetime - pd.DateOffset(minutes=30)) < (pd.Timestamp.now() + pd.DateOffset(minutes=1))) & ((runners.race_datetime - pd.DateOffset(minutes=30)) > (pd.Timestamp.now() - pd.DateOffset(minutes=1)))]
    if len(runners) > 0 :
        odds_grid = gen_atr(runners)
        odds_grid['scrape'] = '30 min'
        odds_grid['timestamp'] = pd.Timestamp.now()
        feather.write_feather(odds_grid, '../output/' + pd.Timestamp.now().strftime('%Y-%m-%d') + '_atr_030_odds' + pd.Timestamp.now().strftime('%d-%H-%M') + '.ftr')
        print("30 min scraped")
        print(pd.Timestamp.now())
        print()

    return

def atr_020min(runners) :
    runners = runners[((runners.race_datetime - pd.DateOffset(minutes=20)) < (pd.Timestamp.now() + pd.DateOffset(minutes=1))) & ((runners.race_datetime - pd.DateOffset(minutes=20)) > (pd.Timestamp.now() - pd.DateOffset(minutes=1)))]
    if len(runners) > 0 :
        odds_grid = gen_atr(runners)
        odds_grid['scrape'] = '20 min'
        odds_grid['timestamp'] = pd.Timestamp.now()
        feather.write_feather(odds_grid, '../output/' + pd.Timestamp.now().strftime('%Y-%m-%d') + '_atr_020_odds' + pd.Timestamp.now().strftime('%d-%H-%M') + '.ftr')
        print("20 min scraped")
        print(pd.Timestamp.now())
        print()
        
    return

def atr_010min(runners) :
    runners = runners[((runners.race_datetime - pd.DateOffset(minutes=10)) < (pd.Timestamp.now() + pd.DateOffset(minutes=1))) & ((runners.race_datetime - pd.DateOffset(minutes=10)) > (pd.Timestamp.now() - pd.DateOffset(minutes=1)))]
    if len(runners) > 0 :
        odds_grid = gen_atr(runners)
        odds_grid['scrape'] = '10 min'
        odds_grid['timestamp'] = pd.Timestamp.now()
        feather.write_feather(odds_grid, '../output/' + pd.Timestamp.now().strftime('%Y-%m-%d') + '_atr_010_odds' + pd.Timestamp.now().strftime('%d-%H-%M') + '.ftr')
        print("10 min scraped")
        print(pd.Timestamp.now())
        print()
        
    return

def atr_005min(runners) :
    runners = runners[((runners.race_datetime - pd.DateOffset(minutes=5)) < (pd.Timestamp.now() + pd.DateOffset(minutes=1))) & ((runners.race_datetime - pd.DateOffset(minutes=5)) > (pd.Timestamp.now() - pd.DateOffset(minutes=1)))]
    if len(runners) > 0 :
        odds_grid = gen_atr(runners)
        odds_grid['scrape'] = '5 min'
        odds_grid['timestamp'] = pd.Timestamp.now()
        feather.write_feather(odds_grid, '../output/' + pd.Timestamp.now().strftime('%Y-%m-%d') + '_atr_005_odds' + pd.Timestamp.now().strftime('%d-%H-%M') + '.ftr')
        print("5 min scraped")
        print(pd.Timestamp.now())
        print()
        
    return

def main(schedule) :
    runners = proform_import()

    while True :
        
        sched_ran = False
        
        if runners.race_datetime.dt.date.min() < pd.Timestamp.now().normalize() :
            runners = proform_import()
        
        atr_180min(runners)
        atr_120min(runners)
        atr_090min(runners)
        atr_060min(runners)
        atr_030min(runners)
        atr_020min(runners)
        atr_010min(runners)
        atr_005min(runners)
        schedule.run_pending()
        if ~sched_ran :
            time.sleep(45)
    
    return
     
#%% body ==================================================
import pyodbc
import pandas as pd
import numpy as np
from selenium import webdriver
import pyarrow.feather as feather
import schedule
import time
from fake_useragent import UserAgent
import smtplib
from email.message import EmailMessage
import warnings 
warnings.filterwarnings("ignore") 

schedule.clear()

atr_today()

schedule.every().day.at("07:30").do(atr_today)
schedule.every().day.at("08:00").do(atr_today)
schedule.every().day.at("08:30").do(atr_today)
schedule.every().day.at("09:00").do(atr_today)
schedule.every().day.at("09:30").do(atr_today)
schedule.every().day.at("10:00").do(atr_today)
schedule.every().day.at("10:30").do(atr_today)

schedule.every().day.at("11:00").do(atr_today)
schedule.every().day.at("11:30").do(atr_today)
schedule.every().day.at("12:00").do(atr_today)

schedule.every().day.at("16:00").do(atr_tomorrow)
schedule.every().day.at("18:00").do(atr_tomorrow)
schedule.every().day.at("19:00").do(atr_tomorrow)
schedule.every().day.at("20:00").do(atr_tomorrow)
schedule.every().day.at("21:00").do(atr_tomorrow)
schedule.every().day.at("23:00").do(atr_tomorrow)

globals()['i'] = 0

msg = EmailMessage()
msg.set_content('scraper re-started')
msg['Subject'] = 'ATR scraper'
msg['From'] = 'weldonci@tcd.ie'
msg['To'] = 'scwapers@gmail.com'

server = smtplib.SMTP('smtp.gmail.com',587) #port 465 or 587
server.ehlo()
server.starttls()
server.ehlo()
server.login('weldonci@tcd.ie','o$o@74tS')
server.send_message(msg)
server.close()

while True :
    
    try :
        main(schedule)
        
    except Exception as e:
        globals()['i'] = globals()['i']+1
        time.sleep(30)
        if globals()['i'] >1 :
            time.sleep(30)
            if  globals()['i'] > 3 :
                time.sleep(30)
                if globals()['i'] > 10 :
                    
                    msg = EmailMessage()
                    msg.set_content('Scraper stopped after ' + str(globals()['i']) + ' consecutive times with exception:\n' + str(e))
                    msg['Subject'] = '**URGENT** ATR SCRAPER STOPPED'
                    msg['From'] = 'weldonci@tcd.ie'
                    msg['To'] = 'scwapers@gmail.com'
                    
                    server = smtplib.SMTP('smtp.gmail.com',587) #port 465 or 587
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login('weldonci@tcd.ie','o$o@74tS')
                    server.send_message(msg)
                    server.close()
                
                    break
        print(globals()['i'])
        pass
    
