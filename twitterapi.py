#!/usr/bin/env python
#-*- coding: utf-8 -*-

import twoauth
import threading
import time
import sys

# Twitter API Class
class twitterapi():
    def __init__(self, keys, maxn):
        # Generate API Library instance
        self.api = twoauth.api(*keys)
        self.maxn = maxn
        self.threads = list()
    
    def create_timeline(self, func, sleep, args, kwargs):
        # Add New Timeline Thread
        th = timeline_thread(getattr(self.api, func),
                             sleep, self.maxn, args, kwargs)
        self.threads.append(th)
        return th

# Timeline Thread
class timeline_thread(threading.Thread):
    def __init__(self, func, sleep, maxn, args, kwargs):
        # Thread Initialize
        threading.Thread.__init__(self)
        self.setDaemon(True)
        
        self.func = func
        self.sleep = sleep
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
                # append new statuses to timeline buffer
                self.timeline.extend(self.last)
                # update lastid
                self.lastid = self.last[-1].id
                self.kwargs["since_id"] = self.lastid
                # exec EventHander (TreeView Refresh
                self.reloadEventHandler(self.last)
            
            # Sleep
            time.sleep(self.sleep)
