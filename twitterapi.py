#!/usr/bin/env python
#-*- coding: utf-8 -*-

import twoauth
import threading
import sys
import time

# Twitter API Class
class twitterapi():
    def __init__(self, keys, maxn):
        # Generate API Library instance
        self.api = twoauth.api(*keys)
        self.threads = list()
        
        # User, Status Buffer
        self.users = dict()
        self.statuses = dict()
        
        self.maxn = maxn
        self.myid = self.api.user.id
        self.users[self.myid] = self.api.user
    
    def create_timeline(self, func, interval, args, kwargs):
        # Add New Timeline Thread
        th = timeline_thread(getattr(self.api, func),
                             interval, self.maxn, args, kwargs)
        th.added_event = self.add_status
        th.statuses = self.statuses
        self.threads.append(th)
        return th
    
    def add_statuses(self, slist):
        for i in slist:
            self.add_status(i)
    
    def add_status(self, status):
        self.statuses[status.id] = status
        self.add_user(status.user)
    
    def add_user(self, user):
        self.users[user.id] = user

# Timeline Thread
class timeline_thread(threading.Thread):
    def __init__(self, func, interval, maxn, args, kwargs):
        # Thread Initialize
        threading.Thread.__init__(self)
        self.setDaemon(True)
        
        # Event lock
        self.lock = threading.Event()
        
        self.func = func
        self.interval = interval
        self.lastid = None
        self.timeline = set()
        
        # API Arguments
        self.args = args
        self.kwargs = kwargs
        self.kwargs["count"] = maxn
    
    # Thread run
    def run(self):
        if self.func.func_name == "user_timeline":
            # extract cached status if gets user_timeline
            cached = set()
            for i in self.statuses.itervalues():
                if i.user.id == self.kwargs["user"]:
                    cached.add(i.id)
            
            if cached:
                self.add(cached)
        
        while True:
            try:
                # Get Timeline
                last = self.func(*self.args, **self.kwargs)
            except Exception, e:
                last = None
                print >>sys.stderr, "[Error] TwitterAPI ",
                print >>sys.stderr, time.strftime("%H:%M:%S"), e
            
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
            
            # debug print
            print "[debug] reload", time.strftime("%H:%M:%S"),
            print self.func.func_name, self.args, self.kwargs
            
            # Reload lock
            self.lock.clear()
            if self.interval != -1:
                self.lock.wait(self.interval)
            else:
                self.lock.wait()
    
    def add(self, ids):
        # exec EventHander (TreeView Refresh
        ids.difference_update(self.timeline)
        self.reloadEventHandler(ids)
        # add new statuse ids
        self.timeline.update(ids)
