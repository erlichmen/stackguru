import logging
from google.appengine.api.xmpp import send_message
from entities import Follower2
from algorithms.ahocorasick import AhoCorasick
from time import clock

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
    def _publish_tags(domain, tags, get_followers=None, publish=None):
        
        def group_followers():
            set_tags = {}
            
            for followr in get_followers():
                set_tags.setdefault(followr.tag_name, []).append(followr)

            return set_tags
        
        def gae_get_followers():
            cursor = None
            while True:                
                q = Follower2.gql("where domain=:1 and mute!=TRUE", domain).with_cursor(cursor)
                    
                l = 0
                for followr in q.fetch(1000):
                    l += 1
                    yield followr
                    
                if l < 1000:
                    break
                
                cursor = q.cursor
        
        
        def gae_publish(domain, tag_name, subscribers, question_id, title):            
            if len(subscribers) > 0:
                logging.debug("sending %s to %d followers" % (question_id, len(subscribers)))
                msg = "%s: %s" % (tag_name, question_url(domain, question_id, title))
                send_message(subscribers, msg)
        
        def on_match(which, pos):
            full_tag = tag_names[text_lookup[pos]]
            followers = set_tags[set_tags_keys[which]]
                        
            questions = tags[full_tag]
            
            subscribers = []
            need_publish = False
            for follower in followers:
                if not follower.is_match(full_tag):
                    continue
                                
                subscribers.append(follower)
                need_publish = True
                 
            if need_publish:
                jids = map(lambda follower: follower.follower.address, subscribers)
                
                for question_id, title in questions:
                    current_subscribers = set(jids)
                    prev_subscribers = published_questions.setdefault(question_id, set())                    
                    subscribers = current_subscribers - prev_subscribers  
                    prev_subscribers |= current_subscribers
                                
                    logging.info("publishing %s" % (question_id, ))
                    publish(domain, full_tag, subscribers, question_id, title)   
                    
        if len(tags) == 0:
            logging.info("nothing to publish")
            return
        
        get_followers = get_followers or gae_get_followers
        publish = publish or gae_publish 
        
        start_group_followers = clock()
        set_tags = group_followers()
        logging.info("group followers time %g", clock() - start_group_followers)
                
        set_tags_keys = set_tags.keys()
        start_build_matcher = clock()
        matcher = AhoCorasick(set_tags_keys)
        logging.info("matcher build time %g", clock() - start_build_matcher) 
        
        text_lookup = []
        tag_names = tags.keys()
        logging.info("publishing %d tags to %d tag followers" % (len(tag_names), len(set_tags)))
        published_questions = {}
        for tag_index in range(len(tag_names)):  
            tag_name = tag_names[tag_index]
            text_lookup.extend([tag_index] * len(tag_name))
            text_lookup.append(-1)
        
        text = " ".join(tag_names) 
        
        matcher(text, on_match)
                

    @staticmethod
    def _append_tags(tags, question):
        if question == None:
            return
        
        if "tags" in question:
            for tag in question["tags"]:
                if not tag in tags:
                    tags[tag] = []                                      
                
                tags[tag].append((question['question_id'], question["title"]))