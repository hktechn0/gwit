#-*- coding: utf-8 -*-

'''Streaming API view like Timeline class
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


import pygtk
pygtk.require('2.0')
import gtk

import threading

import twoauth.streaming
from statusview import StatusView
from timeline import Timeline

class StreamingThread(threading.Thread):
    def __init__(self, twitter, params = {}):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        
        self.twitter = twitter
        self.params = params
        self.sapi = twoauth.streaming.StreamingAPI(self.twitter.api.oauth)
        
        self.timeline = set()    
        self.die = False
    
    def run(self):
        #stream = self.sapi.sample()
        #stream = self.sapi.filter(follow = tuple(self.twitter.following)[:400])
        stream = self.sapi.filter(**self.params)
        stream.start()
        
        while not self.die:
            newids = set()
            for i in stream.pop():
                if "text" in i.keys():
                    self.twitter.add_status(i)
                    newids.add(i.id)
            
            self.timeline.update(newids)
            self.on_received_statuses(newids)
            stream.event.wait()
        
        stream.stop()
    
    def destroy(self):
        self.die = True
    
    def on_received_statuses(self, ids): pass

class StreamingView(Timeline):
    # Start Sync Timeline (new twitter timeline thread create)
    def init_timeline(self, params = {}):
        self.timeline = StreamingThread(self.twitter, params)
        # Set Event Hander
        self.timeline.on_received_statuses = self.view.prepend_new_statuses
    
    def start_timeline(self):
        # Start Streaming API
        self.timeline.start()
    
    # Reload Timeline
    def reload(self):
        pass
    
    # Get timeline ids
    def get_timeline_ids(self):
        return self.timeline.timeline
