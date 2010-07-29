import globals
from google.appengine.api import urlfetch
import logging
import simplejson as json
import urllib

class GoogleSearch:
    def search(self, q):
        q = urllib.quote(q)
        url = ('http://ajax.googleapis.com/ajax/services/search/web?v=1.0&q=%s&key=%s&cx=001464108856017723352:kdxkhliydge' % (q, globals.google_api_key))
        
        logging.debug(url)
        
        return self.search_url(url)
        
    def search_url(self, url):
        respose = urlfetch.fetch(url=url, headers={'Referer': "userzeroooo.appspot.com"})
                       
        if respose.status_code == 200:
            logging.debug(respose.content)
            return json.loads(respose.content)["responseData"]
        
        raise Exception(respose.status_code)
                