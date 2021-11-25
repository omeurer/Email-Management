#Librairies
import smtplib, sys, imaplib, os, email
from pandas import DataFrame, Series
from email.header import Header, decode_header, make_header
import matplotlib.pyplot as plt
import datetime
import pandas as pd
import time
import numpy as np

my_email=os.environ.get('google_mail')
password=os.environ.get('google_psw')

imap = imaplib.IMAP4_SSL("imap.gmail.com", port=993)

#To know the exact names of your mailbox kinds. 
for i in imap.list()[1]:
    l = i.decode().split(' "/" ')
    print(l[0] + " = " + l[1])

mailbox_selection='Inbox'

# Mail connection
def mailbox_connection():

    """ The function returns the list of all emails. """
    fromStr=''
    subjectStr=''

    status,msgs=imap.select(mailbox_selection)  
    print('The status for the mailbox selection is :' + status)

    if status=='OK':
        typ, data=imap.uid('search',None,'ALL')
    
    #Count the number of messages
        msgList=data[0].split()
        numMsg=len(msgList)
        print('Total %s messages in mailbox' %str(numMsg))
    return msgList

mailbox_connection()


# Generate the df.
def mails_to_df(percFirstMail=0.4): #
    #Set up a dictionary to hold the data
    subjectDict={}
    fromDict={}
    dateDict={}
    
    imap.noop() #refreshes the connection. After it, the server logs out automatically after 30 minutes. 
    
    time_duration = 29*60 # the loop to store mails will finish before the 30 minutes. Otherwise, we loose connection. 
    time_start = time.time() #current second
  
    messages=mailbox_connection() #list of mails id. 
    lenMailbox=len(messages)

    i=np.floor(percFirstMail*lenMailbox) # the num of the mail you begin with.

    while (time.time() < time_start + time_duration) & (i<lenMailbox): #before 29 minutes and until we stored the maximum of emails.

        num=messages[i]
        rv, data = imap.uid('fetch',num,'(RFC822)')

        if rv != 'OK':
            print("ERROR getting message: ", num)

        if data[0] is not None:

            msg = email.message_from_bytes(data[0][1])
            fromStr=make_header(decode_header(msg['From']))
            fromStr=str(fromStr)
            fromDict[num]=fromStr

            date=msg['Date']
            dateDict[num]=date

            if msg['Subject']: #if the message has a subject. 

                subjectStr=str(make_header(decode_header(msg['Subject'])))
                subjectStr=str(subjectStr)
                print ('Message: %s, Subject: %s Date: %s' %(num, subjectStr, str(msg['Date'])))

            else: 

                subjectStr=''
                print ('From:', fromStr) 
            
            i+=1
            
        subjectDict[num]=subjectStr 
        
    imap.noop()    

    Subjects, Froms , Dates = subjectDict,fromDict, dateDict
    msgDict={'Subject':Subjects,'From':Froms, 'Date':dateDict}
    df=DataFrame(msgDict)
    
    print('\n')
    print(len(df)/len(mailbox_connection())*100, '% of the mailbox has been stored in "msgData" for a duration of', (time.time()-time_start)/60, "minutes.")

    
    return df

msgData=mails_to_df() #the df

#Get a clean df with the message id, the subject, the expeditor and the email address and the good date format. 
def cleanDf(dataframe):

    """ It allows us to separate the name from the address in the df. """

    address_list=[]
    from_list=[]
    date_list=[]

    df=dataframe.copy()
    df.dropna(how='any',inplace=True)
    df.reset_index(inplace=True)
    

    len1=len("Mon, 4 Aug 2008 21:09:52 +0000 (GMT)")
    len2=len("Mon, 21 Aug 2008 21:09:52 +0000 (GMT)")
    len3=len("Wed, 26 Jul 2017 12:11:31 +0200 (CEST)")
    len8=len("Thu, 07 Nov 2019 14:58:13 GMT")

    len9=len("Tue,  2 Jun 2020 18:17:24 +0000 (UTC)")

    len4=len("Mon, 4 Aug 2008 21:09:52 +0000")
    len5=len("Mon, 21 Aug 2008 21:09:52 +0000")

    len6=len("4 Sep 2019 10:42:52 -0400") 
    len7=len("11 Sep 2019 10:42:52 -0400")

    for i in df.From: #for the address : we extrat the name of expeditor and the email address. 
        
        if '<' in i:
            pos1=i.find('<')
            pos2=i.find('>')

            expeditor=i[:pos1]
            address=i[pos1+1:pos2]

            address_list.append(address)
            from_list.append(expeditor)

        else:
            address_list.append(i)
            from_list.append(i)

    for i in df.Date: #to get the date. In each header, we have ±XXXX (GMT) or (PDT), but the type can differ. 
        
        if len(i) in [len1,len2,len4,len5,len8]:
            pos1=i.find(',')
            pos2=i.find(':')
            
            dateFormat=i[pos1+2:pos2-3]
            date_list.append(dateFormat)

        elif len(i) in [len6,len7]:
            pos=i.find(':')
            
            dateFormat=i[pos-18:pos-3]
            date_list.append(dateFormat)

        elif len(i) in [len3,len9]:

            if i[5]==' ':
                pos1=i.find(',')
                pos2=i.find(':')

                dateFormat=i[pos1+3:pos2-3]
                date_list.append(dateFormat)

            elif i[5]!=' ':
                pos1=i.find(',')
                pos2=i.find(':')

                dateFormat=i[pos1+2:pos2-3]
                date_list.append(dateFormat)

        else:
            print(i)

    df['Address']=address_list
    df['From']=from_list
    df['Date']=date_list
    df['Date']= pd.to_datetime(df['Date'],errors='coerce', format='%d %b %Y')
    
    return df


