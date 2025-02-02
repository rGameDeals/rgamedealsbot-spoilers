import sqlite3
import time
import praw
import prawcore
import requests
import os
import datetime
import logging
import re
import dateparser
import yaml
import pymysql
import schedule

os.environ['TZ'] = 'UTC'

REDDIT_CID=os.environ['REDDIT_CID']
REDDIT_SECRET=os.environ['REDDIT_SECRET']
REDDIT_USER = os.environ['REDDIT_USER']
REDDIT_PASS = os.environ['REDDIT_PASS']
REDDIT_SUBREDDIT= os.environ['REDDIT_SUBREDDIT']
AGENT="python:rGameDeals-response:2.0b (by dgc1980)"

reddit = praw.Reddit(client_id=REDDIT_CID,
                     client_secret=REDDIT_SECRET,
                     password=REDDIT_PASS,
                     user_agent=AGENT,
                     username=REDDIT_USER)
subreddit = reddit.subreddit(REDDIT_SUBREDDIT)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%m-%d %H:%M')

logging.info("scanning spoiler...")

def runspoiler(postlimit):
 con = pymysql.connect(
    host=os.environ['MYSQL_HOST'],
    user=os.environ['MYSQL_USER'],
    passwd=os.environ['MYSQL_PASS'],
    db=os.environ['MYSQL_DB']
 )
 try:
  for submission in subreddit.new(limit=postlimit):
    con.ping(reconnect=True)
    if submission.link_flair_text is not None:
      flair = submission.link_flair_text.lower()
    else:
      flair = ""
    isflair = False


    try:
      if flair.index('expired') > -1:
        isflair = True
    except ValueError:
      pass
    allowsend =0

    #if 1 == 0:
    if len(submission.all_awardings) > 0 :
      #print("has awards")

      cursorObj = con.cursor()
      cursorObj.execute('SELECT * FROM awards WHERE postid = "'+submission.id+'"')
      rows = cursorObj.fetchall()
      if len(rows) != 0:
        # already has awards
        if rows[0][2] < len(submission.all_awardings):
          logging.info("found more awards on :" + submission.id)
          cursorObj.execute('UPDATE awards SET counted = %s WHERE postid = %s', (len(submission.all_awardings),submission.id)  )
          con.commit()
          has_gild = ""
          for award in submission.all_awardings:
            print( "Award......: " + award['name'] )
            if award['name'] == "Silver":
              has_gild = "** Silver/Gold/Plat found **"
            if award['name'] == "Gold":
              has_gild = "** Silver/Gold/Plat found **"
            if award['name'] == "Platinum":
              has_gild = "** Silver/Gold/Plat found **"

            if award['name'] != "Silver" and award['name'] != "Gold" and award['name'] != "Platinum" and award['name'] != "[deleted]":
              allowsend = 1

          if allowsend == 1:
            reddit.subreddit('modgamedeals').message('Post Awards Again', 'There has been an Award found on https://new.reddit.com/r/GameDeals/comments/' + submission.id)
            #reddit.subreddit('gamedeals').message('Post Awards Again', 'There has been an Award found on https://new.reddit.com/r/GameDeals/comments/' + submission.id + '\n\n' + has_gild)
      else:
        #first time
        logging.info("found awards on :" + submission.id)
        cursorObj.execute('INSERT INTO awards(postid, counted) VALUES(%s, %s)', (submission.id, 1)  )
        con.commit()
        has_gild = ""
        for award in submission.all_awardings:
          if award['name'] == "Silver":
            has_gild = "** Silver/Gold/Plat found **"
          if award['name'] == "Gold":
            has_gild = "** Silver/Gold/Plat found **"
          if award['name'] == "Platinum":
            has_gild = "** Silver/Gold/Plat found **"
          if award['name'] != "Silver" and award['name'] != "Gold" and award['name'] != "Platinum" and award['name'] != "[deleted]":
            allowsend = 1

        if allowsend == 1:
          #reddit.subreddit('gamedeals').message('Post Awards', 'There has been an Award found on https://new.reddit.com/r/GameDeals/comments/' + submission.id + '\n\n' + has_gild)
          reddit.subreddit('modgamedeals').message('Post Awards', 'There has been an Award found on https://new.reddit.com/r/GameDeals/comments/' + submission.id)


    if submission.spoiler and not isflair :
      if not isflair and flair != "":
        flairtime = str( int(time.time()))
        cursorObj = con.cursor()
        cursorObj.execute('INSERT INTO flairs(postid, flairtext, timeset) VALUES(%s,%s,%s)', (submission.id,submission.link_flair_text,flairtime)  )
        con.commit()
      #if submission.mod.flair != "":
      #  submission.mod.flair(text='Expired: ' + submission.mod.flair, css_class='expired')
      #else
      #  submission.mod.flair(text='Expired', css_class='expired')
      submission.mod.flair(text='Expired', css_class='expired')

      logging.info("flairing spoiled post of " + submission.title)
    elif not submission.spoiler and isflair:
      submission.mod.flair(text='')
      logging.info("unflairing spoiled post of " + submission.title)
      cursorObj = con.cursor()
      cursorObj.execute('SELECT * FROM flairs WHERE postid = "'+submission.id+'"')
      rows = cursorObj.fetchall()
      if len(rows) != 0 and rows[0][2] != "Expired":
        cursorObj.execute('DELETE FROM flairs WHERE postid = "'+submission.id+'"')
        submission.mod.flair(text=rows[0][2], css_class='')
    time.sleep(5)

 except (prawcore.exceptions.RequestException, prawcore.exceptions.ResponseException):
        logging.info("Error connecting to reddit servers. Retrying in 1 minute...")
        time.sleep(60)

 except praw.exceptions.APIException:
        logging.info("Rate limited, waiting 5 seconds")
 except:
        logging.info("Unknown Error connecting to reddit servers. Retrying in 1 minute...")
        time.sleep(60)

 con.close()

schedule.every(5).minutes.do(runspoiler, 50)
schedule.every(1).hours.do(runspoiler, 200)

runspoiler(10)

while 1:
#  try:
    schedule.run_pending()
    time.sleep(1)

#  except:
#    time.sleep(10)
