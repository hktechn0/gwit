#-*- coding: utf-8 -*-

'''Twitter user selection widget
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
import gobject
import pango

import os.path
import threading
import sched
import time

from twittertools import TwitterTools

class UserSelection(gtk.VBox):
    twitter = None
    iconstore = None
    
    def __init__(self):
        gtk.VBox.__init__(self)
        hbox = gtk.HBox()
        
        self.users = self.twitter.users
        self.userids = frozenset()
        
        # Setting up screen_name entry
        self.entry = gtk.Entry()
        self.entry.connect("activate", self.on_entry_activate)
        self.entry.connect("focus-in-event", self.on_entry_focus_in)
        self.entry.connect("focus-out-event", self.on_entry_focus_out)
        hbox.pack_start(self.entry, padding = 5)
        
        button_add = gtk.Button()
        button_add.set_image(gtk.image_new_from_stock("gtk-add", gtk.ICON_SIZE_BUTTON))
        button_add.connect("clicked", self.on_button_add_clicked)
        hbox.pack_start(button_add, expand = False, padding = 5)

        button_refresh = gtk.Button()
        button_refresh.set_image(gtk.image_new_from_stock("gtk-refresh", gtk.ICON_SIZE_BUTTON))
        button_refresh.connect("clicked", self.on_button_refresh_clicked)
        hbox.pack_start(button_refresh, expand = False, padding = 5)
        
        # icon, screen_name, user.id, description, followicon, follwoericon, following, follower
        self.store = gtk.ListStore(gtk.gdk.Pixbuf, str, gobject.TYPE_INT64, str, gtk.gdk.Pixbuf, gtk.gdk.Pixbuf, bool, bool)
        self.iconstore.add_store(self.store, 2)
        
        # sort order by screen_name ASC
        self.store.set_sort_column_id(3, gtk.SORT_ASCENDING)
        
        # setup treeview
        self.treeview = gtk.TreeView(self.store)
        self.treeview.set_headers_visible(True)
        self.treeview.set_headers_clickable(True)
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
        col_name.set_clickable(True)
        col_name.connect("clicked", self.on_column_clicked, 1)
        self.treeview.append_column(col_name)
        
        col_following = gtk.TreeViewColumn("Following?", gtk.CellRendererPixbuf(), pixbuf = 4)
        col_following.set_clickable(True)
        col_following.connect("clicked", self.on_column_clicked, 6)
        self.treeview.append_column(col_following)
        
        col_follower = gtk.TreeViewColumn("Follower?", gtk.CellRendererPixbuf(), pixbuf = 5)
        col_follower.set_clickable(True)
        col_follower.connect("clicked", self.on_column_clicked, 7)
        self.treeview.append_column(col_follower)
        
        self.scrwin = gtk.ScrolledWindow()
        self.scrwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self.scrwin.set_shadow_type(gtk.SHADOW_NONE)
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
                user.screen_name, TwitterTools.replace_amp(user.name))
            is_friend = user.id in self.twitter.following
            is_follower = user.id in self.twitter.followers
            icon = self.iconstore.get(user)
            
            following = self.pix_follow if is_friend else self.pix_nofollow
            follower = self.pix_follow if is_follower else self.pix_nofollow
            
            gtk.gdk.threads_enter()
            self.store.append((icon, text, user.id, user.screen_name, following, follower, is_friend, is_follower))
            gtk.gdk.threads_leave()
        
        self.userids = now
    
    def activate_user(self, sname):
        # create new timeline
        if sname == "": return True
        
        user = self.twitter.get_user_from_screen_name(sname)
        if user != None:
            self.twitter.new_timeline("@%s" % sname, "user_timeline",
                                      user = user.id)
        else:
            self.twitter.new_timeline("@%s" % sname, "user_timeline",
                                      user = sname, is_screen_name = True)
    
    def refresh_user_information(self, user):        
        bio = """
<big><b>%s</b></big> - %s
<b>%d</b> following, <b>%d</b> followers, <b>%d</b> tweets
<small><span foreground='#666666'>Location: %s
Bio: %s
Web: %s</span></small>
""" % (
            user.screen_name,
            user.name,
            user.friends_count,
            user.followers_count,
            user.statuses_count,
            user.location,
            unicode(user.description).replace("\n", ""),
            "<a href='%s'>%s</a>" % (user.url, user.url) if user.url != None else None,
            )

        if user.protected: bio += "\n[Protected user]"
        bio = TwitterTools.replace_amp(bio)
        
        img = gtk.image_new_from_pixbuf(self.iconstore.get(user))
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
        label.set_property("height-request", 150)
        
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
    
    ### Event
    def on_entry_activate(self, entry):
        sname = entry.get_text()
        return self.activate_user(sname)
    
    def on_button_add_clicked(self, button):
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
            self.twitter.api_wrapper(self.twitter.api.friends_create, uid)
            button.set_image(gtk.image_new_from_stock("gtk-apply", gtk.ICON_SIZE_BUTTON))
            button.set_label("Following")
            self.twitter.following.add(uid)
        else:
            self.twitter.api_wrapper(self.twitter.api.friends_destroy, uid)
            button.set_image(gtk.image_new_from_stock("gtk-add", gtk.ICON_SIZE_BUTTON))
            button.set_label("Follow")
            self.twitter.following.remove(uid)

    def on_column_clicked(self, column, n):
        nowsort, is_asc = self.treeview.get_model().get_sort_column_id()
        
        if nowsort == n:
            self.treeview.get_model().set_sort_column_id(n, gtk.SORT_ASCENDING if is_asc != gtk.SORT_ASCENDING else gtk.SORT_DESCENDING)
        else:
            self.treeview.get_model().set_sort_column_id(n, gtk.SORT_ASCENDING if n == 1 else gtk.SORT_DESCENDING)

    def on_button_refresh_clicked(self, button):
        builder = gtk.Builder()
        gladefile = os.path.join(os.path.dirname(__file__), "glade/getfollow.glade")
        builder.add_from_file(gladefile)
        builder.connect_signals(self)
        win = builder.get_object("assistant_getfollow")
        win.show_all()
    
    def on_assistant_getfollow_prepare(self, assistant, page):
        pass

    def on_assistant_getfollow_apply(self, assistant):
        assistant.destroy()
    
    def on_assistant_getfollow_cancel(self, assistant):
        assistant.destroy()
