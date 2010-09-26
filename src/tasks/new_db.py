from mapreduce import operation as op
from entities import Follower2, FollowerId 
import globals

def process1(entity):    
    entity.question_id = entity.question.question_id 
    entity.domain = entity.question.domain
    yield op.db.Put(entity)

def process2(entity):    
    entity.tag_name = entity.tag.name
    entity.domain = entity.tag.domain 
    yield op.db.Put(entity)
    
    
def create_follower2(entity):
    follower_id = FollowerId.create(entity.follower)
    
    domain = globals.default_domain if not follower_id.domain else follower_id.domain
        
    follower2 = Follower2(key_name=Follower2.build_key_name(entity.follower, entity.tag_name, domain),
                          follower=entity.follower,
                          matcher=0,
                          mute=entity.mute,
                          tag_name=entity.tag_name,
                          filter_user_rep=entity.filter_user_rep,
                          filter_user_rate=entity.filter_user_rate,
                          domain=domain,
                          snooze=entity.snooze)    
    yield op.db.Put(follower2)
        