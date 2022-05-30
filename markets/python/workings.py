# -*- coding: utf-8 -*-
"""
Created on Mon May 30 17:53:25 2022

@author: weldo
"""

# Import smtplib for the actual sending function
import smtplib
from email.message import EmailMessage

msg = EmailMessage()
msg.set_content('something happened')
msg['Subject'] = 'URGENT (nah jk)'
msg['From'] = 'scwapers@gmail.com'
msg['To'] = 'scwapers@gmail.com'

server = smtplib.SMTP('smtp.gmail.com',587) #port 465 or 587
server.ehlo()
server.starttls()
server.ehlo()
server.login('scwapers@gmail.com','NU9tpKimbc2ThNH')
server.send_message(msg)
server.close()