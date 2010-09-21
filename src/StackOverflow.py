from google.appengine.api import urlfetch
import logging
import simplejson as json
import globals
import urllib

domain_alias = {
                'so': 'stackoverflow.com', 
                'sf': 'serverfault.com', 
                'su': 'superuser.com',
                'meta': 'meta.stackoverflow.com',
                'stackoverflow': 'stackoverflow.com', 
                'stackoverflow.com': 'stackoverflow.com',
                'www.stackoverflow.com': 'stackoverflow.com',
                'serverfault': 'serverfault.com', 
                'serverfault.com': 'serverfault.com',
                'www.serverfault.com': 'serverfault.com',
                'superuser': 'superuser.com', 
                'superuser.com': 'superuser.com',
                'www.superuser.com': 'superuser.com',
                'meta.stackoverflow.com': 'meta.stackoverflow.com',
                'stackapps': 'stackapps.com', 
                'stackapps.com': 'stackapps.com',
                'www.stackapps.com': 'stackapps.com',
                }

class Api:    
    def __init__(self, domain = globals.default_domain):
        self.api_version = 1.0
        self.appkey = globals.stack_api_key
        self.domain = domain

    @staticmethod
    def full_domain_name(domain):
        if domain in domain_alias:
            return domain_alias[domain]
        elif domain.find('.') == -1:
            return domain + ".stackexchange.com"
        
        return domain
    
    @staticmethod
    def get_and_validate(domain):
        check_domain = True
        if domain in domain_alias:
            domain = domain_alias[domain]
            check_domain = False   
        elif domain.find('.') == -1:
            domain = domain + ".stackexchange.com"
        
        api = Api(domain)
        if check_domain and not api.is_domain_avaliable():
            return None
    
        return api
     
    @staticmethod
    def _csv_ids(ids):
        return "%3B".join(map(lambda id: str(id), ids))
        
    def _fetch(self, command, params = {}, raw_result=False):        
        params_str = "".join(map(lambda p: "&%s=%s" % p, params.iteritems()))
        
        url = "http://api.%s/%s/%s?key=%s%s" % (self.domain, self.api_version, command, self.appkey, params_str)            
        logging.debug(url)
        respose = urlfetch.fetch(url=url, deadline=10)
        
        if raw_result:
            return respose 
        
        if respose.status_code == 200:
            #logging.debug(respose.content)
            return json.loads(respose.content)
        else:
            raise Exception(respose.status_code)

    def is_domain_avaliable(self):
        try:
            respose = self._fetch("help", raw_result=True)
            if respose.status_code == 200:
                return True
            else:
                return False
        except:
            return False
        
    def search(self, q, pagesize = 5, page=1):
        result = self._fetch("questions", {'intitle': urllib.quote(q), 'pagesize': pagesize, 'page': page})
        
        return result
    
    def questions(self, ids=None, sort = "creation"):        
        if not ids:
            result = self._fetch("questions", {'sort': sort})
        else:
            result = self._fetch("questions/%s" % (Api._csv_ids(ids),))
            
        if 'questions' in result:
            return result['questions']        
        
        return None

    def user(self, id):
        try:
            result = self._fetch("users/%s" % (id,))
        except:
            return None
        
        if 'users' in result:
            return result['users'][0]        
        
        return None

    def user_tags(self, id, page=1):
        result = self._fetch("users/%s/tags" % (id,), {'page': 1}) 
        if 'tags' in result:
            return (result["result"], result['tags'][0])        
        
        return (0, None)

    def system_tags(self, id, page=1):
        result = self._fetch("users/tags", {'page': 1}) 
        if 'tags' in result:
            return (result["result"], result['tags'][0])        
        
        return (0, None)

    def question_ansewrs(self, ids, pagesize=100, page=1):        
        result = self._fetch("questions/%s/answers" % (Api._csv_ids(ids),), {'page': page, 'pagesize': pagesize}) 
        if 'answers' in result:
            return (result["total"], result['answers'])
        
        return [0, None]

    def question_commments(self, ids, pagesize=100, page=1):        
        result = self._fetch("questions/%s/comments" % (Api._csv_ids(ids),), {'page': page, 'pagesize': pagesize}) 
        if 'comments' in result:
            return (result["total"], result['comments'])
        
        return [0, None]

    def users(self, pagesize=100, page=1):        
        result = self._fetch("users", {'page': page, 'pagesize': pagesize}) 
        if 'users' in result:
            return (result["total"], result['users'])
        
        return [0, None]
    
    def question(self, id):        
        result = self._fetch("questions/%s" % (id,)) 
        if 'questions' in result:
            return result['questions'][0]
        
        return None