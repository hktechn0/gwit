#!/usr/bin/env python
#-*- coding: utf-8 -*-

import sys
import time
import mutex
import threading
import urllib2
import socket

import twoauth

# Twitter API Class
class twitterapi():
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
        self.followers.update([int(i) for i in self.api.followers_ids()])
        self.following.update([int(i) for i in self.api.friends_ids()])
    
    def create_timeline(self, method, interval, counts, args = (), kwargs = {}):
        # Add New Timeline Thread
        th = timeline_thread(getattr(self.api, method), interval, counts, args, kwargs)
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
    
    def status_update(self, status, reply_to = None, footer = ""):
        if reply_to != None:
            self.api.status_update(status, in_reply_to_status_id = reply_to)
        else:
            if footer != "": status = u"%s %s" % (status, footer)
            self.api.status_update(status)

# Timeline Thread
class timeline_thread(threading.Thread):
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
            statuses = None
            
            try:
                # Get Timeline
                statuses = self.api_method(*self.args, **self.kwargs)
                self.on_timeline_refresh()
                break
            except urllib2.HTTPError, e:
                print "[Error] TwitterAPI %s (%s)" % (e, self.api_method.func_name)
                self.on_twitterapi_error(self, e)
                time.sleep(5)
            except socket.timeout:
                print "[Error] TwitterAPI timeout (%s)" % (self.api_method.func_name)
            except Exception, e:
                print "[Error] TwitterAPI %s (%s)" % (e, self.api_method.func_name)
        
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
    def on_twitterapi_error(self, timeline, e): pass
