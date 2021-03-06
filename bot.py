import praw
from collections import deque
import re
import json
import os

#Set globals
r=praw.Reddit("PlusBot by /u/captainmeta4")
sub = r.get_subreddit('captainmeta4bots')


class Bot():

    def __init__(self):

        #login
        r.login('PlusBot',os.environ.get('password'))

        #store up to 100 link/author pairs
        self.link_authors = deque([],maxlen=100)

        #get cache of authors and links awarded
        self.author_points = json.loads(r.get_wiki_page(sub,"plusbot").content_md)

    def run(self):
        self.scan_comments()

    def get_OP(self, link_id):

        #first check cache for if we already have this name
        for entry in self.link_authors:
            if entry[0]==link_id:
                return entry[1]
                break

        #then fetch and add it
        else:
            link = r.get_info(thing_id=link_id)
            author = link.author
            if author is None:
                self.link_authors.append((link_id,None))
                return None
            else:
                self.link_authors.append((link_id,author.name))
                return author.name

    def score_class(self, score):

        flair_class = "score-t1"
        if score >=3:
            flair_class = "score-t2"
        if score >=10:
            flair_class = "score-t3"
        if score >=30:
            flair_class = "score-t4"

        return flair_class

        

    def scan_comments(self):

        for comment in praw.helpers.comment_stream(r, "mod", limit=100, verbosity=0):

            #Flair reset
            if comment.author_flair_css_class == "reset":
                score = 0
                if comment.author.name in self.author_points:
                    score = len(self.author_points[comment.subreddit.display_name][comment.author.name])
                flair_class = self.score_class(score)
                flair_text = "+"+str(score)
                r.set_flair(comment.subreddit, comment.author, flair_text=flair_text, flair_css_class = flair_class)
                print('reset flair for /u/'+comment.author.name+' in /r/'+comment.subreddit.display_name)
                continue


            #if comment isn't by OP then we're not interested
            op = self.get_OP(comment.link_id)
            if comment.author.name != op:
                continue

            #if comment doesn't start with a + character then we're not interested
            if not comment.body.startswith("+"):
                continue

            #if comment is top level then we're not interested
            if comment.parent_id == comment.link_id:
                continue

            #get parent comment author
            parent_comment = r.get_info(thing_id = comment.parent_id)

            #make sure user exists
            if parent_comment.author is None:
                continue

            #make sure they are different people
            if parent_comment.author.name == comment.author.name:
                continue

            #add user to authorpoints

            if comment.subreddit.display_name not in self.author_points:
                self.author_points[comment.subreddit.display_name]={}
            if parent_comment.author.name not in self.author_points[comment.subreddit.display_name]:
                self.author_points[comment.subreddit.display_name][parent_comment.author.name]=[]

            #check to see if user has scored this thread
            if comment.link_id in self.author_points[comment.subreddit.display_name][parent_comment.author.name]:
                continue

            #add user to authorpoints
            self.author_points[comment.subreddit.display_name][parent_comment.author.name].append(comment.link_id)

            #get new score and flair text
            score = len(self.author_points[comment.subreddit.display_name][parent_comment.author.name])


            #variables for new flair
            flair_class = self.score_class(score)
            flair_text = "+"+str(score)


            #if user has no flair, or score flair, set new score flair
            if parent_comment.author_flair_css_class is None:
                #save flair to reddit
                r.set_flair(comment.subreddit,parent_comment.author,flair_text = flair_text, flair_css_class = flair_class)

            elif any(x in parent_comment.author_flair_css_class for x in ['score-t1','score-t2','score-t3','score-t4']):
                #save flair to reddit
                r.set_flair(comment.subreddit,parent_comment.author,flair_text = flair_text, flair_css_class = flair_class)

            #save new authorpoints to wiki

            reason = "/u/"+parent_comment.author.name+" has "+flair_text+" in /r/"+comment.subreddit.display_name+" at "+comment.link_id
            r.edit_wiki_page(sub,"plusbot",json.dumps(self.author_points),reason=reason)
            print(parent_comment.author.name+" scored in /r/"+comment.subreddit.display_name)

            

            





if __name__=="__main__":
    bot=Bot()
    bot.run()
