#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk

import threading
import random
import time

from objects import GtkObjects
from timeline import timeline
from twitterapi import twitterapi
from iconstore import IconStore

# Main Class
class Main:
    # Constractor
    def __init__(self, glade, keys, maxn = 200, iconmode = True):
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
        self.iconmode = iconmode
        
        # init status timelines
        self.timelines = list()
        # init icon store
        self.icons = IconStore(iconmode)
        
        init = threading.Thread(target=self.initialize, args=(keys, maxn))
        init.start()
    
    def main(self):        
        # Gtk Multithread Setup
        gtk.gdk.threads_init()
        gtk.gdk.threads_enter()
        self.obj.window1.show_all()
        # Start gtk main loop
        gtk.main()
        gtk.gdk.threads_leave()
    
    # Initialize Twitter API and Tabs (in another thread)
    def initialize(self, keys, maxn):
        # Twitter class instance
        self.twitter = twitterapi(keys, maxn)
        
        # Set Status Views
        for i in (("Home", "home_timeline", 30),
                  ("Mentions", "mentions", 300)):
            self._tab_append(*i)
            # insert littledelay
            time.sleep(random.random())
    
    # Window close event
    def close(self, widget):
        gtk.main_quit()
    
    # Get text
    def _get_text(self):
        buf = self.obj.textview1.get_buffer()
        start, end = buf.get_start_iter(), buf.get_end_iter()
        return  buf.get_text(start, end)
    
    # Clear Buf
    def _clear_buf(self):
        buf = self.obj.textview1.get_buffer()
        buf.set_text("")
    
    def _tab_append(self, name, method, sleep, *args, **kwargs):
        # Create Timeline Object
        tl = timeline(self.twitter, self.icons, self.iconmode)
        self.timelines.append(tl)
        
        # Start sync timeline
        if method:
            tl.start_sync(method, sleep, args, kwargs)
        
        # Add Notebook (Tab view)
        tl.add_notebook(self.obj.notebook1, name)
        # Add Popup Menu
        tl.add_popup(self.obj.menu_timeline)
        
        # Treeview double click signal connect
        tl.treeview.connect(
            "row-activated",
            self.on_treeview_row_activated)

    def get_selected_status(self):
        n = self.obj.notebook1.get_current_page()
        return self.timelines[n].get_selected_status()

    def get_current_tab(self):
        return self.obj.notebook1.get_current_page()
    
    ########################################
    # Gtk Signal Events
    
    # Status Update
    def on_button1_clicked(self, widget):
        txt = self._get_text()
        if self.re:
            # in_reply_to is for future
            self.twitter.api.status_update(
                txt, in_reply_to_status_id = self.re)
            self._clear_buf()
            self.re = None
        else:
            self.twitter.api.status_update(txt)
            self._clear_buf()
    
    # Reply if double-clicked status
    def on_treeview_row_activated(self, treeview, path, view_column):
        status = self.get_selected_status()
        self.re = status.id
        name = status.user.screen_name
        buf = self.obj.textview1.get_buffer()
        buf.set_text("@%s " % (name))
        self.obj.textview1.grab_focus()
    # Same....
    def on_menuitem_reply_activate(self, menuitem):
        status = self.get_selected_status()
        self.re = status.id
        name = status.user.screen_name
        buf = self.obj.textview1.get_buffer()
        buf.set_text("@%s " % (name)) 
        self.obj.textview1.grab_focus()
    
    # Retweet menu clicked
    def on_menuitem_retweet_activate(self, memuitem):
        status = self.get_selected_status()
        self.twitter.api.status_retweet(status.id)
    
    # Retweet with comment menu clicked
    def on_menuitem_reteet_with_comment_activate(self, memuitem):
        status = self.get_selected_status()
        self.re = status.id
        name = status.user.screen_name
        text = status.text
        buf = self.obj.textview1.get_buffer()
        buf.set_text("RT @%s: %s" % (name, text))
        self.obj.textview1.grab_focus()    
        
    # Added user timeline tab
    def on_menuitem_usertl_activate(self, menuitem):
        status = self.get_selected_status()
        sname = status.user.screen_name
        self._tab_append("@%s" % sname, "user_timeline", 60, user = sname)

    def on_menuitem_fav_activate(self, menuitem):
        status = self.get_selected_status()
        self.twitter.api.favorite_create(status.id)
