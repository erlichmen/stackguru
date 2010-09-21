from google.appengine.ext import db
import globals
import logging
        
class FollowerId(db.Model):
    user = db.IMProperty(required=True)    
    snooze = db.IMProperty(required=False)
    more_search = db.StringProperty(required=False)
    filter_user_rep = db.IntegerProperty(required=False)
    filter_user_rate = db.IntegerProperty(required=False)
    mute = db.BooleanProperty(required=False)
    domain = db.StringProperty(required=False)
    created = db.DateTimeProperty(auto_now_add=True)
    secret = db.StringProperty(required=False)
    @staticmethod
    def create(im_from):
        keyname = str(im_from)
        return FollowerId.get_or_insert(keyname, user = im_from)
    
class Tag(db.Model):
    name = db.StringProperty(required=True)
    domain = db.StringProperty(default=globals.default_domain)
    @staticmethod
    def create(tag):
        keyname = tag
        return Tag.get_or_insert(keyname, name=tag)

class Follower(db.Model):
    follower = db.IMProperty(required=True) 
    tag = db.ReferenceProperty(Tag, required=True)
    mute = db.BooleanProperty(required=False)
    filter_user_rep = db.IntegerProperty(required=False)
    filter_user_rate = db.IntegerProperty(required=False)
    snooze = db.IMProperty(required=False)
    domain = db.StringProperty(required=False)
    created = db.DateTimeProperty(auto_now_add=True)
    @staticmethod
    def create(keyname, db_tab, domain, follower_id):        
        Follower.get_or_insert(keyname,
                                tag=db_tab,
                                follower=follower_id.user,
                                mute=follower_id.mute,
                                filter_user_rep=follower_id.filter_user_rep,
                                filter_user_rate=follower_id.filter_user_rate,
                                domain=domain,
                                snooze=follower_id.snooze)
        
class QuestionsScanner(db.Model):
    last_question = db.IntegerProperty(default=0)

    @staticmethod
    def create(keyname):
        return QuestionsScanner.get_or_insert(keyname)
        
class Question(db.Model):
    end_time = db.DateTimeProperty(required=False)
    last_comment_time = db.DateTimeProperty(auto_now_add=True)
    last_answer_time = db.DateTimeProperty(auto_now_add=True)
    domain = db.StringProperty(required=True) 
    question_id = db.IntegerProperty(required=True)
    title = db.StringProperty(required=False)
    
    @staticmethod 
    def build_keyname(domain, id):
        return "%s_%s" %( id, domain, )
    
    @staticmethod
    def get_by_ids_domain(domain, ids):
        key_names = map(lambda id: Question.build_keyname(domain, id), ids) 
        logging.debug("searching question with key names %s" % (key_names,))
        return Question.get_by_key_name(key_names)
    
    @staticmethod
    def create(question_id, end_time, domain, title):
        keyname = Question.build_keyname(domain, question_id)
        return Question.get_or_insert(keyname, title=title, end_time = end_time, domain=domain, question_id=question_id)
        
class QuestionFollower(db.Model):    
    follower = db.IMProperty(required=True)
    question = db.ReferenceProperty(Question, required=True)  
    @staticmethod
    def create(question, follower):
        keyname = "%s%d%s" % (follower.address, question.question_id,question.domain)
        return QuestionFollower.get_or_insert(keyname, follower = follower, question = question)    