cleanMsgData=cleanDf(msgData)

trashFolderName="Trash"

# Transfer selected mail to the trash folder
def transferFiles(deleteSeries):

    count=0

    for i in range(len(deleteSeries)):

        uid=deleteSeries.index[i]
        rv, data = imap.uid('COPY',uid,trashFolderName) # we copy the mail in the trash folder
        print ('The status for copying', uid,' to the trash is :' + rv)

        if rv != 'OK':
            print("ERROR getting message: ", uid)

        else: 
            print('moving msg %s' %uid)
            count+=1
            mov, data = imap.uid('STORE', uid , '+FLAGS', '(\\Deleted)') #This deletes for ever the mail. To copy it in the trash is not the same thing. 
            print ('The status for deleting', uid,' is :' + mov)
            print('\n')
            imap.expunge()
            
    print( count, "emails have been removed.")
    print('\n')
    return count


listToSuppress=['firstMail@mail.com',
'secondMail@mail.com']

## transfer mail according to specific criteria. 
def transferCriteria(timeDelta=30): #All mails before 30 days. 

    """ This function will transfer all mails which are dated before the delta time and for the specific list instancied before"""

    today = datetime.date.today()
    lastMonth = today - datetime.timedelta(days=timeDelta)
    date=lastMonth.strftime("%d-%b-%Y") #the date of last month's same day, because timeDelta=30. 

    count=0 #number of mail deleted. 

    for exped in listToSuppress:
        
        print(exped)
        print('\n')

        try: 

            status, messages_id_list = imap.uid('search', None, 'BEFORE', date ,'FROM' , exped) 
            print ('The status for these search criterion is :' + status)
            print('\n')

            messages = messages_id_list[0].split() #convert the string ids to list of email ids
            print(messages)
            print('\n')

            for uid in messages:
                rv, data = imap.uid('COPY',uid,trashFolderName)
                print ('The status for copying', uid,'to the trash is :' + rv)
                if rv != 'OK':
                    print("ERROR getting message: ", uid)
                else: 
                    print('moving msg %s' %uid)
                    mov, data = imap.uid('STORE', uid , '+FLAGS', '(\\Deleted)')
                    print ('The status for deleting', uid,' is :' + status)
                    count+=1
                    print('\n')
                    imap.expunge()

        except:
            print('The procedure did not succeed.')
    print("In total,", count, 'mails have been removed. It is about', count*10, 'grams of CO2 avoided by year.')

count=transferCriteria()

#Send email
from smtplib import SMTP_SSL, SMTP_SSL_PORT


SMTP_HOST = 'smtp.gmail.com' #for google
SMTP_USER=os.environ['google_mail']
SMTP_PASS=password=os.environ['google_psw'] #the password of your api key (2-SV)


# Craft the email by hand
from_email = SMTP_USER  
to_emails = [SMTP_USER] 
body = 'You just erased ' + str(count) + ' mails from your '+ my_email + ' mailbox, which represents ' + str(10*count) + 'grams of C02 avoided by year. The top senders are ' +  str(cleanMsgData['Address'].value_counts()[:25])
headers = f"From: {from_email}\r\n"
headers += f"To: {', '.join(to_emails)}\r\n" 
headers += f"Subject: Hello\r\n"
email_message = headers + "\r\n" + body  # Blank line needed between headers and body

# Connect, authenticate, and send mail
smtp_server = SMTP_SSL(SMTP_HOST, port=SMTP_SSL_PORT)
smtp_server.set_debuglevel(1)  # Show SMTP server interactions
smtp_server.login(SMTP_USER, SMTP_PASS)
smtp_server.sendmail(from_email, to_emails, email_message)

# Disconnect
smtp_server.quit()