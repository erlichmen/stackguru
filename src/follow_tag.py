import globals
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from entities import Follower2, QuestionsScanner, InvalidTag
from google.appengine.api import memcache
from gen_utils import FollowHandler, sum_dict, InvalidDomain
import StackOverflow
import urllib

class TooManyTags(Exception):
    pass


def delete_following_tags(user):
    memcache.delete(user.address, namespace="users_tags")

def following_tags(user):
    ids = memcache.get(user.address, namespace="users_tags")
    if not ids:
        tag_following_query = Follower2.gql('where follower=:1', user).fetch(globals.max_follow_tags)
        items = [(tag_follow.domain, tag_follow.full_tag) for tag_follow in tag_following_query]

        ids = {}
        for domain, tag_name in items:
            ids.setdefault(domain, []).append(tag_name)
            
        memcache.set(user.address, ids, namespace="users_tags")
    
    return ids
    
def unfollow_tags_all(follower_id):
    follower_query = Follower2.all().filter('follower', follower_id.user).fetch(globals.max_follow_tags)
    
    delete_following_tags(follower_id.user)
    
    for follower in follower_query:
        yield follower
        
def unfollow_tags(follower_id, tags_per_site):
    follower_query = Follower2.all().filter('follower', follower_id.user).fetch(globals.max_follow_tags)
        
    delete_following_tags(follower_id.user)
    
    remove_items = []
    for domain, tags in tags_per_site.iteritems():
        for tag in tags:
            remove_items.append((StackOverflow.Api.full_domain_name(domain), tag.lower()))
    
    remove_items = frozenset(remove_items)
    
    for follower in follower_query:        
        item = (follower.domain, follower.tag_name.lower()) 
        if item in remove_items:
            yield follower
    
def follow_tags(follower_id, tags_per_site):
    tag_following_query = Follower2.gql('where follower=:1', follower_id.user)
    count = tag_following_query.count() + sum_dict(tags_per_site)  

    if (count >= globals.max_follow_tags):
        raise TooManyTags
                
    for domain, tags in tags_per_site.iteritems():        
        if not StackOverflow.Api.is_valid_domain(domain) and \
            not QuestionsScanner.get_by_domain(domain) and  \
            not StackOverflow.Api.get_and_validate(domain):
                raise InvalidDomain(domain) 
        
        full_domain_name = StackOverflow.Api.full_domain_name(domain)
                     
        Follower2.create_multi(follower_id, full_domain_name, tags)
        
        delete_following_tags(follower_id.user)
                
        scanner = QuestionsScanner.create(full_domain_name)

        yield (scanner.domain, tags)
        
class TagHandler(FollowHandler):
    pass

class FollowTagsHandler(TagHandler):
    def get(self, tag):
        follower_id = self.get_follower_id() 
        if not follower_id:
            return

        domain = self.get_domain(follower_id)
                                
        result = {}
        
        if len(tag) == 0:
            tags = following_tags(follower_id.user)
            result["ids"] = tags[domain] if domain in tags else []
            result["status"] = "success"
        else:
            tag = urllib.unquote(tag).lower()
            msg = ""
            try:            
                for domain, tags in follow_tags(follower_id, {domain: [tag]}):
                    for tag in tags:
                        msg += 'You are now following: "%s" on %s\n' % (tag, domain,)
                
                result["status"] = "success"
            except InvalidDomain, e:
                msg = "Invalid domain %s." % (e.domain)        
                result["status"] = "error"
            except InvalidTag, e:
                msg = "Invalid tag %s." % (e.tag)
                result["status"] = "error"
            except TooManyTags:
                msg = "you follow too much tags, please unfollow some."        
                result["status"] = "error"
                
            result["msg"] = msg
            
        self.handle_result(result)
        
class UnfollowTagsHandler(TagHandler):
    def get(self, tag):
        follower_id = self.get_follower_id() 
        if not follower_id:
            return

        if len(tag) == 0:
            self.response.out.write("missing tag");
            self.response.set_status(401)
            return

        result = {}

        domain = self.get_domain(follower_id)
                
        followers = list(unfollow_tags(follower_id, {domain: [tag]}))

        db.delete(followers)
                
        if len(followers) > 0:
            for follower in followers:
                # TODO: prefetch question                
                result["msg"] = 'You no longer follow \"%s\" on %s' % (follower.tag_name, follower.domain,)
                result["status"] = "success"   
        else:
            result["msg"] = 'You are not following \"%s\" on %s' % (tag, domain,)
            result["status"] = "error"   
            
        self.handle_result(result)
        
application = webapp.WSGIApplication([("/tag/(.*)", FollowTagsHandler), ("/untag/(.*)", UnfollowTagsHandler)], debug=globals.debug_mode)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
