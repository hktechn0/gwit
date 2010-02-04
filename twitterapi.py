#!/usr/bin/env python
#-*- coding: utf-8 -*-

import twoauth
import threading
import time

# Twitter API Class
class twitterapi():
    def __init__(self, keys):
        # init id
        self.lastid = None
        # OAuth key, token, secrets
        self.keys = keys
        # Generate API Library instance
        self.api = twoauth.api(*self.keys)

        self.threads = list()
    
    def add(self, func, sleep):
        # Add New Timeline Thread
        th = autoreload(
            len(self.threads), getattr(self.api, func), sleep)
        th.EventHandler = self.EventHandler
        th.start()
        self.threads.append(th)

# Timeline Thread
class autoreload(threading.Thread):
    def __init__(self, index, func, sleep):
        # Thread Initialize
        threading.Thread.__init__(self)
        self.setDaemon(True)
        
        self.index = index
        self.func = func
        self.sleep = sleep
        self.lastid = None
    
    # Thread run
    def run(self):
        while True:
            # Get Timeline
            self.data = self.func(
                count = 200, since_id = self.lastid)
            
            # If Timeline update
            if self.data:
                # update lastid
                self.lastid = self.data[-1].id
                # exec EventHander (TreeView Refresh
                self.EventHandler(self.data, self.index)
            
            # Sleep
            time.sleep(self.sleep)
