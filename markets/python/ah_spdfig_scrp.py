# -*- coding: utf-8 -*-
"""
Created on Thu Jul 21 21:05:52 2022

@author: Cian

ah_spdfig_scrp.py

this file scrapes andy holding speed figures
"""
#%% funcitons

def log_in(driver) :
    '''logs in to webstie'''
    
    def logged_in(driver) :
        '''checks if logged in using admin bar'''
        try:
            driver.find_element_by_id('wpadminbar')
        except NoSuchElementException:
            return False
        return True

    if logged_in(driver) : return
        
    usr_name = 'Andy Holding'
    pswrd = 'Edward2017'
    
    driver.get('https://andyholdingspeedfigures.co.uk/log-in/')
    driver.find_element_by_id('iump_login_username').send_keys(usr_name)
    driver.find_element_by_id('iump_login_password').send_keys(pswrd)
    driver.find_element_by_name('rememberme').click()
    driver.find_element_by_name('Submit').click()
    
    return


def nav_to_date(driver, date) :
    '''navs to given date using drop down menu'''
    
    if driver.find_element_by_class_name('vdp-datepicker__calendar').get_attribute('style') == 'display: none;' :  driver.find_element_by_id('datepickerid').click()

    mon_yr = driver.find_element_by_class_name('day__month_btn').text
    mon_yr = mon_yr.split(' ')

    while mon_yr[1] != date.strftime('%Y') :
        driver.find_element_by_class_name('prev').click()
        mon_yr = driver.find_element_by_class_name('day__month_btn').text
        mon_yr = mon_yr.split(' ')
        time.sleep(1)
        
    while mon_yr[0] != date.strftime('%b') :
        driver.find_element_by_class_name('prev').click()
        mon_yr = driver.find_element_by_class_name('day__month_btn').text
        mon_yr = mon_yr.split(' ')
        time.sleep(1)
       
    els = driver.find_elements_by_class_name('cell')
    for el in els :
        if el.text == date.strftime('%#d') : el.click()
    
    return

    

#%% main
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
from selenium.common.exceptions import NoSuchElementException  
from selenium.webdriver.support.select import Select
from itertools import islice
import warnings
warnings.filterwarnings("ignore") 

ua = UserAgent()
userAgent = ua.chrome
op = webdriver.ChromeOptions()
#op.add_argument('--headless')
op.add_argument('--window-size=1920x1080')
op.add_argument(f'user-agent={userAgent}')

base_url = 'https://andyholdingspeedfigures.co.uk/'

driver = webdriver.Chrome(options=op)
action = webdriver.ActionChains(driver)
driver.get(base_url)
driver.maximize_window()

log_in(driver)

url = 'https://andyholdingspeedfigures.co.uk/race-search/'
driver.get(url)

date = pd.to_datetime('2016-06-01 00:00:00')

#%%


crses = driver.find_elements_by_class_name('form-control')[1].find_elements_by_xpath('./*')
crses = [x.text for x in crses]
crse_drp = Select(driver.find_elements_by_class_name('form-control')[1])

crse_drp.select_by_index(1)

driver.find_element_by_xpath("//button[text()='Search']").click()

scrp_date = []
scrp_crse = []
race_time = []
pos = []
hrs = []
spdfig = []
jock = []

table_id = driver.find_element_by_class_name('table')
rows = table_id.find_elements_by_tag_name("tr") # get all of the rows in the table
for row in islice(rows, 1, None):
    # Get desired columns        
    scrp_date = scrp_date + [row.find_elements_by_tag_name("td")[0].text]
    scrp_crse = scrp_crse + [row.find_elements_by_tag_name("td")[1].text]
    race_time = race_time + [row.find_elements_by_tag_name("td")[2].text]
    pos = pos + [row.find_elements_by_tag_name("td")[4].text]
    hrs = hrs + [row.find_elements_by_tag_name("td")[5].text]
    spdfig = spdfig + [row.find_elements_by_tag_name("td")[6].text]
    jock = jock + [row.find_elements_by_tag_name("td")[13].text]


#%%
nav_to_date(driver, date)

    #driver.execute_script("arguments[0].style.display = 'grid';", el)

driver.close()
