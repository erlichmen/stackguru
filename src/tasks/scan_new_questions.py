import logging
import StackOverflow 
import webapp2
from google.appengine.api.taskqueue import Task, Queue
from publisher import Publisher
from entities import QuestionsScanner
import guru_globals

class ScanNewQuestions(webapp2.RequestHandler):
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
    
            if len(tags) > 0:
                settings.last_question = questions[0]['question_id']
                settings.put() 
                
                Publisher._publish_tags(domain, tags)
            else:
                logging.info('Nothing to publish')
        else:
            logging.error('no questions!?')

    def get(self, domain):
        self._scan(domain)

    def post(self, domain):
        self._scan(domain)
        
class TaskNewQuestions(webapp2.RequestHandler):            
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
            
app = webapp2.WSGIApplication([('/tasks/scan_new_questions', TaskNewQuestions), 
                               ('/tasks/scan_new_questions/(.*)', ScanNewQuestions)], 
                               debug=guru_globals.debug_mode)