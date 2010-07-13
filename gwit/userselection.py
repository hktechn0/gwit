#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango

import threading
import sched
import time

class UserSelection(gtk.VBox):
    def __init__(self, twitter, icons):
        gtk.VBox.__init__(self)
        hbox = gtk.HBox()
        
        self.twitter = twitter
        self.icons = icons
        self.users = twitter.users
        self.userids = frozenset()
        
        # Setting up screen_name entry
        self.entry = gtk.Entry()
        self.entry.connect("activate", self.on_entry_activate)
        self.entry.connect("focus-in-event", self.on_entry_focus_in)
        self.entry.connect("focus-out-event", self.on_entry_focus_out)
        hbox.pack_start(self.entry, padding = 5)
        
        button = gtk.Button()
        button.set_image(gtk.image_new_from_stock("gtk-add", gtk.ICON_SIZE_BUTTON))
        button.connect("clicked", self.on_button_clicked)
        hbox.pack_start(button, expand = False, padding = 5)
        
        self.store = gtk.ListStore(gtk.gdk.Pixbuf, str, gobject.TYPE_INT64, str, gtk.gdk.Pixbuf, gtk.gdk.Pixbuf)
        self.icons.add_store(self.store, 2)
        
        # sort order by screen_name ASC
        self.store.set_sort_column_id(3, gtk.SORT_ASCENDING)
        
        # setup treeview
        self.treeview = gtk.TreeView(self.store)
        #self.treeview.set_headers_visible(False)
        self.treeview.set_rules_hint(True)
        self.treeview.set_enable_search(True)
        self.treeview.set_search_column(3)
        self.treeview.connect("cursor-changed", self.on_treeview_cursor_changed)
        self.treeview.connect("button-press-event", self.on_treeview_button_press_event)
        self.treeview.connect("row-activated", self.on_treeview_row_activated)
        #self.treeview.connect("size-allocate", self.on_treeview_width_changed)
        
        self.treeview.append_column(
            gtk.TreeViewColumn("Icon", gtk.CellRendererPixbuf(), pixbuf = 0))
        
        cell_name = gtk.CellRendererText()
        cell_name.set_property("wrap-mode", pango.WRAP_WORD)
        cell_name.set_property("wrap-width", 300)
        col_name = gtk.TreeViewColumn("Name", cell_name, markup = 1)
        col_name.set_expand(True)
        self.treeview.append_column(col_name)
        
        self.treeview.append_column(
            gtk.TreeViewColumn("Following?", gtk.CellRendererPixbuf(), pixbuf = 4))
        self.treeview.append_column(
            gtk.TreeViewColumn("Follower?", gtk.CellRendererPixbuf(), pixbuf = 5))
        
        self.scrwin = gtk.ScrolledWindow()
        self.scrwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self.scrwin.set_shadow_type(gtk.SHADOW_IN)
        self.scrwin.add(self.treeview)
        
        self._now_box = gtk.Label()
        
        self.paned = gtk.VPaned()
        self.paned.pack1(self._now_box)
        self.paned.pack2(self.scrwin)
        
        self.pack_start(hbox, expand = False, padding = 5)
        self.pack_start(self.paned)

        self.pix_follow = self.render_icon("gtk-yes", gtk.ICON_SIZE_BUTTON)
        self.pix_nofollow = self.render_icon("gtk-no", gtk.ICON_SIZE_BUTTON)
        
        # User view scheduler run
        self.scheduler = sched.scheduler(self.user_count, self._delay)
        t = threading.Thread(target=self.scheduler_run)
        t.setDaemon(True)
        t.setName("userselection")
        t.start()
    
    def _delay(self, n):
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
            text = "<b>%s</b>\n<small><span foreground='#666666'>%s</span></small>" % (
                user.screen_name, unicode(user.name).replace("&", "&amp;"))
            is_friend = user.id in self.twitter.following
            is_follower = user.id in self.twitter.followers
            icon = self.icons.get(user)
            
            following = self.pix_follow if is_friend else self.pix_nofollow
            follower = self.pix_follow if is_follower else self.pix_nofollow
            
            gtk.gdk.threads_enter()
            self.store.append((icon, text, user.id, user.screen_name, following, follower))
            gtk.gdk.threads_leave()
        
        self.userids = now
    
    def activate_user(self, sname):
        # create new timeline
        if sname == "": return True
        
        user = self.twitter.get_user_from_screen_name(sname)
        if user != None:
            self.new_timeline("@%s" % sname, "user_timeline",
                              user = user.id)
        else:
            self.new_timeline("@%s" % sname, "user_timeline",
                              user = sname, is_screen_name = True)
    
    def refresh_user_information(self, user):
        bio = """<big><b>%s</b></big> - %s\n<small><span foreground='#666666'>Location: %s\nBio: %s\nWeb: %s</span></small>\n<b>%d</b> following, <b>%d</b> followers, <b>%d</b> tweets""" % (
            user.screen_name, unicode(user.name).replace("&", "&amp;"),
            unicode(user.location).replace("&", "&amp;"),
            unicode(user.description).replace("\n", "").replace("&", "&amp;"),
            ("<a href='%s'>%s</a>" % (user.url, user.url)) if user.url != None else None,
            user.friends_count, user.followers_count, user.statuses_count)

        if user.protected: bio += "\n[Protected user]"
        
        img = gtk.image_new_from_pixbuf(self.icons.get(user))
        is_follow = user.id in self.twitter.following
        button = gtk.ToggleButton("Following" if is_follow else "Follow")
        button.set_active(is_follow)
        button.set_image(gtk.image_new_from_stock("gtk-apply", gtk.ICON_SIZE_BUTTON)
                         if is_follow else gtk.image_new_from_stock("gtk-add", gtk.ICON_SIZE_BUTTON))
        button.connect("toggled", self.on_follow_button_toggled)
        
        vbox = gtk.VBox()
        vbox.set_spacing(10)
        vbox.pack_start(img)
        vbox.pack_end(button, expand = False)
        
        label = gtk.Label()
        label.set_padding(30, 0)
        label.set_alignment(0, 0.5)
        label.set_line_wrap(True)
        label.set_markup(bio)
        
        hbox = gtk.HBox()
        hbox.set_border_width(10)
        hbox.pack_start(vbox, expand = False)
        hbox.pack_end(label)
        
        img.show()
        label.show()
        hbox.show_all()
        
        self.paned.remove(self._now_box)
        self._now_box = hbox
        self.paned.pack1(self._now_box, shrink = False)
    
    # for override
    def new_timeline(self, label, method, sleep, *args, **kwargs):
        pass
    
    ### Event    
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
    
    def on_treeview_button_press_event(self, treeview, event):
        path = treeview.get_path_at_pos(int(event.x), int(event.y))[0]
        treeview.grab_focus()
        treeview.set_cursor(path)
    
    def on_treeview_cursor_changed(self, treeview):
        if not self.entry.is_focus():
            path, column = treeview.get_cursor()
            uid = treeview.get_model()[path][2]
            user = self.users[uid]
            self.entry.set_text(user.screen_name)
            self.refresh_user_information(user)
    
    def on_entry_focus_in(self, entry, direction):
        self.treeview.set_search_entry(entry)
    
    def on_entry_focus_out(self, entry, direction):
        self.treeview.set_search_entry(None)

    def on_follow_button_toggled(self, button):
        path, column = self.treeview.get_cursor()
        uid = self.treeview.get_model()[path][2]
        follow = button.get_active()
        
        if follow:
            self.twitter.api.friends_create(uid)
            button.set_image(gtk.image_new_from_stock("gtk-apply", gtk.ICON_SIZE_BUTTON))
            button.set_label("Following")
            self.twitter.following.add(uid)
        else:
            self.twitter.api.friends_destroy(uid)
            button.set_image(gtk.image_new_from_stock("gtk-add", gtk.ICON_SIZE_BUTTON))
            button.set_label("Follow")
            self.twitter.following.remove(uid)
