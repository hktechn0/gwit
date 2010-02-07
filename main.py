#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk

from objects import GtkObjects
from timeline import timeline
from twitterapi import twitterapi
from iconstore import IconStore

# Main Class
class Main:
    # Constractor
    def __init__(self, glade):
        # GtkBuilder instance
        builder = gtk.Builder()
        # Glade file input
        builder.add_from_file(glade)
        # Connect signals
        builder.connect_signals(self)
        
        # GtkObjects instance
        # usage: self.obj.`objectname`
        # ex) self.obj.button1
        self.obj = GtkObjects(builder.get_objects())
        
        # Set Default Mention Flag
        self.re = 0
        
        # init status timelines
        self.timelines = list()
        # init icon store
        self.icons = IconStore()
    
    def main(self, keys):
        # Twitter class instance
        self.twitter = twitterapi(keys)
        
        # Set Status Views
        for i in (("Home", "home_timeline", 30),
                  ("Mentions", "mentions", 300)):
            # Create Timeline Object
            tl = timeline(self.twitter, self.icons)
            self.timelines.append(tl)
            # Start sync timeline
            tl.start_sync(*i[1:])
            # Add Notebook (Tab view)
            tl.add_notebook(self.obj.notebook1, i[0])
            # row-activated signal connect
            tl.treeview.connect(
                "row-activated", 
                self.on_treeview_row_activated)
        
        self.obj.window1.show_all()
        
        # Gtk Multithread Setup
        gtk.gdk.threads_init()
        gtk.gdk.threads_enter()
        # Start gtk main loop
        gtk.main()
        gtk.gdk.threads_leave()
    
    # Window close event
    def close(self, widget):
        gtk.main_quit()
    
    # Status Update
    def on_button1_clicked(self, widget):
        txt = self.get_text()
        if self.re == 1:
            # in_reply_to is for future
            self.twitter.api.status_update(
                txt, in_reply_to_status_id = None)
            self.clear_buf()
            self.re = 0
        else:
            self.twitter.api.status_update(txt)
            self.clear_buf()
    
    # Reply
    def on_treeview_row_activated(self, treeview, path, view_column):
        self.re = 1
        liststore = treeview.get_model()
        path_name = liststore[path]
        buf = self.obj.textview1.get_buffer()
        buf.set_text("@%s " % (path_name[0]))
    
    # Get text
    def get_text(self):
        buf = self.obj.textview1.get_buffer()
        start, end = buf.get_start_iter(), buf.get_end_iter()
        return  buf.get_text(start, end)
    
    # Clear Buf
    def clear_buf(self):
        buf = self.obj.textview1.get_buffer()
        buf.set_text("")
