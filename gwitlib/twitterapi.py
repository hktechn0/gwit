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

from twittertools import TwitterTools

# Twitter API Class
class TwitterAPI(object):
    def __init__(self, screen_name, ckey, csecret, atoken, asecret):
        # set timeout
        socket.setdefaulttimeout(90)
        
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
        self.configuration = dict()
    
    @property
    def my_id(self):
        if self._my_id != -1:
            return self._my_id
        else:
            for user in self.users.values():
                if user.screen_name == self.my_name:
                    self._my_id = user.id
                    return user.id
        
        return -1
    
    @property
    def me(self):
        self.users.get(self.my_id)
    
    def update_configuration_bg(self):
        threading.Thread(
            target = self.update_configuration).start()
    
    def update_configuration(self):
        for _ in range(5):
            conf = self.api_wrapper(self.api.help_configuration)
            if conf:
                self.configuration = conf
                break
    
    def get_followers_bg(self):
        threading.Thread(target = self.get_followers).start()
    def get_following_bg(self):
        threading.Thread(target = self.get_following).start()
    
    def get_following(self):
        newset = set()
        cursor = -1
        
        while cursor != 0:
            r = self.api_wrapper(self.api.friends_ids, cursor = cursor) or {}
            newset.update([int(i) for i in r.get("ids", [])])
            cursor = r.get("next_cursor", 0)
        
        self.following = newset
    
    def get_followers(self):
        newset = set()
        cursor = -1
        
        while cursor != 0:
            r = self.api_wrapper(self.api.followers_ids, cursor = cursor) or {}
            newset.update([int(i) for i in r.get("ids", [])])
            cursor = r.get("next_cursor", 0)
        
        self.followers = newset
    
    def add_statuses(self, statuses):
        if isinstance(statuses, dict):
            map(self.add_status, statuses.iteritems())
        elif statuses:
            map(self.add_status, statuses)
    
    def add_status(self, status, overwrite = True):
        found = status.id in self.statuses
        if overwrite or not found:
            # fix: twitter api response is broken?
            if found: status.retweeted = self.statuses[status.id].retweeted
            self.statuses[status.id] = status
        
        self.add_user(status.user)
        status["user"] = self.users[status.user.id]
        
        if status.retweeted_status:
            self.add_status(status.retweeted_status, overwrite = False)
            status["retweeted_status"] = self.statuses[status.retweeted_status.id]
    
    def add_users(self, users):
        if isinstance(users, dict):
            map(self.add_user, users.itervalues())
        elif users:
            map(self.add_user, users)
    
    def add_user(self, user):
        self.users[user.id] = user
    
    def get_user_from_screen_name(self, screen_name):
        # search user from screen_name
        for user in self.users.values():
            if user.screen_name == screen_name:
                return user
        
        return None
    
    def get_statuses(self, ids):
        return tuple(
            self.statuses[i] for i in sorted(tuple(ids), reverse=True))
    
    def destory_tweet(self, status):
        threading.Thread(
            target = self._destroy_tweet_in_thread, args = [status,]).start()
    
    def _destroy_tweet_in_thread(self, status):
        self.api_wrapper(self.api.status_destroy, status.id)
        status["deleted"] = True
        if TwitterTools.isretweet(status):
            self.statuses[status.retweeted_status.id]["retweeted"] = False
    
    def delete_event(self, i):
        if i in self.statuses:
            self.statuses[i]["deleted"] = True
            self.on_tweet_event(i)
    
    def favorite_event(self, status, user):
        status.favorited = False # fix
        self.add_status(status, overwrite = False)
        self.add_user(user)
        
        if user.id == self.my_id:
            self.statuses[status.id].favorited = True
        else:
            self.on_notify_event("@%s favorited tweet" % user.screen_name, 
                                 "@%s: %s" % (status.user.screen_name,
                                              status.text),
                                 user)
        
        if "faved_by" in self.statuses[status.id]:
            self.statuses[status.id]["faved_by"].add(user.id)
        else:
            self.statuses[status.id]["faved_by"] = set([user.id])
        
        self.on_tweet_event(status.id)
    
    def unfavorite_event(self, status, user):
        status.favorited = False # fix
        self.add_status(status, overwrite = False)
        self.add_user(user)
        
        if user.id == self.my_id:
            self.statuses[status.id].favorited = False
        else:
            self.on_notify_event("@%s unfavorited tweet" % user.screen_name, 
                                 "@%s: %s" % (status.user.screen_name,
                                              status.text),
                                 user)
        
        if "faved_by" in self.statuses[status.id]:
            try:
                self.statuses[status.id]["faved_by"].remove(user.id)
            except KeyError:
                pass
        
        self.on_tweet_event(status.id)
    
    def follow_event(self, source, target):
        self.add_users((source, target))
        
        if source.id == self.my_id:
            self.followers.add(source.id)
        else:
            self.following.add(source.id)
            self.on_notify_event("@%s is following you" % source.screen_name, 
                                 "%s\n%s" % (source.name, source.description),
                                 source)
    
    def api_wrapper(self, method, *args, **kwargs):
        for i in range(3):
            try:
                self.apilock.acquire()
                response = None
                response = method(*args, **kwargs)
                break
            except urllib2.HTTPError, e:
                if e.code == 400:
                    print >>sys.stderr, "[Error] Rate Limitting %s (%s)" % (
                        e, method.func_name)
                    break
                elif e.code == 403:
                    print >>sys.stderr, "[Error] Access Denied %s (%s)" % (
                        e, method.func_name)
                    break
                elif e.code == 404:
                    print >>sys.stderr, "[Error] Not Found %s (%s)" % (
                        e, method.func_name)
                    break
                
                if i >= 3:
                    self.on_twitterapi_error(method, e)
                
                print >>sys.stderr, "[Error] %d: TwitterAPI %s (%s)" % (
                    i, e, method.func_name)
            except socket.timeout:
                print >>sys.stderr, "[Error] %d: TwitterAPI timeout (%s)" % (
                    i, method.func_name)
            except Exception, e:
                print >>sys.stderr, "[Error] %d: TwitterAPI %s (%s)" % (
                    i, e, method.func_name)
            finally:
                self.on_twitterapi_requested()
                self.apilock.release()
            
            time.sleep(1)
        
        return response
    
    def on_twitterapi_error(self, method, e): pass
    def on_twitterapi_requested(self): pass
    def on_tweet_event(self, i): pass
    def on_notify_event(self, title, text, icon_user): pass
