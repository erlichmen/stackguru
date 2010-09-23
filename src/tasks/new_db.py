from mapreduce import operation as op

def process1(entity):    
    entity.question_id = entity.question.question_id 
    entity.domain = entity.question.domain
    yield op.db.Put(entity)

def process2(entity):    
    entity.tag_name = entity.tag.name
    entity.domain = entity.tag.domain 
    yield op.db.Put(entity)
    