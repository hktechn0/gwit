#-*- coding: utf-8 -*-

'''Thread class for Timeline
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


import socket
import mutex
import threading
import urllib2

import twoauth

class BaseThread(threading.Thread):
    twitter = None
    
    def __init__(self, method, args = (), kwargs = {}):
        # Thread Initialize
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.setName(method + str(args))
        
        self.method = method
        self.args = args
        self.kwargs = kwargs
        
        self.timeline = set()    
        self.die = False
    
    def run(self): pass
    
    def destroy(self):
        self.die = True
    
    def add_statuses(self, statuses):
        new_statuses = set()
        
        for i in statuses:
            if isinstance(i, twoauth.TwitterStatus):
                self.twitter.add_status(i)
                new_statuses.add(i.id)
            else:
                # deleted, favorited, followed... for StreamingAPI
                if "friends" in i:
                    self.twitter.following.update(i["friends"])
        
        new_statuses.difference_update(self.timeline)
        self.on_received_status(new_statuses)
        self.timeline.update(new_statuses)
    
    def on_received_status(self, ids): pass

# Timeline Thread
class TimelineThread(BaseThread):
    def __init__(self, method, interval, counts, args = (), kwargs = {}):
        BaseThread.__init__(self, method, args, kwargs)
        
        # Event lock
        self.lock = threading.Event()
        
        self.api_method = method
        self.interval = interval
        
        # set first get count
        self.set_count(counts[0])
        self.count = counts[1]
    
    # Thread run
    def run(self):
        lastid = None
        
        # extract cached status if gets user_timeline
        if self.method == "user_timeline":
            cached = list()
            for i in self.twitter.statuses.values():
                if i.user.id == self.kwargs["user"]:
                    cached.append(i)
            
            if len(cached) > 0:
                self.add_statuses(cached)
        
        # Auto reloading loop
        while not self.die:
            apimethod = getattr(self.twitter.api, self.method)
            statuses = self.twitter.api_wrapper(apimethod, *self.args, **self.kwargs)
            # If Timeline update
            if statuses:
                # Add statuses to timeline
                self.add_statuses(statuses)
                
                # update lastid
                self.lastid = statuses[-1].id
                self.kwargs["since_id"] = self.lastid
            # Reload lock
            self.lock.clear()
            if self.interval != -1:
                self.lock.wait(self.interval)
            else:
                self.lock.wait()
            
            self.set_count(self.count)
    
    def destroy(self):
        self.die = True
        self.lock.set()
    
    def set_count(self, n):
        if self.method == "lists_statuses":
            self.kwargs["per_page"] = n
        else:
            self.kwargs["count"] = n

class StreamingThread(BaseThread):
    def run(self):
        apimethod = getattr(self.twitter.sapi, self.method)
        stream = apimethod(*self.args, **self.kwargs)
        
        stream.start()
        while not self.die:
            self.add_statuses(stream.pop())
            stream.event.wait()
        stream.stop()
