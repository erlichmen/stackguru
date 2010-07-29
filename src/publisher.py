import logging
from google.appengine.api.xmpp import send_message
from entities import Tag, Follower

def safe_title(title):
    result = title.lower()
    title = ""
    for ch in result:
        if ch.isalpha() or ch.isdigit():
            title = title + ch
        elif ch.isspace() and len(title) > 1 and title[len(title)-1:1].isspace() == False:
            title = title + " "
            
    title = title.strip()
    title = title.replace(" ", "-")
        
    return title

def question_url(domain, question_id, title):
    return "http://%s/questions/%s/%s" % (domain, question_id, safe_title(title))

class Publisher:
    @staticmethod
    def _publish(domain, tag, followers, questions):
        for question_id, title in questions:
            msg = "%s: %s" % (tag, question_url(domain, question_id, title))
            jids = map(lambda follower: follower.follower.address, followers)
            if len(jids) > 0:
                logging.debug("sending %s to %d followers" % (question_id, len(jids)))            
                send_message(jids, msg)
            else:
                logging.debug("no followers")

    @staticmethod
    def _publish_tags(domain, tags):
        db_tags = Tag.get_by_key_name(tags.keys())
        
        for db_tag in db_tags:
            if not db_tag:
                continue

            logging.debug("tag %s on %s" % (db_tag.name, domain,))
            
            followers = list(Follower.gql('where tag=:1 and mute!=True and domain=:2', db_tag.key(), domain))
            
            if len(followers) == 0:
                logging.debug("no followers")
                continue
                
            Publisher._publish(domain, db_tag.name, followers, tags[db_tag.name]) 

    @staticmethod
    def _append_tags(tags, question):
        if question == None:
            return
        
        if "tags" in question:
            for tag in question["tags"]:
                if not tag in tags:
                    tags[tag] = []                                      
                    tags[tag].append((question['question_id'], question["title"]))