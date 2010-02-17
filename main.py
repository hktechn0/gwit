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
    def __init__(self, glade, keys):
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

        init = threading.Thread(target=self.initialize, args=(keys))
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
    def initialize(self, *keys):
        # Twitter class instance
        self.twitter = twitterapi(keys)
        
        # Set Status Views
        for i in (("Home", "home_timeline", 30),
                  ("Mentions", "mentions", 300),
                  ("Nations", "", 300)):
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
        tl = timeline(self.twitter, self.icons)
        self.timelines.append(tl)
        
        # Start sync timeline
        if method:
            tl.start_sync(method, sleep, args, kwargs)
        
        # Add Notebook (Tab view)
        tl.add_notebook(self.obj.notebook1, name)
        # Add Popup Menu
        tl.add_popup(self.obj.menu_timeline)
        
        # Click, Double Click signal connect
        tl.treeview.connect(
            "cursor-changed",
            self.on_treeview_cursor_changed)
        tl.treeview.connect(
            "row-activated",
            self.on_treeview_row_activated)
    
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
        n = self.obj.notebook1.get_current_page()
        status = self.timelines[n].get_status(path)
        self.re = status.id
        name = status.user.screen_name
        buf = self.obj.textview1.get_buffer()
        buf.set_text("@%s " % (name))
    
    def on_menuitem_usertl_activate(self, menuitem):
        n = self.obj.notebook1.get_current_page()
        status = self.timelines[n].get_selected_status()
        sname = status.user.screen_name
        self._tab_append("@%s" % sname, "user_timeline", 60, user = sname)

    def on_menuitem_reply_activate(self, menuitem):
        n = self.obj.notebook1.get_current_page()
        status = self.timelines[n].get_selected_status()
        self.re = status.id
        name = status.user.screen_name
        buf = self.obj.textview1.get_buffer()
        buf.set_text("@%s " % (name)) 
        self.callback(textview1, gtk.DIR_TAB_FORWARD)

    def on_menuitem_retweet_activate(self, memuitem):
        n = self.obj.notebook1.get_current_page()
        status = self.timelines[n].get_selected_status()
        self.twitter.api.status_retweet(status.id)

    def on_menuitem_reteet_with_comment_activate(self, memuitem):
        n = self.obj.notebook1.get_current_page()
        status = self.timelines[n].get_selected_status()
        self.re = status.id
        name = status.user.screen_name
        text = status.text
        buf = self.obj.textview1.get_buffer()
        buf.set_text("RT @%s: %s" % (name, text))

    # Status Clicked
    def on_treeview_cursor_changed(self, treeview):
        n = self.obj.notebook1.get_current_page()
        status = self.timelines[n].get_selected_status()

        id = status.id
        uid = status.user.id
        to = status.in_reply_to_status_id
        to_uid = status.in_reply_to_user_id
        
        me = self.twitter.api.user.id
        
        store = self.timelines[n].store
        i = store.get_iter_first()
        
        # Colord status
        while i:
            iid, iuid, ito, ito_uid = store.get(i, 2, 3, 4, 5)
            if iuid == me:
                # My status (Green)
                bg = "#CCFFCC"
            elif ito_uid == me:
                # Reply to me (Red)
                bg = "#FFCCCC"
            elif iid == to:
                # Reply to (Orange)
                bg = "#FFCC99"
            elif iuid == to_uid:
                # Reply to other (Yellow)
                bg = "#FFFFCC"
            elif iuid == uid:
                # Selected user (Blue)
                bg = "#CCCCFF"
            else:
                bg = None
            
            store.set_value(i, 6, bg)
            i = store.iter_next(i)
