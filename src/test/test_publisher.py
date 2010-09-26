import unittest, logging
from publisher import Publisher, question_url
from entities import Follower2 
from google.appengine.ext import db

class TestPublisher(unittest.TestCase):
    def setUp(self):
        pass

    def test_publish(self):
        def test_get_followers():
            def create_follower(name, domain, tag):
                im = db.IM("xmpp " + name)
                tag_name, matcher = Follower2.tag_without_wildcard(tag)
                return Follower2(follower=im, domain=domain, tag_name=tag_name, matcher=matcher)
                
            yield create_follower("jq_is@mail.com", "mydomain", "jquery")
            yield create_follower("jq_contains@mail.com", "mydomain", "*jquery*")
            yield create_follower("jq_startswith@mail.com", "mydomain", "jquery*")            
            yield create_follower("c#_endswith@mail.com", "mydomain", "*bcl")

        def test_publish(domain, tag_name, subscribers, question_id, title):
            msg = "%s: %s" % (tag_name, question_url(domain, question_id, title))            
            logging.info("sending %s to %s" % (msg, subscribers))

        tags = {}
        
        Publisher._append_tags(tags, {'tags': ['jquery-ui', 'jquery', 'javascript'], 'question_id':1 , 'title': 'title1'})
        Publisher._append_tags(tags, {'tags': ['.net', '.net-bcl'], 'question_id':2 , 'title': 'title2'})
        
        Publisher._publish_tags("mydomain.com", tags, get_followers=test_get_followers, publish=test_publish)
    
if __name__ == '__main__':
    unittest.main()