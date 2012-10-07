import webapp2
from google.appengine.ext import db

import guru_globals
from entities import QuestionFollower, Question
from datetime import datetime, timedelta

class TaskDeleteOldQuestionsFollow(webapp2.RequestHandler):
    def get(self):
        two_weeks_ago = datetime.now() - timedelta(days=guru_globals.default_question_scan_lifespan_days)
        old_questions_followers = QuestionFollower.all().filter('created < ', two_weeks_ago)
        db.delete(old_questions_followers)

        old_questions = Question.all().filter('end_time < ', datetime.now())
        db.delete(old_questions)

app = webapp2.WSGIApplication([('/tasks/delete_old_questions_follow', TaskDeleteOldQuestionsFollow)], 
                                      debug = guru_globals.debug_mode)