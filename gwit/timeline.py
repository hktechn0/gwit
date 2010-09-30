#-*- coding: utf-8 -*-

'''Implementation of timeline scrolled window
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

from statusview import StatusView
from timelinethread import TimelineThread, StreamingThread

class Timeline(gtk.ScrolledWindow):
    twitter = None
    
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)
        self.timeline = None
        self.stream = None
        
        # Add treeview to scrolledwindow
        self.view = StatusView()
        self.add(self.view)
        
        # Scrollbar policy
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        self.set_shadow_type(gtk.SHADOW_IN)
        self.connect("destroy", self.on_destroy)
        
        # Auto scroll to top setup
        vadj = self.get_vadjustment()
        self.vadj_upper = vadj.upper
        self.vadj_lock = False
        vadj.connect("changed", self.on_vadjustment_changed)
        vadj.connect("value-changed", self.on_vadjustment_value_changed)
    
    # Start Sync Timeline (new twitter timeline thread create)
    def set_timeline(self, method, interval, counts, args, kwargs):
        self.timeline = TimelineThread(method, interval, counts, args, kwargs)

    def set_stream(self, method, kwargs = {}):
        self.stream = StreamingThread(method, kwargs = kwargs)
    
    def start_timeline(self):
        # Set Event Hander (exec in every get timeline
        self.timeline.on_received_status = self.on_received_statuses
        # Start Timeline sync thread
        self.timeline.start()
        
    def start_stream(self):
        self.stream.on_received_status = self.on_received_statuses
        self.stream.start()
    
    # Reload Timeline
    def reload(self):
        if self.timeline != None and not self.timeline.lock.isSet():
            # lock flag set (unlock)
            self.timeline.lock.set()
    
    # Get timeline ids
    def get_timeline_ids(self):
        timeline = self.timeline.timeline if self.timeline != None else set()
        stream = self.stream.timeline if self.stream != None else set()
        
        return timeline.union(stream)
    
    def on_received_statuses(self, ids):
        self.view.prepend_new_statuses(ids.difference(self.get_timeline_ids()))
    
    
    ########################################
    # Gtk Signal Events
    
    # Scroll to top if upper(list length) changed Event
    def on_vadjustment_changed(self, adj):
        if not self.vadj_lock and self.vadj_upper < adj.upper:
            if len(self.view.store):
                self.view.scroll_to_cell((0,))
                self.view.added = False
        
        self.vadj_upper = adj.upper
        self.vadj_len = len(self.view.store)
    
    def on_vadjustment_value_changed(self, adj):
        if adj.value == 0.0:
            self.vadj_lock = False
        elif self.vadj_upper == adj.upper and not self.view.added:
            self.vadj_lock = True
    
    def on_destroy(self, widget):
        if self.timeline != None:
            self.timeline.destroy()
        if self.stream != None:
            self.stream.destroy()
        self.view.destroy()
