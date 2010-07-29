from google.appengine.api.labs.taskqueue import Task
from datetime import datetime
import logging
from google.appengine.ext import db
import StackOverflow 
from entities import Question
from BeautifulSoup import BeautifulSoup
from markdown import markdown
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.xmpp import send_message
import bitly
import globals
from publisher import safe_title

class AnswerTask(Task):
    @staticmethod
    def create_and_queue(domain, ids, page = 1):
        params = {'ids': ";".join(ids), 'page': page}
        comments_task = Task(url='/answers/%s' % (domain,), params=params)            
        comments_task.add(queue_name="answers")


class CommentTask(Task):
    @staticmethod    
    def create_and_queue(domain, ids, page = 1):
        params = {'ids': ";".join(ids), 'page': page}
        comments_task = Task(url='/comments/%s' % (domain,), params=params)            
        comments_task.add(queue_name="comments")

class ScanNewAnswers(webapp.RequestHandler):
    @staticmethod
    def _answer_url(domain, answer, with_hash = True):
        question = answer['question']
        title = question.title if question.title else str(answer['answer_id'])  
        title = safe_title(title)
        if with_hash:
            return "http://%s/questions/%s/%s/%s#%s" % (domain, answer['question_id'], title, answer['answer_id'], answer['answer_id'],)
        else:
            return "http://%s/questions/%s/%s/%s" % (domain, answer['question_id'], title, answer['answer_id'],)        
        
    def _shorten_answers_urls(self, domain, answers):
        urls = {}
        for answer in answers:
            urls[answer['answer_id']] = ScanNewAnswers._answer_url(domain, answer) 
        
        if len(urls) > 0:
            a = bitly.Api(login = globals.bitly_login, apikey = globals.bitly_api_key)
            short_urls = a.shorten(urls.values())                
            return dict(zip(urls.keys(), short_urls))
        
        return {}
    
    def _notify_answers(self, domain, notify_answers):
        all_answers = []
        for question, answers in notify_answers.iteritems():
            for answer in answers:
                answer['question'] = question
                 
            all_answers.extend(answers)
            
        short_urls = self._shorten_answers_urls(domain, all_answers)
        
        for question in notify_answers:
            answers = notify_answers[question]
            for answer in answers:                    
                owner = answer['owner']
                if 'display_name' in owner:
                    name = owner['display_name']
                else:
                    name = owner['user_id']
                    
                url = short_urls[answer['answer_id']]                         
                
                if 'last_edit_date' in answer:
                    msg = "Answer from %s edited: %s" % (name,  url)
                else:
                    msg = "New answer from %s: %s" % (name,  url)
                
                followers = list(question.questionfollower_set)
                jids = map(lambda follower: follower.follower.address, followers)
                if len(jids) > 0:
                    logging.debug('sending message to %s' % (jids,))            
                    send_message(jids, msg)
                else:
                    logging.debug('no follower')
                
    def _scan(self, domain, ids, page=1, pagesize = 100):        
        api = StackOverflow.Api(domain)
        
        total, answers = api.question_ansewrs(ids, pagesize=pagesize, page=page)
        
        if total > page * pagesize:
            AnswerTask.create_and_queue(ids, page+1)
                    
        question_ids = map(lambda id: int(id), ids)
        values = list(Question.get_by_ids_domain(domain, ids))
        questions = dict(zip(question_ids, values)) 
        questions_update_time = {}
        updated_questions = {}
        notify_answers = {}
        for answer in answers:
            question_id = answer['question_id']
            question = questions[question_id]
            if 'last_edit_date' in answer:
                answer_time_unix = answer['last_edit_date']
            else: 
                answer_time_unix = answer['creation_date']
                
            answer_time = datetime.fromtimestamp(answer_time_unix)
            if not question.last_answer_time or question.last_answer_time < answer_time:                                                                
                if not question_id in questions_update_time or questions_update_time[question_id] < answer_time:
                    questions_update_time[question_id] = answer_time
                    
                if not question_id in updated_questions:
                    updated_questions[question_id] = question
                           
                if not question in notify_answers:
                    notify_answers[question] = []
                     
                notify_answers[question].append(answer)
                            
        for question_id in questions_update_time:
            updated_questions[question_id].last_answer_time = questions_update_time[question_id] 
                
        db.put(updated_questions.values())
        self._notify_answers(api.domain, notify_answers)
            
    def get(self, domain):
        self._scan(domain)

    def post(self, domain):
        ids = self.request.get('ids').split(";")
        page = 1 if not self.request.get('page') else self.request.get('page') 
        self._scan(domain, ids, page)


