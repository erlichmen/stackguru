import globals
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
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
        url = memcache.set(token, url, time=60*10, namespace="shorturls")
        if url is not None:
            return url
        
class ShortUrlChromeHandler(webapp.RequestHandler):
    def get(self, email):
        url = ShortUrls.get_url(email)
        if not url:
            #TODO: better message
            self.response.out.write('Url expired, you need to call the "chrome" command again')
            return
        
        self.redirect(url)

application = webapp.WSGIApplication([("/c/(.*)", ShortUrlChromeHandler)], debug=globals.debug_mode)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
        