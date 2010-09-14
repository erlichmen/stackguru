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
    created = db.DateTimeProperty(auto_add_now=True)
    @staticmethod
    def create(im_from):
        keyname = str(im_from)
        if globals.USING_SDK:
            q = FollowerId.get_by_key_name(keyname)
            if not q:
                q = FollowerId(key_name = keyname, user = im_from)
                q.put()
            
            return q
        else:        
            return FollowerId.get_or_insert(keyname, user = im_from) 
    
class Tag(db.Model):
    name = db.StringProperty(required=True)
    domain = db.StringProperty(default=globals.default_domain)
    @staticmethod
    def create(tag):
        keyname = tag
        if globals.USING_SDK:
            q = Tag.get_by_key_name(keyname)
            if not q:
                q = Tag(key_name = keyname, name=tag)
                q.put()
            
            return q
        else:        
            return Tag.get_or_insert(keyname, name=tag) 
    
class Follower(db.Model):    
    follower = db.IMProperty(required=True) 
    tag = db.ReferenceProperty(Tag, required=True)
    mute = db.BooleanProperty(required=False)
    filter_user_rep = db.IntegerProperty(required=False)
    filter_user_rate = db.IntegerProperty(required=False)
    snooze = db.IMProperty(required=False)
    domain = db.StringProperty(required=False)
        
    @staticmethod
    def create(keyname, db_tab, domain, im_from, follower_id):        
        if globals.USING_SDK:
            f = Follower.get_by_key_name(keyname)
            if not f:
                f = Follower(keyname = keyname,
                             tag=db_tab,
                             follower=im_from,
                             mute=follower_id.mute,
                             filter_user_rep=follower_id.filter_user_rep,
                             filter_user_rate=follower_id.filter_user_rate,
                             domain=domain,
                             snooze=follower_id.snooze)
                f.put()
                
            return f
        else:
            Follower.get_or_insert(keyname,
                                   tag=db_tab,
                                   follower=im_from,
                                   mute=follower_id.mute,
                                   filter_user_rep=follower_id.filter_user_rep,
                                   filter_user_rate=follower_id.filter_user_rate,
                                   domain=domain,
                                   snooze=follower_id.snooze)
        
class QuestionsScanner(db.Model):
    last_question = db.IntegerProperty(default=0)

    @staticmethod
    def create(keyname):
        if globals.USING_SDK:
            q = QuestionsScanner.get_by_key_name(keyname)
            if not q:
                q = QuestionsScanner(key_name = keyname)
                q.put()
            
            return q
        else:
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
        if globals.USING_SDK:
            q = Question.get_by_key_name(keyname)
            if not q:
                q = Question(key_name = keyname, title=title, end_time=end_time, domain=domain, question_id=question_id)
                q.put()
            
            return q
        else:
            return Question.get_or_insert(keyname, title=title, end_time = end_time, domain=domain, question_id=question_id)
        
class QuestionFollower(db.Model):    
    follower = db.IMProperty(required=True)
    question = db.ReferenceProperty(Question, required=True)  
    @staticmethod
    def create(question, follower):
        keyname = "%s%d%s" % (follower.address, question.question_id,question.domain)
        if globals.USING_SDK:
            q = QuestionFollower.get_by_key_name(keyname)
            if not q:
                q = QuestionFollower(key_name = keyname, follower = follower, question = question)
                q.put()
            
            return q
        else:
            return QuestionFollower.get_or_insert(keyname, follower = follower, question = question)    