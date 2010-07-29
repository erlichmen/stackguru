import logging
import StackOverflow 
from google.appengine.api.labs.taskqueue import Task, Queue
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from publisher import Publisher
from entities import QuestionsScanner, Follower
import globals

class ScanNewQuestions(webapp.RequestHandler):
    def _scan(self, domain):
        api = StackOverflow.Api(domain)
        questions = api.questions()
        
        if questions != None:
            settings = QuestionsScanner.get_by_key_name(domain)        
            
            tags = {}
            logging.debug('scanning %d questions on domain %s' % (len(questions), domain, ) )
            for question in questions:
                logging.debug('question: %d' % question['question_id'])
                if  question['question_id'] == settings.last_question:                 
                    break;
                
                logging.info('question: %d is new on %s' % (question['question_id'], domain,))
                
                Publisher._append_tags(tags, question)

            settings.last_question = questions[0]['question_id']
            settings.put() 
    
            Publisher._publish_tags(domain, tags)
        else:
            logging.error('no questions!?')

    def get(self, domain):
        if domain == 'fix':
            q = list(Follower.all())
            for follower in q:
                follower.domain = "stackoverflow.com"
                follower.put()            
        else:
            self._scan(domain)

    def post(self, domain):
        self._scan(domain)
        
class TaskNewQuestions(webapp.RequestHandler):            
    def _queue_tasks(self):
        scanners = QuestionsScanner.all()
        
        tasks = []
        for scanner in scanners:
            domain = scanner.key().name()
            task = Task(url='/tasks/scan_new_questions/%s' % (domain,))  
            tasks.append(task)
        
        if len(tasks) > 0:
            queue = Queue(name="scannewquestions") 
            queue.add(tasks)  
        
    def get(self):
        self._queue_tasks()
        
    def post(self):
        self._queue_tasks()
            
application = webapp.WSGIApplication([('/tasks/scan_new_questions/', TaskNewQuestions), (r'/tasks/scan_new_questions/(.*)', ScanNewQuestions)], debug=globals.debug_mode)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()        