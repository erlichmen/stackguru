import guru_globals
from google.appengine.api import memcache
import webapp2 
from google.appengine.ext import db
import logging
from datetime import datetime, timedelta
from entities import Question, QuestionFollower
import StackOverflow
from gen_utils import sum_dict, FollowHandler, InvalidDomain

class TooManyQuestions(Exception):
    pass

class InvalidQuestions(Exception):
    def __init__(self, invalid_ids):
        self.invalid_ids = invalid_ids
    def __str__(self):
        return repr(self.invalid_ids)

def delete_following_ids(user):
    memcache.delete(user.address, namespace="users") #@UndefinedVariable
    
def following_ids(user):
    ids = memcache.get(user.address, namespace="users") #@UndefinedVariable
    if not ids:
        following_question_query = QuestionFollower.gql('where follower=:1', user).fetch(guru_globals.max_follow_tags)
        items = [(qf.domain, qf.question_id) for qf in following_question_query]

        ids = {}
        for domain, question_id in items:
            if not domain in ids:
                ids[domain] = []
                
            ids[domain] += [question_id]
            
        memcache.set(user.address, ids, namespace="users") #@UndefinedVariable
    
    return ids

def unfollow_questions_all(follower_id):
    follower_query = QuestionFollower.all().filter('follower', follower_id.user).fetch(guru_globals.max_follow_tags)
    
    delete_following_ids(follower_id.user)
    
    for follower in follower_query:
        yield follower

def unfollow_questions(follower_id, question_ids_per_site):
    follower_query = QuestionFollower.all().filter('follower', follower_id.user).fetch(guru_globals.max_follow_tags)
    
    delete_following_ids(follower_id.user)
    
    remove_items = []
    for domain, questions_id in question_ids_per_site.iteritems():
        for question_id in questions_id:
            remove_items.append((domain, str(question_id)))
    
    remove_items = set(remove_items)

    for follower in follower_query:        
        item = (follower.domain,  str(follower.question_id)) 
        if item in remove_items:
            yield follower  
    
def follow_questions(follower_id, question_ids_per_site):                                
    ids = following_ids(follower_id.user)
    count = sum_dict(ids) + sum_dict(question_ids_per_site)
    if (count >= guru_globals.max_follow_tags):
        raise TooManyQuestions

    delete_following_ids(follower_id.user)

    for domain in question_ids_per_site:
        api = StackOverflow.Api.get_and_validate(domain)
        
        if not api:
            raise InvalidDomain(domain)
        
        question_ids = question_ids_per_site[domain]
        questions = api.questions(question_ids)
        
        valid_questions_ids = map(lambda q: q['question_id'], questions)
        valid_questions_set = set(valid_questions_ids)
        logging.debug("valid questions id %s" % (valid_questions_ids,))        
        left_question_set = set(question_ids) - valid_questions_set
        if len(left_question_set) > 0:
            raise InvalidQuestions(left_question_set)
        
        end_time = datetime.now() + timedelta(days=guru_globals.default_question_scan_lifespan_days)
        for question in questions:
            question_id = question['question_id']
            title = question['title']
            q = Question.create(question_id, end_time, domain, title)  
                
            QuestionFollower.create(q, follower_id.user)
    
        yield (domain, questions)

class QuestionHandler(FollowHandler):
    pass

class UnfollowQuestionHandler(QuestionHandler):
    def get(self, question_id):
        if len(question_id) > 0 and not question_id.isdigit():
            self.response.out.write("invalid question id");
            self.response.set_status(400)
            return None
        
        follower_id = self.get_follower_id() 
        if not follower_id:
            return

        if len(question_id) == 0:
            self.response.out.write("missing question id");
            self.response.set_status(401)
            return
                                
        result = {}
        
        domain = self.get_domain(follower_id)
        
        followers = list(unfollow_questions(follower_id, {domain: [question_id]}))

        db.delete(followers)

        if len(followers) > 0:
            for follower in followers:
                # TODO: prefetch question                                
                result["msg"] = 'You no longer follow \"%s\" on %s' % (follower.question.title, follower.domain,)
                result["status"] = "success"          
        else:
            result["msg"] = 'You are not following \"%s\" on %s' % (question_id, domain,)
            result["status"] = "error"          
            
        self.handle_result(result)
        
class FollowQuestionHandler(QuestionHandler):
    def get(self, question_id):
        if len(question_id) > 0 and not question_id.isdigit():
            self.response.out.write("invalid question id");
            self.response.set_status(400)
            return None
        
        follower_id = self.get_follower_id() 
        if not follower_id:
            return
        
        result = {}
        
        domain = self.get_domain(follower_id)
        
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
            except InvalidDomain, e:
                msg = "Invalid domain %s" % (e.domain)
                result["status"] = "error"
            except InvalidQuestions, e:
                msg = "Invalid question id %s" % (",".join([str(question_id) for question_id in e.invalid_ids]),)
                result["status"] = "error"
            except TooManyQuestions:
                msg = "you follow too much questions, please unfollow some."        
                result["status"] = "error"
                
            result["msg"] = msg
                        
        self.handle_result(result)
        
app = webapp2.WSGIApplication([("/follow/(.*)", FollowQuestionHandler), 
                              ("/unfollow/(.*)", UnfollowQuestionHandler)], 
                             debug=guru_globals.debug_mode)