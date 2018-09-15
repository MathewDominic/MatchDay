import os
import json
import time
import logging
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from config import constants
from utils import initLogging

API_KEY = constants['SPORTSMONK_API_KEY']
cred = credentials.Certificate(os.path.expanduser('~/matchday-firebase-firebase-adminsdk-83hhc-40b0ae1594.json'))
firebase_admin.initialize_app(cred)
db = firestore.Client()



if __name__ == '__main__':
    initLogging(logging.INFO, filename=os.path.expanduser('~/logs/start_match.log'))
    matches = list(db.collection('matches')
                   .where(u'timestamp', u'<', int(time.time()) * 1000).where(u'started', u'==', False))
