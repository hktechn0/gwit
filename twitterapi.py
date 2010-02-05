#!/usr/bin/env python
#-*- coding: utf-8 -*-

import twoauth
import threading
import time

# Twitter API Class
class twitterapi():
    def __init__(self, keys):
        # Generate API Library instance
        self.api = twoauth.api(*keys)
        self.threads = list()
    
    def create_timeline(self, func, sleep):
        # Add New Timeline Thread
        th = timeline_thread(getattr(self.api, func), sleep)
        self.threads.append(th)
        return th

# Timeline Thread
class timeline_thread(threading.Thread):
    def __init__(self, func, sleep):
        # Thread Initialize
        threading.Thread.__init__(self)
        self.setDaemon(True)
        
        self.func = func
        self.sleep = sleep
        self.lastid = None
        self.timeline = list()
    
    # Thread run
    def run(self):
        while True:
            # Get Timeline
            self.last = self.func(
                count = 200, since_id = self.lastid)
            
            # If Timeline update
            if self.last:
                # append new statuses to timeline buffer
                self.timeline.extend(self.last)
                # update lastid
                self.lastid = self.last[-1].id
                # exec EventHander (TreeView Refresh
                self.reloadEventHandler(self.last)
            
            # Sleep
            time.sleep(self.sleep)