class ScanNewComments(webapp.RequestHandler):
    @staticmethod
    def _comment_url(domain, comment, with_hash = True):
        if with_hash:
            return "http://%s/questions/%s#comment-%s" % (domain, comment['post_id'], comment['comment_id'], )
        else:
            return "http://%s/questions/%s" % (domain, comment['post_id'], )        
    
    def _shorten_comments(self, domain, comments):
        urls = {}
        for question in comments:
            for comment in comments[question]:
                url = ScanNewComments._comment_url(domain, comment) 
                urls[comment['comment_id']] = url
        
        if len(urls.values()) > 0:
            a = bitly.Api(login = globals.bitly_login, apikey = globals.bitly_api_key)
            short_urls = a.shorten(urls.values())                
            return dict(zip(urls.keys(), short_urls))
        
        return {}
    
    def _notify_comments(self, domain, comments):
        short_urls = self._shorten_comments(domain, comments)
        
        for question in comments:                    
            followers = list(question.questionfollower_set)
            jids = map(lambda follower: follower.follower.address, followers)
            for comment in comments[question]:
                owner = comment['owner']
                if 'display_name' in owner:
                    name = owner['display_name']
                else:
                    name = owner['user_id']
                    
                body = comment['body']
                
                html = markdown(body)
                text = ''.join(BeautifulSoup(html).findAll(text=True))
                
                url = short_urls[comment['comment_id']]                         
                msg = "%s said: %s %s" % (name, text, url)
                if len(jids) > 0:
                    logging.debug('sending message to %s' % (jids,))            
                    send_message(jids, msg)
                else:
                    logging.debug('no follower')

                
    def _scan(self, domain, ids, page=1, pagesize = 100):        
        api = StackOverflow.Api(domain)
        
        total, comments = api.question_commments(ids, pagesize=pagesize, page=page)
        
        if total > page * pagesize:
            CommentTask.create_and_queue(ids, page+1)
        
        logging.debug("scanning questions %s for comments on %s" % (ids, domain,))
        question_ids = map(lambda id: int(id), ids)
        values = list(Question.get_by_ids_domain(domain, ids))
        questions = dict(zip(question_ids, values)) 
        questions_update_time = {}
        updated_questions = {}
        notify_comments = {}
        for comment in comments:
            question_id = comment['post_id']
            question = questions[question_id]
            comment_time_unix = comment['creation_date'] 
            comment_time = datetime.fromtimestamp(comment_time_unix)
            if not question.last_comment_time or question.last_comment_time < comment_time:                                                                
                if not question_id in questions_update_time or questions_update_time[question_id] < comment_time:
                    questions_update_time[question_id] = comment_time
                    
                if not question_id in updated_questions:
                    updated_questions[question_id] = question
                     
                if not question in notify_comments:
                    notify_comments[question] = []
                
                notify_comments[question].append(comment)
                            
        for question_id in questions_update_time:
            updated_questions[question_id].last_comment_time = questions_update_time[question_id] 
                
        db.put(updated_questions.values())
        self._notify_comments(domain, notify_comments)
        
    def get(self, domain):
        self._scan()

    def post(self, domain):
        ids = self.request.get('ids').split(";")
        page = 1 if not self.request.get('page') else self.request.get('page') 
        self._scan(domain, ids, page)
                
class TaskNewComments(webapp.RequestHandler):
    def _scan(self):
        questions = Question.all().order('domain')
        
        index = 0
        
        while True:
            questions_query = questions.fetch(10, index) 
            
            if not questions_query:
                break
            
            questions_list = list(questions_query)
            
            if len(questions_list) == 0:
                break

            domain_ids = {}
            for question in questions_list:
                if not question.domain in domain_ids:
                    domain_ids[question.domain] = []
                
                domain_ids[question.domain].append(str(question.question_id))
            
            for domain in domain_ids:            
                AnswerTask.create_and_queue(domain, domain_ids[domain])
                CommentTask.create_and_queue(domain, domain_ids[domain])
            
            index += 10
                        
    def get(self):
        self._scan()

    def post(self, domain):
        self._scan()
                
application = webapp.WSGIApplication(
                                     [('/tasks/scan_new_comments/', TaskNewComments), 
                                      ('/comments/(.*)', ScanNewComments), 
                                      ('/answers/(.*)', ScanNewAnswers)], 
                                      debug = globals.debug_mode)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()        