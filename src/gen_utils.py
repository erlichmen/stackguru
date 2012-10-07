from google.appengine.ext.db import GqlQuery
import webapp2
from google.appengine.api import memcache
import json
import StackOverflow, guru_globals

def tag_to_key_name(tag):
    return tag.replace("*", "__WC__")

def key_name_to_tag(tag):
    return tag.replace("__WC__", "*")

def sum_dict(d):
    return sum([len(values) for values in d.values()])

class InvalidDomain(Exception):
    def __init__(self, domain):
        self.domain = domain
    def __str__(self):
        return repr(self.domain)

class FollowHandler(webapp2.RequestHandler):
    def handle_result(self, result):
        if not result:
            return
        
        if 'Origin' in self.request.headers:
            self.response.headers['Access-Control-Allow-Origin'] = self.request.headers['Origin']
            
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(result))
    
    def get_domain(self, follower_id):
        domain = self.request.GET["domain"] if "domain" in self.request.GET else follower_id.default_domain
        domain = guru_globals.default_domain if not domain else domain
        return StackOverflow.Api.full_domain_name(domain)
        
    def get_follower_id(self):
        token = self.request.GET["token"] if "token" in self.request.GET else None
        
        if not token:
            self.response.out.write("token missing");
            self.response.set_status(401)
            return None

        follower_id = memcache.get(token, namespace="tokens")
        if not follower_id:
            query = GqlQuery("SELECT * FROM FollowerId WHERE secret = :1", token).fetch(1)
                    
            if len(query) == 0:
                self.response.out.write("invalid token");
                self.response.set_status(401)
                return
        
            follower_id = query[0]
            
            memcache.set(token, follower_id, namespace="tokens")

        return follower_id
    
    
def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]    