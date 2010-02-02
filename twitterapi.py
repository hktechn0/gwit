#!/usr/bin/env python
#-*- coding: utf-8 -*-

import twoauth
import threading
import time

# Twitter API Class
class twitterapi(threading.Thread):
    def __init__(self, keys):
        # init Thread
        threading.Thread.__init__(self)
        self.setDaemon(True)
        
        # init id
        self.lastid = None

        # OAuth key, token, secrets
        self.keys = keys

    # Start Thread
    def run(self):
        # Generate API Library instance
        self.api = twoauth.api(*self.keys)

        while True:
            # Get home_timeline -> Exec EventHandler (Refresh TreeView)
            # Every 30 sec
            self.autoreload()
            time.sleep(10)
    
    def autoreload(self):
        # Get Home Timeline
        self.home = self.api.home_timeline(since_id = self.lastid, count = 200)
        if self.home:
            self.lastid = self.home[-1].id
            self.EventHandler()
