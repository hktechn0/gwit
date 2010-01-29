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

        # Generate API Library instance
        self.keys = keys
        self.api = twoauth.api(*self.keys)
    
    def run(self):
        # Start Thread
        while True:
            # Get home_timeline -> Exec EventHandler (Refresh TreeView)
            # Every 30 sec
            self.autoreload()
            self.EventHandler()
            time.sleep(30)
    
    def autoreload(self):
        # Get Home Timeline
        self.home = self.api.home_timeline()
