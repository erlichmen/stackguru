import globals
from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.db import GqlQuery
import logging
from datetime import datetime, timedelta
from entities import Question, QuestionFollower, Follower, Tag, QuestionsScanner
import StackOverflow
import simplejson as json;

class TooManyQuestions(Exception):
    pass

class InvalidQuestions(Exception):
    def __init__(self, invalid_ids):
        self.invalid_ids = invalid_ids
    def __str__(self):
        return repr(self.value)

def sum_dict(d):
    return sum([len(values) for values in d.values()])

def follow_tags(follower_id, tags_per_site):
    tag_following_query = Follower.gql('where follower=:1', follower_id.user)
    count = tag_following_query.count() + sum_dict(tags_per_site)  

    if (count >= globals.max_follow_tags):
        raise TooManyQuestions
                
    for domain in tags_per_site:    
        for tag in tags_per_site[domain]:
            db_tab = Tag.create(tag)
            
            follower_keyname = "%s/%s" % (follower_id.user.address, tag)
    
            Follower.create(follower_keyname,
                            db_tab,
                            domain,
                            follower_id)
        
        QuestionsScanner.create(domain)
        

def delete_following_ids(user):
    memcache.delete(user.address, namespace="users")
    
def following_ids(user):
    ids = memcache.get(user.address, namespace="users")
    if not ids:
        following_question_query = QuestionFollower.gql('where follower=:1', user).fetch(globals.max_follow_tags)
        items = [(qf.question.domain, qf.question.question_id) for qf in following_question_query]

        ids = {}
        for domain, id in items:
            if not domain in ids:
                ids[domain] = []
                
            ids[domain] += [id]
            
        memcache.set(user.address, ids, namespace="users")
    
    return ids
    
def follow_questions(follower_id, question_ids_per_site):                                
    ids = following_ids(follower_id.user)
    count = sum_dict(ids) + sum_dict(question_ids_per_site)
    if (count >= globals.max_follow_tags):
        raise TooManyQuestions

    delete_following_ids(follower_id.user)

    for domain in question_ids_per_site:
        api = StackOverflow.Api.get_and_validate(domain)
        question_ids = question_ids_per_site[domain]
        questions = api.questions(question_ids)
        
        valid_questions_ids = map(lambda q: q['question_id'], questions)
        valid_questions_set = set(valid_questions_ids)
        logging.debug("valid questions id %s" % (valid_questions_ids,))        
        left_question_set = set(question_ids) - valid_questions_set
        if len(left_question_set) > 0:
            raise InvalidQuestions(left_question_set)
        
        end_time = datetime.now() + timedelta(days=1)
        for question in questions:
            question_id = question['question_id']
            title = question['title']
            q = Question.create(question_id, end_time, domain, title)  
                
            QuestionFollower.create(q, follower_id.user)
    
        yield (domain, questions)

class QuestionHandler(webapp.RequestHandler):
    def validate_params(self, question_id):
        if len(question_id) > 0 and not question_id.isdigit():
            self.response.out.write("invalid question id");
            self.response.set_status(400)
            return None
                
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
    
class UnfollowQuestionHandler(QuestionHandler):
    def get(self, question_id):
        follower_id = self.validate_params(question_id) 
        if not follower_id:
            return

        if len(question_id) == 0:
            self.response.out.write("missing question id");
            self.response.set_status(401)
            return
            
        domain = self.request.GET["domain"] if "domain" in self.request.GET else follower_id.default_domain
        domain = globals.default_domain if not domain else domain
                                
        result = {}
        
        follower_query = QuestionFollower.all().filter('follower', follower_id.user).fetch(globals.max_follow_tags)

        for follower in follower_query:
            # TODO: prefetch question
            if str(follower.question.question_id) == question_id and follower.question.domain == domain:
                db.delete(follower)
                delete_following_ids(follower_id.user)                
                result["msg"] = 'You no longer follow \"%s\" on %s' % (follower.question.title, follower.question.domain,)
                result["status"] = "success"          
                break
            
        if 'Origin' in self.request.headers:
            self.response.headers['Access-Control-Allow-Origin'] = self.request.headers['Origin']
            
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(result))
        
class FollowQuestionHandler(QuestionHandler):
    def get(self, question_id):
        follower_id = self.validate_params(question_id) 
        if not follower_id:
            return
        
        domain = self.request.GET["domain"] if "domain" in self.request.GET else follower_id.default_domain
        domain = globals.default_domain if not domain else domain
                                
        result = {}
        
        if len(question_id) == 0:
            ids = following_ids(follower_id.user)
            result["ids"] = ids[domain] if domain in ids else []
            result["status"] = "success"
        else:
            question_id = int(question_id)
            
            msg = ""
            try:            
                for domain, questions in follow_questions(follower_id, {domain: [question_id]}):
                    for question in questions:
                        msg += 'You are now following: "%s" on %s\n' % (question['title'], domain,)
                
                result["status"] = "success"        
            except InvalidQuestions, e:
                msg = "Invalid question id %s" % (",".join([str(id) for id in e.invalid_ids]),)
                result["status"] = "error"
            except TooManyQuestions:
                msg = "you follow too much questions, please unfollow some."        
                result["status"] = "error"
                
            result["msg"] = msg
                        
        if 'Origin' in self.request.headers:
            self.response.headers['Access-Control-Allow-Origin'] = self.request.headers['Origin']

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(result))
        
application = webapp.WSGIApplication([("/follow/(.*)", FollowQuestionHandler), ("/unfollow/(.*)", UnfollowQuestionHandler)], debug=globals.debug_mode)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
