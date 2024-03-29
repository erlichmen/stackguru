import guru_globals
import webapp2 
from google.appengine.api import memcache
import random, string

class ShortUrls:
    @staticmethod
    def get_url(token):
        url = memcache.get(token, namespace="shorturls")
        if url is not None:
            return url

    @staticmethod
    def build_full_url(follower_id):
        return "/chrome/%s" % (follower_id.secret)
    
    @staticmethod
    def generate_secret(l=10):
        short_url = ""    
        letters = string.letters + string.digits 
        for _ in range(0, l):
            short_url += random.choice(letters) 
    
        return short_url
                
    @staticmethod
    def build_short_url(follower_id):
        full_url = ShortUrls.build_full_url(follower_id)
        
        short_url = ShortUrls.generate_secret()
        ShortUrls.set_url(short_url, full_url)
        
        return "/c/" + short_url
            
    @staticmethod
    def set_url(token, url):
        #The url will expire after X min
        url = memcache.set(token, url, time=guru_globals.short_url_lifespan, namespace="shorturls")
        if url is not None:
            return url
        
class ShortUrlChromeHandler(webapp2.RequestHandler):
    def get(self, email):
        url = ShortUrls.get_url(email)
        if not url:
            #TODO: better message
            self.response.out.write('Url expired, you need to call the "chrome" command again')
            return
        
        self.redirect(url)

app = webapp2.WSGIApplication([("/c/(.*)", ShortUrlChromeHandler)], debug=guru_globals.debug_mode)
