#!/usr/local/bin/python
# -*- coding: utf-8 -*-
          
from google.appengine.ext import db 
import google.appengine.api.xmpp as xmpp
import webapp2
import logging

def canonical_user(user):
    return user.lower().strip()
    
class UpdateSubscriber(db.Model):
    available = db.BooleanProperty(default=False, indexed=False)
    send_always = db.BooleanProperty(default=False, indexed=False)
    
    @staticmethod
    def create(user):
        user = canonical_user(user)        
        UpdateSubscriber(key_name=user, available = xmpp.get_presence(user)).put()
    
def send_message_to_subscribers(subscribers, body):
    subscribers = [canonical_user(subscriber) for subscriber in subscribers]
    active_subscribers = [subscriber.key().name() for subscriber in UpdateSubscriber.get_by_key_name(subscribers) if subscriber and (subscriber.available or subscriber.send_always)]   
    
    logging.debug('sending to %s ' % str(active_subscribers))
    if active_subscribers:
        xmpp.send_message(active_subscribers, body=body)

class PresenceHandler(webapp2.RequestHandler):
    def post(self, status):
        from_user = self.request.get('from').split('/')[0]
        logging.debug('status %s from %s' % (status, from_user))        
        from_user = canonical_user(from_user)
        subscriber = UpdateSubscriber.get_or_insert(from_user)
        
        subscriber.available = status.startswith('available') 
        subscriber.put()
        logging.debug('user %s available = %s' % (from_user, subscriber.available))
