from google.appengine.ext import db
import logging
import StackOverflow

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

class InvalidTag(Exception):
    def __init__(self, tag):
        self.tag = tag
    def __str__(self):
        return repr(self.tag)


class Tag(db.Model):
    pass

class Follower(db.Model):
    follower = db.IMProperty(required=True) 
    tag = db.ReferenceProperty(Tag, required=True)
    mute = db.BooleanProperty(required=False)
    filter_user_rep = db.IntegerProperty(required=False)
    filter_user_rate = db.IntegerProperty(required=False)
    snooze = db.IMProperty(required=False)
    domain = db.StringProperty(required=False)
    created = db.DateTimeProperty(auto_now_add=True)
    tag_name = db.StringProperty(required=False)    
    @staticmethod
    def create(keyname, db_tag, domain, follower_id):        
        Follower.get_or_insert(keyname,
                                tag=db_tag,
                                follower=follower_id.user,
                                mute=follower_id.mute,
                                tag_name=db_tag.tag.name,
                                filter_user_rep=follower_id.filter_user_rep,
                                filter_user_rate=follower_id.filter_user_rate,
                                domain=domain,
                                snooze=follower_id.snooze)

class Follower2(db.Model):
    follower = db.IMProperty(required=True) 
    mute = db.BooleanProperty(required=False)
    filter_user_rep = db.IntegerProperty(required=False)
    filter_user_rate = db.IntegerProperty(required=False)
    snooze = db.IMProperty(required=False)
    domain = db.StringProperty(required=False)
    created = db.DateTimeProperty(auto_now_add=True)
    tag_name = db.StringProperty(required=False)
    #0 is, 1 contains, 2 startswith, 3 endswith
    matcher = db.IntegerProperty(required=False, default=0)
    
    @staticmethod
    def build_key_name(user, tag_name, domain):
        return "%s/%s/%s" % (user.address.lower(), tag_name.lower(), domain.lower())
    
    @staticmethod
    def create(follower_id, domain, tag_name):        
        tag_name = tag_name.lower()
        
        tag_name, matcher = Follower2.tag_without_wildcard(tag_name) 
        key_name = Follower2.build_key_name(follower_id.user, tag_name, domain)
                    
        def txn(*args, **kwds):
            logging.info("creating follow tag %s" % (key_name, ))
            entity = Follower2.get_by_key_name(key_name)
            if not entity:
                entity = Follower2(key_name=key_name, **kwds)
            else:
                entity.matcher = kwds.get('matcher')
            entity.put()
            return entity
        
        return db.run_in_transaction(txn, 
                                follower=follower_id.user,
                                matcher=matcher,
                                mute=follower_id.mute,
                                tag_name=tag_name,
                                filter_user_rep=follower_id.filter_user_rep,
                                filter_user_rate=follower_id.filter_user_rate,
                                domain=domain,
                                snooze=follower_id.snooze)
                
    @staticmethod
    def create_multi(follower_id, domain, tags):
        for tag in tags:
            if not Follower2.is_valid_tag(tag):
                raise InvalidTag(tag)  

        for tag in tags:
            Follower2.create(follower_id, domain, tag)
        
    @property
    def full_tag(self):
        return Follower2.tag_with_wildcard(self.tag_name, self.matcher)
   
    @staticmethod
    def tag_with_wildcard(tag, matcher):
        if matcher == 0: #is
            return tag
        elif matcher == 1: #contains
            return "*" + tag + "*"
        elif matcher == 2: #startswith
            return tag + "*"
        elif matcher == 3: #endswith
            return "*" + tag
        
        return tag
    
    @staticmethod
    def is_valid_tag(tag):
        if tag.find('*', 1, -1) > 0: 
            return False
    
        if len(tag.strip('*')) < 2:
            return False
    
        return True
    
    def is_match(self, full_tag):
        if self.matcher == 0: #is
            return self.tag_name == full_tag
        elif self.matcher == 1: #contains
            return full_tag.index(self.tag_name) >= 0 
        elif self.matcher == 2: #startswith
            return full_tag.startswith(self.tag_name)
        elif self.matcher == 3: #endswith
            return full_tag.endswith(self.tag_name)
    
        return False
    
    @staticmethod
    def tag_without_wildcard(tag):
        if tag.find('*') < 0:
            return (tag, 0) #is
        elif tag[0] == '*' and tag[-1] == '*':
            return (tag[1:-1], 1) #contains
        elif tag[-1] == '*':
            return (tag[:-1], 2) #startswith
        elif tag[0] == '*':
            return (tag[1:], 3) #endswith
        
        return None
        
        
class QuestionsScanner(db.Model):
    last_question = db.IntegerProperty(default=0)

    @property
    def domain(self):
        return self.key().name()
    
    @staticmethod
    def create(domain):
        full_domain_name = StackOverflow.Api.full_domain_name(domain)
                    
        return QuestionsScanner.get_or_insert(full_domain_name)
        
    @staticmethod
    def get_by_domain(domain):
        full_domain_name = StackOverflow.Api.full_domain_name(domain)
        return QuestionsScanner.get_by_key_name(full_domain_name)
    
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
    question = db.ReferenceProperty(Question, required=True, collection_name="followers")
    domain = db.StringProperty(required=False) 
    question_id = db.IntegerProperty(required=False)
    created = db.DateTimeProperty(auto_now_add=True)
    
    @staticmethod
    def create(question, follower):
        keyname = "%s%d%s" % (follower.address, question.question_id,question.domain)
        return QuestionFollower.get_or_insert(keyname, follower = follower, question = question, question_id = question.question_id, domain = question.domain)