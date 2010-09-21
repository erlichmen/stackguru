from google.appengine.api import xmpp
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import xmpp_handlers
import globals
import logging, math
import GoogleSearch
import StackOverflow
from entities import * 
from gen_utils import *
from publisher import question_url
from datetime import datetime
from follow_question import follow_questions, TooManyQuestions, follow_tags, InvalidQuestions, delete_following_ids
from chrome import ShortUrls
            
def get_bare_jid(im_addr):
    pos = im_addr.rfind("/")
    if pos > 0:
        return im_addr[:pos]  
    else:
        return im_addr

class XmppHandler(xmpp_handlers.CommandHandler):
    def _reply_search_result(self, results, message=None):
        for result in results["results"]: 
            message.reply(result["url"])
            
        follower = self._get_current_follower(message)

        if follower != None and "moreResultsUrl" in results:
            msg = "you can can more search results by calling /more"
            message.reply(msg)

            follower.more_search = results["moreResultsUrl"] 
            follower.put()

    def _reply_stackoverflow_search_result(self, domain, results, message=None):
        if 'questions' in results:
            for question in results["questions"]: 
                msg = question_url(domain, question["question_id"], question["title"]) 
                message.reply(msg)
                    
    def text_message(self, message=None):
        if len(message.arg) == 0:
            return

        logging.debug("arg: %s" % (message.arg,))
        logging.debug("body: %s" % (message.body,))
        params = message.arg.split(" ", 1) 
        command = params[0].lower() + "_command"
        method = getattr(self, command, None) 

        if callable(method):
            if len(params) > 1:
                body = params[1]
            else:
                body = ""
            
            new_message = xmpp.Message({'from': message.sender, 'to': message.to, 'body': body})

            method(new_message)
        else: #unknown command 
            message.reply("I don't know how to '%s'" % (params[0], ))

    def search_command(self, message=None):
        """search <text>\nsearch text using stackapps API\nreutrns links to the questions"""
        follower_id = self._get_current_follower(message)
        
        domain = globals.default_domain if not follower_id.domain else follower_id.domain

        api = StackOverflow.Api(domain)
        
        results = api.search(message.arg)
        self._reply_stackoverflow_search_result(domain, results, message)

    def google_command(self, message=None):
        """search <text>\nsearch text using Google custom search\nreutrns links to the questions"""
        follower_id = self._get_current_follower(message)
        
        default_domain = globals.default_domain if not follower_id.domain else follower_id.domain
        
        if default_domain != "stackoverflow.com":
            message.reply("Sorry but the google command works only on the stackoverflow domain")
            return

        api = GoogleSearch.GoogleSearch()        
        
        results = api.search(message.arg)
        self._reply_search_result(results, message)

    def more_command(self, message=None):
        api = GoogleSearch.GoogleSearch()
        
        follower = self._get_current_follower(message)
        
        if follower != None and len(follower.more_search) > 0:
            results = api.search_url(follower.more_search)
            self._reply_search_result(results, message)
        else:
            "No more search result"
                                
    def _get_current_follower(self, message):
        im_from = db.IM("xmpp", get_bare_jid(message.sender))
        return FollowerId.create(im_from)

    def _get_current_followers(self, message):
        im_from = db.IM("xmpp", get_bare_jid(message.sender))
        return Follower.all().filter('follower', im_from)

    def mute_command(self, message=None):
        """mute\n stop questions notifications"""
        logging.debug("mute")
        
        followers = list(self._get_current_followers(message))
        follower_id = self._get_current_follower(message)
        if follower_id:
            follower_id.mute = True 
            followers.append(follower_id)
                        
        if len(followers) > 0:
            for follower in followers:
                follower.mute = True                        
        
            msg = "Enjoy the silence, use /unmute to get notifications again"
        else:
            msg = "You are not following anything there nothing to /mute"
        
        if len(followers) > 0:
            db.put(followers)
            
        message.reply(msg)

    def unmute_command(self, message=None):
        """unmute\nresume questions notifications"""
        logging.debug("unmute")
        followers = list(self._get_current_followers(message))
        follower_id = self._get_current_follower(message)

        if follower_id:
            follower_id.mute = None 
            followers.append(follower_id)

        if len(followers) > 0:
            for follower in followers:
                follower.mute = None
            
                db.put(followers)

            msg = "Unmuted, use /mute to disable notifications"
        else:
            msg = "You are not following anything there nothing to /unmute"

        if len(followers) > 0:
            db.put(followers)
            
        message.reply(msg)
        
    def snooze_command(self, message=None):
        follower = self._get_current_follower(message)
        
        if (follower == None):
            msg = "You don't exist. Go away!"
            message.reply(msg)    
            return
        
        if message.arg == None or message.arg == "on": 
            follower.snooze = datetime.now()
            msg = "You are snoozing, I won't bother you for an hour"            
        elif message.arg == "off":
            follower.snooze = None
            msg = "Snooze off"                
        else:
            msg = "/snooze on/off"            
            
        message.reply(msg)        
        follower.put()
    
    @staticmethod
    def _get_tags(tags):
        return map(lambda tag: tag.strip().lower(), tags.split(','))
        
    def unfollow_command(self, message=None):
        """unfollow <tag>,<question id>...\nstop notifications for specific tags or question ids\nPassing *, all or everything will make you unfollow everything.""" 
        im_from = db.IM("xmpp", get_bare_jid(message.sender))

        key_names = []
        tags = XmppHandler._get_tags(message.arg)
        logging.debug(tags)

        items = []
        followers = []

        if len(tags) == 1 and tags[0].lower() in ('*', 'all', 'everything'):
            question_query = QuestionFollower.all().filter('follower', im_from)
            follower_query = Follower.all().filter('follower', im_from)

            for follower in question_query:
                followers.append(follower)
                items.append(str(follower.question.question_id));

            for follower in follower_query:
                followers.append(follower)
                items.append(follower.tag.name);
                
            delete_following_ids(im_from)
        else:
            for tag in tags:
                key_names.append(tag_to_key_name(tag))

            db_tags = Tag.get_by_key_name(key_names)

            logging.debug(db_tags)

            for db_tag in db_tags:
                if not db_tag:
                    continue

                follower_query = Follower.all().filter('follower', im_from).filter('tag', db_tag.key())
                for follower in follower_query:
                    followers.append(follower)
                    items.append(follower.tag.name)

            follower_query = QuestionFollower.all().filter('follower', im_from).fetch(globals.max_follow_tags)

            for follower in follower_query:
                # TODO: prefetch question
                if str(follower.question.question_id) in key_names:
                    followers.append(follower)
                    items.append(str(follower.question.question_id))                    
                    delete_following_ids(im_from)
                    
        if len(followers) > 0:
            msg = "you are no longer following: %s" % (",".join(items),)
            db.delete(followers)
        else:
            msg = "you are not following %s" % message.arg

        message.reply(msg)

    def _nice_domain_name(self, domain):
        return domain

    def following_command(self, message=None): 
        im_from = db.IM("xmpp", get_bare_jid(message.sender))
        follower_id = self._get_current_follower(message)
        query = Follower.gql('where follower=:1', im_from)
        tags = []

        default_domain = globals.default_domain if not follower_id.domain else follower_id.domain
                
        for follower in query:
            tag = key_name_to_tag(follower.tag.key().name())
            if follower.domain == default_domain: 
                tags.append(tag)
            else:
                tags.append("%s on %s" % (tag, self._nice_domain_name(follower.domain)))
                
        query = QuestionFollower.all().filter('follower', im_from)
        for follower in query:
            tag = str(follower.question.question_id)
            if follower.question.domain == default_domain: 
                tags.append(tag)
            else:
                tags.append("%s on %s" % (tag, self._nice_domain_name(follower.question.domain)))
                 
        if len(tags) > 0:
            msg = "you are following: %s" % (",".join(tags),)     
        else:
            msg = "you are not following any topic"
            
        message.reply(msg)
                        
    def follow_command(self, message=None): 
        """follow <tag>,<question id>...\nget notifications each time a new question is posted on a specific tag\nCalling follow without any parameters will return the topics and questions that you're following.""" 
        if len(message.arg) == 0:
            self.following_command(message)
            return
                    
        follower_id = self._get_current_follower(message)
                        
        tags = XmppHandler._get_tags(message.arg)
        logging.debug(tags)
        question_tags = {}
        actual_tags = {}
        domain = globals.default_domain if not follower_id.domain else follower_id.domain
        for tag in tags:        
            if tag.isdigit() == False:
                logging.debug("following tag %s on %s" % (tag,domain,))

                if not domain in actual_tags:
                    actual_tags[domain] = []
                                
                actual_tags[domain].append(tag)
            else:
                logging.debug("tag %s might be a question tag" % (tag,))
                if not domain in question_tags:
                    question_tags[domain] = []
                    
                question_tags[domain].append(int(tag))            
                    
        logging.debug("actual tags %s" % (actual_tags,))
        logging.debug("question tags %s" % (question_tags,))

        if len(actual_tags) > 0:
            try:
                follow_tags(follower_id, actual_tags)
                
                if len(actual_tags) > 1:
                    msg = "OK! I will let you know once a question on those topics is asked"
                    message.reply(msg)
                elif len(actual_tags) == 1:
                    msg = "OK! I will let you know once a question on this topic is asked"            
                    message.reply(msg)
            except TooManyQuestions:
                msg = "you follow too much tags, please /unfollow some."        
                message.reply(msg)
                return                
            
        if len(question_tags) > 0:
            self.follow_questions(message, follower_id, question_tags)
                
    def follow_questions(self, message, follower_id, question_tags):
        msg = ""
        try:
            default_domain = globals.default_domain if not follower_id.domain else follower_id.domain
            
            for domain, questions in follow_questions(follower_id, question_tags):
                for question in questions:
                    if default_domain == domain:
                        msg += 'You are now following: "%s"\n' % (question['title'],) 
                    else:
                        msg += 'You are now following: "%s" on %s\n' % (question['title'],domain,)            
        except InvalidQuestions, e:
            if len(e.invalid_ids) == 1: 
                msg = "Invalid question id %s" % (",".join([str(id) for id in e.invalid_ids]),)
            else:
                msg = "Invalid question ids %s" % (",".join([str(id) for id in e.invalid_ids]),)                                    
        except TooManyQuestions:
            msg = "you follow too much questions, please /unfollow some."        

        message.reply(msg)                
        
    def filter_command(self, message=None):
        pass
    
    def rank_command(self, message=None):
        """rank <user id>\nCalculates the rank of user id, limited to the top 10000 users"""
        
        if len(message.arg) == 0:
            msg = "rank [user id]"
            message.reply(msg)
            return
        
        follower_id = self._get_current_follower(message)
        
        domain = globals.default_domain if not follower_id.domain else follower_id.domain
        
        user_id = message.arg
        api = StackOverflow.Api(domain)
        user = api.user(user_id)
        
        if not user:
            msg = "No such user on %s" % (domain, )
            message.reply(msg)
            return
        
        page_size = globals.ranks_page_size
        limit = globals.ranks_limit
        
        user_id = int(user_id)
        total, _ = api.users(pagesize=page_size)
        max_pages = int(math.ceil(total / page_size))
        total_pages = min(max_pages, limit / page_size) 
        
        page_min = 1
        page_max = total_pages
        reputation = user['reputation']
        ttl = int(math.log(min(total, limit) / page_size) * 1.5)
        
        from ranks import RankTask
        
        RankTask.create_and_queue(message.sender, int(user_id), page_min, page_max, reputation, ttl, domain, page_size, limit, user['display_name'])
            
        msg = "Calculating the rank of %s, this might take some time..." % (user['display_name'],)
        message.reply(msg)
    
    
    def domain_command(self, message=None):
        """domain <domain or alias> Set the active domain on which the bot commands will work."""
        follower = self._get_current_follower(message)
                
        if len(message.arg) == 0:
            domain = globals.default_domain if not follower.domain else follower.domain
            msg = "Your default domain is %s" % (domain,)
            message.reply(msg)
            return
                
        domain = message.arg.strip().lower()
        
        api = StackOverflow.Api.get_and_validate(domain)
                
        if not api:
            msg = "Invalid domain"
        else:
            follower.domain = domain
            follower.put() 
            msg = "Your new default domain is now %s" % (domain,)
            
        message.reply(msg)
        
    def question_command(self, message=None):
        if len(message.arg) == 0:
            msg = "question [question id]"
            message.reply(msg)
            return

        follower_id = self._get_current_follower(message)
        
        default_domain = globals.default_domain if not follower_id.domain else follower_id.domain

        question_id = message.arg
                        
        self.follow_questions(message, follower_id, {default_domain: [question_id]})
                            

    def help_command(self, message=None):
        if len(message.arg) == 0: 
            methodList = [method for method in dir(self) if callable(getattr(self, method)) and method.endswith("_command")]
            methods = []
            logging.debug(methods)
            for method in methodList:
                doc = getattr(self, method).__doc__           
                if doc:
                    methods.append(method[:len(method) - 8])
                
            methods.remove('unhandled')
            msg = "Available commands:\n%s\n /help <command name> for more info" % ("\n".join(methods))
            message.reply(msg)
        else:
            attr = getattr(self, message.arg + "_command", None)
            if not attr:
                msg = "Unknown command"
                message.reply(msg)
                return
            
            doc = attr.__doc__
            if not doc:
                msg = "Unknown command"
                message.reply(msg)
                return
            
            message.reply(doc)
      
    def chrome_command(self, message=None): 
        domain = self.request.url[:self.request.url.find(self.request.path)]
        follower_id = self._get_current_follower(message)
        if not follower_id.secret: 
            follower_id.secret = ShortUrls.generate_secret()
            follower_id.put()
        
        short_url = ShortUrls.build_short_url(follower_id)
                    
        msg = "Click this link to install the Chrome extension %s%s" % (domain, short_url, )
        message.reply(msg)

      
application = webapp.WSGIApplication([('/_ah/xmpp/message/chat/', XmppHandler)], debug=globals.debug_mode)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
