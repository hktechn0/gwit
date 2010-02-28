#!/usr/bin/env python
#-*- coding: utf-8 -*-

import twoauth
import threading
import sys

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
        self.timeline = list()
        
        # API Arguments
        self.args = args
        self.kwargs = kwargs
        self.kwargs["count"] = maxn
    
    # Thread run
    def run(self):
        while True:
            try:
                # Get Timeline
                self.last = self.func(*self.args, **self.kwargs)
            except Exception, e:
                self.last = list()
                print >>sys.stderr, "Error", e
            
            # If Timeline update
            if self.last:
                for i in self.last:
                    # append new statuses to timeline buffer
                    self.timeline.append(i.id)
                    self.added_event(i)
                
                # update lastid
                self.lastid = self.last[-1].id
                self.kwargs["since_id"] = self.lastid
                
                # exec EventHander (TreeView Refresh
                self.reloadEventHandler(self.last)
            
            # Reload delay
            self.lock.clear()
            self.lock.wait(self.interval)
