#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk

from objects import GtkObjects
from twitterapi import twitterapi
from statusview import statusview

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
        
        # Setup status views
        self.views = list()
    
    def main(self, keys):
        # Twitter class instance
        self.twitter = twitterapi(keys)
        # Set Event Hander (exec in every get timeline
        self.twitter.EventHandler = self.refresh

        # Set Status Views
        for i in (("Home", "home_timeline", 30),
                  ("Mentions", "mentions", 300)):
            self.tab_append(*i)
        
        self.obj.window1.show_all()
        
        # Gtk Multithread Setup
        gtk.gdk.threads_init()
        gtk.gdk.threads_enter()
        
        # Start gtk main loop
        gtk.main()
        gtk.gdk.threads_leave()
    
    # Refresh TreeView
    def refresh(self, data, index):
        gtk.gdk.threads_enter()
        
        # Insert New Status
        for i in data:
            self.views[index].store.prepend(
                (i.user.screen_name ,i.text))
        
        #print self.twitter.threads[index].timeline[0].id
        
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
    
    # Tab append
    def tab_append(self, name, method, sleep):
        # Generate Views
        view = statusview()
        view.add(self.obj.notebook1, name)
        
        # row-activated signal connect
        view.treeview.connect(
            "row-activated", 
            self.on_treeview_row_activated)
        
        # View append
        self.views.append(view)
        # Timeline append
        self.twitter.add(method, sleep)
