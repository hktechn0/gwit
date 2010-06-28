#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk
import gobject

import threading
import sched
import time

class UserSelection(gtk.VBox):
    def __init__(self):
        gtk.VBox.__init__(self, spacing = 5)        
        hbox = gtk.HBox()

        self.entry = gtk.Entry()
        self.entry.connect("activate", self.on_entry_activate)
        self.entry.connect("focus-in-event", self.on_entry_focus_in)
        self.entry.connect("focus-out-event", self.on_entry_focus_out)
        hbox.pack_start(self.entry)

        button = gtk.Button()
        button.set_image(gtk.image_new_from_stock("gtk-add", gtk.ICON_SIZE_BUTTON))
        button.connect("clicked", self.on_button_clicked)
        hbox.pack_start(button, expand = False)

        self.pack_start(hbox, expand = False)
        
        self.store = gtk.ListStore(gtk.gdk.Pixbuf, str, gobject.TYPE_INT64)
        self.store.set_sort_column_id(1, gtk.SORT_ASCENDING)

        self.treeview = gtk.TreeView(self.store)
        self.treeview.set_headers_visible(False)
        self.treeview.set_enable_search(True)
        self.treeview.connect("cursor-changed", self.on_treeview_cursor_changed)
        self.treeview.connect("row-activated", self.on_treeview_row_activated)
        self.treeview.append_column(
            gtk.TreeViewColumn(
                "Icon", gtk.CellRendererPixbuf(), pixbuf = 0))
        self.treeview.append_column(
            gtk.TreeViewColumn(
                "screen_name", gtk.CellRendererText(), text = 1))
        
        self.scrwin = gtk.ScrolledWindow()
        self.scrwin.set_policy(
            gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        self.scrwin.set_shadow_type(gtk.SHADOW_IN)
        self.scrwin.add(self.treeview)
        
        self.pack_start(self.scrwin)
    
    def set_userdict(self, userdict, iconstore):
        self.users = userdict
        self.icons = iconstore
        self.userids = frozenset()
        
        self.scheduler = sched.scheduler(self.user_count, self.delay)
        t = threading.Thread(target=self.scheduler_run)
        t.setDaemon(True)
        t.setName("userselection")
        t.start()
    
    def delay(self, n):
        time.sleep(10)
    
    def user_count(self):
        return int(len(self.users))
    
    def scheduler_run(self):
        while True:
            self.scheduler.enter(1, 1, self.refresh_users, ())
            self.scheduler.run()
    
    def refresh_users(self):
        now = frozenset(self.users.keys())
        diff = now.difference(self.userids)
        
        for uid in diff:
            user = self.users[uid]
            gtk.gdk.threads_enter()  
            self.store.prepend(
                (self.icons.get(user),
                 user.screen_name,
                 user.id,))
            gtk.gdk.threads_leave()
        
        self.userids = now

    def activate_user(self, sname):
        if sname == "":
            return True
        
        user = self.twitter.get_user_from_screen_name(sname)
        if user != None:
            self.new_timeline("@%s" % sname, "user_timeline", -1,
                              user = user.id)
        else:
            self.new_timeline("@%s" % sname, "user_timeline", -1,
                              user = sname, sn = True)

    def on_entry_activate(self, entry):
        sname = entry.get_text()
        return self.activate_user(sname)
    
    def on_button_clicked(self, button):
        sname = self.entry.get_text()
        return self.activate_user(sname)

    def on_treeview_row_activated(self, treeview, path, view_column):
        uid = treeview.get_model()[path][2]
        sname = self.users[uid].screen_name
        self.entry.set_text(sname)
        return self.activate_user(sname)
    
    def on_treeview_cursor_changed(self, treeview):
        if not self.entry.is_focus():
            path, column = treeview.get_cursor()
            uid = treeview.get_model()[path][2]
            self.entry.set_text(self.users[uid].screen_name)
    
    def on_entry_focus_in(self, entry, direction):
        self.treeview.set_search_entry(entry)
    
    def on_entry_focus_out(self, entry, direction):
        self.treeview.set_search_entry(None)
