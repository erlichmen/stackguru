from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.labs.taskqueue import Task
import globals, logging
import StackOverflow
from google.appengine.api.xmpp import send_message

class RankTask(Task):
    @staticmethod
    def create_and_queue(jid, user_id, page_min, page_max, reputation, ttl, domain, page_size, limit, display_name):
        params = {'jid': jid, 'user_id': user_id, 'min': page_min, 'max': page_max, 'reputation': reputation, 'ttl': ttl, 'domain': domain, 'page_size': page_size, 'limit': limit, 'display_name': display_name}
        comments_task = Task(url = '/ranks/', params = params)            
        comments_task.add(queue_name = "ranks")

class RanksHandler(webapp.RequestHandler):
    def post(self):
        domain = self.request.get('domain') 
        
        api = StackOverflow.Api(domain)
        
        ttl = int(self.request.get('ttl')) - 1
        
        user_id = int(self.request.get('user_id'))
        jid = self.request.get('jid')
        
        if ttl == 0:
            msg = "Couldn't find rank of user %s on %s, sorry" % (user_id, domain, )
            send_message([jid], msg)
            return

        limit = int(self.request.get('limit'))
        page_size = int(self.request.get('page_size'))                     
        page_min = int(self.request.get('min'))
        page_max = int(self.request.get('max'))
        mid = (page_min + page_max) / 2
        display_name = self.request.get('display_name')
        reputation = int(self.request.get('reputation'))
        
        logging.debug("'jid': %s, 'user_id': %s, 'min': %s, 'max': %s, 'reputation': %s, 'ttl': %s, 'domain': %s, 'page_size': %s, 'limit': %s, 'display_name': %s" % (jid, user_id, page_min, page_max, reputation, ttl, domain, page_size, limit,display_name))        
        total, users = api.users(pagesize=page_size, page=mid)
        if reputation > users[0]['reputation']:
            page_max = mid - 1        
        elif reputation < users[page_size-1]['reputation']:
            page_min = mid + 1            
        else:
            index = 0
            for user in users:
                index += 1
                if user["user_id"] != user_id:
                    continue
                
                rank = (mid - 1) * page_size + index                
                
                msg = "The rank of %s on %s is %d out of %d users" % (display_name, domain, rank, total)
                send_message([jid], msg)
                return
            
            msg = "Couldn't find rank of user %s on %s, sorry" % (user_id, domain, )
            send_message([jid], msg)
            return
        
        if mid * page_size >= limit:
            msg = "User %s is not in the top %d on %s, I'm giving up" % (user_id, limit, domain, )
            send_message([jid], msg)
            return
            
        RankTask.create_and_queue(jid, user_id, page_min, page_max, reputation, ttl, api.domain, page_size, limit, display_name)

application = webapp.WSGIApplication([('/ranks/', RanksHandler)], debug = globals.debug_mode)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()        