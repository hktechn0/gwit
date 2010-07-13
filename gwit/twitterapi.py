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
import mutex
import threading
import urllib2
import socket

import twoauth

# Twitter API Class
class TwitterAPI():
    def __init__(self, screen_name, ckey, csecret, atoken, asecret):
        # Generate API Library instance
        self.api = twoauth.api(ckey, csecret, atoken, asecret, screen_name)
        self.myname = self.api.user["screen_name"]
        self.me = None
        self.my_name = screen_name
        #self.threads = list()
        
        # User, Status Buffer
        self.users = dict()
        self.statuses = dict()
        self.followers = set()
        self.following = set()
        
        t = threading.Thread(target=self.get_following_followers)
        t.start()
    
    def init_twitpic(self, apikey):
        import twoauth.twitpic
        self.twitpic = twoauth.twitpic.Twitpic(self.api.oauth, apikey)
    
    def get_following_followers(self):
        # Get followers
        self.followers.update([int(i) for i in self.api_wrapper(self.api.followers_ids)])
        self.following.update([int(i) for i in self.api_wrapper(self.api.friends_ids)])
    
    def create_timeline(self, method, interval, counts, args = (), kwargs = {}):
        # Add New Timeline Thread
        th = TimelineThread(getattr(self.api, method), interval, counts, args, kwargs)
        th.added_event = self.add_status
        th.statuses = self.statuses
        #self.threads.append(th)
        return th
    
    def add_statuses(self, slist):
        for i in slist:
            self.add_status(i)
    
    def add_status(self, status):
        self.statuses[status.id] = status
        self.add_user(status.user)
        
        if status.retweeted_status != None:
            self.add_status(status.retweeted_status)
    
    def add_user(self, user):
        self.users[user.id] = user
        
        if user.screen_name == self.myname:
            self.me = user
    
    def get_user_from_screen_name(self, screen_name):
        # search user from screen_name
        for user in self.users.itervalues():
            if user.screen_name == screen_name:
                return user
        
        return None
    
    def get_statuses(self, ids):
        return tuple(self.statuses[i] for i in sorted(tuple(ids), reverse=True))
    
    def api_wrapper(self, method, *args, **kwargs):
        for i in range(3):
            try:
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
                    self.on_twitterapi_error(self, e)
                print >>sys.stderr, "[Error] %d: TwitterAPI %s (%s)" % (i, e, method.func_name)
                time.sleep(5)
            except socket.timeout:
                print >>sys.stderr, "[Error] %d: TwitterAPI timeout (%s)" % (i, method.func_name)
            except Exception, e:
                print >>sys.stderr, "[Error] %d: TwitterAPI %s (%s)" % (i, e, method.func_name)
        
        return response
    
    def status_update(self, status, reply_to = None, footer = ""):
        if reply_to != None:
            self.api_wrapper(self.api.status_update, status, in_reply_to_status_id = reply_to)
        else:
            if footer != "": status = u"%s %s" % (status, footer)
            self.api_wrapper(self.api.status_update, status)
    
    def on_twitterapi_error(self, method, e): pass

# Timeline Thread
class TimelineThread(threading.Thread):
    def __init__(self, method, interval, counts, args, kwargs):
        # Thread Initialize
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.setName(method.func_name + str(args))
        
        # Event lock
        self.lock = threading.Event()
        self.addlock = mutex.mutex()
        self.die = False
        
        self.api_method = method
        self.interval = interval
        self.lastid = None
        self.timeline = set()
        
        socket.setdefaulttimeout(10)        
        
        # API Arguments
        self.args = args
        self.kwargs = kwargs
        
        # set first get count
        self.set_count(counts[0])
        self.count = counts[1]
    
    # Thread run
    def run(self):
        # extract cached status if gets user_timeline
        if self.api_method.func_name == "user_timeline":
            cached = set()
            for i in self.statuses.itervalues():
                if i.user.id == self.kwargs["user"]:
                    cached.add(i.id)
            
            if cached:
                self.add(cached)
        
        # Auto reloading loop
        while not self.die:
            last = self.refresh_timeline()
            
            # If Timeline update
            if last:
                # Append status cache
                new = set()
                for i in last:
                    new.add(i.id)
                    self.added_event(i)
                
                # Add statuses to timeline
                self.add(new)
                
                # update lastid
                self.lastid = last[-1].id
                self.kwargs["since_id"] = self.lastid
            
            # Reload lock
            self.lock.clear()
            if self.interval != -1:
                self.lock.wait(self.interval)
            else:
                self.lock.wait()
            
            self.set_count(self.count)
    
    def refresh_timeline(self):
        for i in range(3):
            try:
                statuses = None
                # Get Timeline
                statuses = self.api_method(*self.args, **self.kwargs)
                self.on_timeline_refresh()
                break
            except urllib2.HTTPError, e:                
                if i >= 3:
                    self.on_twitterapi_error(self, e)
                print >>sys.stderr, "[Error] %d: TwitterAPI %s (%s)" % (i, e, self.api_method.func_name)
                time.sleep(5)
            except socket.timeout:
                print >>sys.stderr, "[Error] %d: TwitterAPI timeout (%s)" % (i, self.api_method.func_name)
            except Exception, e:
                print >>sys.stderr, "[Error] %d: TwitterAPI %s (%s)" % (i, e, self.api_method.func_name)
        
        return statuses
    
    def add(self, ids):
        # mutex lock
        self.addlock.lock(self.add_mutex, ids)
    
    def add_mutex(self, ids):
        # defference update = delete already exists status
        ids.difference_update(self.timeline)
        if ids:
            # exec EventHander (TreeView Refresh)
            self.reloadEventHandler(ids)
            # add new statuse ids
            self.timeline.update(ids)
        
        self.addlock.unlock()
    
    def destroy(self):
        self.die = True
        self.lock.set()
    
    def set_count(self, n):
        if self.api_method.func_name == "lists_statuses":
            self.kwargs["per_page"] = n
        else:
            self.kwargs["count"] = n
    
    def on_timeline_refresh(self): pass
    def reloadEventHandler(self): pass
