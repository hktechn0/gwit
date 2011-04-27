#-*- coding: utf-8 -*-

'''Implementation of Twitter information and timeline thread control class
'''
 
################################################################################
#
# Copyright (c) 2010 University of Tsukuba Linux User Group
#
# This file is part of "gwit".
#
# "gwit" is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "gwit" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with "gwit".  If not, see <http://www.gnu.org/licenses/>.
#
################################################################################


import sys
import time
import socket
import urllib2
import threading

import twoauth
import twoauth.streaming

# Twitter API Class
class TwitterAPI(object):
    def __init__(self, screen_name, ckey, csecret, atoken, asecret):
        # Generate API Library instance
        self.api = twoauth.api(ckey, csecret, atoken, asecret, screen_name)
        self.sapi = twoauth.streaming.StreamingAPI(self.api.oauth)
        
        self._my_id = -1
        self.my_name = screen_name
        
        self.apilock = threading.Lock()
        
        # User, Status Buffer
        self.users = dict()
        self.statuses = dict()
        self.followers = set()
        self.following = set()
    
    @property
    def my_id(self):
        if self._my_id != -1:
            return self._my_id
        else:
            for user in self.users.itervalues():
                if user.screen_name == self.my_name:
                    self._my_id = user.id
                    return user.id
        
        return -1
    
    @property
    def me(self):
        self.users.get(self.my_id)
    
    def init_twitpic(self, apikey):
        import twoauth.twitpic
        self.twitpic = twoauth.twitpic.Twitpic(self.api.oauth, apikey)
    
    def get_followers_bg(self):
        threading.Thread(target=self.get_followers).start()
    def get_following_bg(self):
        threading.Thread(target=self.get_following).start()
    
    def get_following(self):
        self.following.update([int(i) for i in self.api_wrapper(self.api.friends_ids)])    
    def get_followers(self):
        self.followers.update([int(i) for i in self.api_wrapper(self.api.followers_ids)])
    
    def add_statuses(self, statuses):
        for i in statuses:
            self.add_status(i)
    
    def add_status(self, status):
        self.statuses[status.id] = status
        self.add_user(status.user)
        
        if status.retweeted_status != None:
            self.add_status(status.retweeted_status)
    
    def add_users(self, users):
        if isinstance(users, dict):
            self.users.update(users)
        else:
            self.users.update([(i.id, i) for i in users])
    
    def add_user(self, user):
        self.users[user.id] = user
    
    def get_user_from_screen_name(self, screen_name):
        # search user from screen_name
        for user in self.users.itervalues():
            if user.screen_name == screen_name:
                return user
        
        return None
    
    def get_statuses(self, ids):
        return tuple(self.statuses[i] for i in sorted(tuple(ids), reverse=True))

    def delete_event(self, i):
        if i in self.statuses:
            self.statuses[i]["deleted"] = True
            self.on_tweet_event(i)

    def favorite_event(self, tweet, user):
        if tweet["id"] not in self.statuses:
            self.statuses[tweet["id"]] = tweet
        
        if "faved_by" in self.statuses[tweet["id"]]:
            self.statuses[tweet["id"]]["faved_by"].append(user["id"])
        else:
            self.statuses[tweet["id"]]["faved_by"] = [user["id"]]
        
        self.on_notify_event("@%s favorited your tweet" % user["screen_name"], tweet["text"])
        self.on_tweet_event(tweet["id"])
    
    def api_wrapper(self, method, *args, **kwargs):
        for i in range(3):
            try:
                self.apilock.acquire()
                response = None
                response = method(*args, **kwargs)
                break
            except urllib2.HTTPError, e:
                if e.code == 400:
                    print >>sys.stderr, "[Error] Rate Limitting %s (%s)" % (e, method.func_name)
                    break
                elif e.code == 403:
                    print >>sys.stderr, "[Error] Access Denied %s (%s)" % (e, method.func_name)
                    break
                elif e.code == 404:
                    print >>sys.stderr, "[Error] Not Found %s (%s)" % (e, method.func_name)
                    break
                
                if i >= 3:
                    self.on_twitterapi_error(method, e)
                
                print >>sys.stderr, "[Error] %d: TwitterAPI %s (%s)" % (i, e, method.func_name)
            except socket.timeout:
                print >>sys.stderr, "[Error] %d: TwitterAPI timeout (%s)" % (i, method.func_name)
            except Exception, e:
                print >>sys.stderr, "[Error] %d: TwitterAPI %s (%s)" % (i, e, method.func_name)
            finally:
                self.on_twitterapi_requested()
                self.apilock.release()
            
            time.sleep(1)
        
        return response
    
    def on_twitterapi_error(self, method, e): pass
    def on_twitterapi_requested(self): pass
    def on_tweet_event(self, i): pass
    def on_notify_event(self, title, text, icon): pass
