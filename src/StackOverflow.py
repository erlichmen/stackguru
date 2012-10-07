from google.appengine.api import urlfetch
import logging
import json
import guru_globals
import urllib
from google.appengine.api import memcache

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
    def __init__(self, domain = guru_globals.default_domain):
        self.api_version = 2.1
        self.appkey = guru_globals.stack_api_key
        self.domain = domain

    @staticmethod
    def full_domain_name(domain):
        if domain in domain_alias:
            return domain_alias[domain]
        elif domain.find('.') == -1:
            sites = Api.get_cached_sites()
            
            if domain in sites:
                return sites[domain]
            
            return domain + ".stackexchange.com"
        
        return domain
    
    
    @staticmethod
    def get_cached_sites():
        site_names = memcache.get("stack_exchange_sites")
                
        if not site_names:
            sites = StackAuth().sites()
                
            site_names = {}
            for site in sites["api_sites"]:
                site_name = site["name"].lower()
                site_url = site["site_url"].lower()
                if site_url.startswith("http://"):
                    site_url = site_url[7:]
                site_names[site_name] = site_url 
                site_names[site_url] = site_url
                
            # cache for 24 hours
            memcache.set("stack_exchange_sites", site_names, time=60*60*24)
        
        return site_names
    
    @staticmethod
    def is_valid_domain(domain):
        return domain in domain_alias
        
    @staticmethod
    def get_and_validate(domain):
        check_domain = True
        full_domain_name = None
        if domain in domain_alias:
            domain = domain_alias[domain]
            check_domain = False   
        elif domain.find('.') == -1:
            full_domain_name = domain + ".stackexchange.com"
        elif domain.startswith("http://"):
            domain = domain[7:]
             
        if not check_domain:
            return Api(domain)
                                         
        sites = Api.get_cached_sites()
        
        if domain in sites:
            return Api(sites[domain])

        if full_domain_name and full_domain_name in sites:
            return Api(sites[full_domain_name])  
                        
        return None
     
    @staticmethod
    def _csv_ids(ids):
        return "%3B".join(map(lambda id: str(id), ids))
        
    def _fetch(self, command, params = {}, raw_result=False):        
        params_str = "".join(map(lambda p: "&%s=%s" % p, params.iteritems()))
        
        url = "http://api.stackexchange.com/%s/%s?key=%s%s&site=%s" % (self.api_version, command, self.appkey, params_str, self.domain)            
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
            
        return result.get('items', None)        
    
    def question_ansewrs(self, ids, pagesize=100, page=1):        
        result = self._fetch("questions/%s/answers" % (Api._csv_ids(ids),), {'page': page, 'pagesize': pagesize}) 
        if 'items' in result:
            return (result["total"], result['items'])
        
        return (0, [])

    def question_commments(self, ids, pagesize=100, page=1):        
        result = self._fetch("questions/%s/comments" % (Api._csv_ids(ids),), {'page': page, 'pagesize': pagesize}) 
        if 'items' in result:
            return (result["total"], result['items'])
        
        return (0, [])

    def users(self, pagesize=100, page=1):        
        result = self._fetch("users", {'page': page, 'pagesize': pagesize}) 
        if 'items' in result:
            return (result["total"], result['items'])
        
        return (0, [])
    
class StackAuth(Api):
    def __init__(self):
        Api.__init__(self, "stackauth.com")
    
    def get_domain(self):
        return self.domain
    
    def sites(self):
        return self._fetch("sites")