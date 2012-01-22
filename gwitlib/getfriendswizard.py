#-*- coding: utf-8 -*-

'''Get Twitter following/followers wizard
'''

################################################################################
#
# Copyright (c) 2011 University of Tsukuba Linux User Group
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

import threading

class GetFriendsWizard(gtk.Assistant):
    twitter = None
    
    def __init__(self):
        gtk.Assistant.__init__(self)
        self.connect("cancel", self.on_cancel_close)
        self.connect("close", self.on_cancel_close)
        self.connect("apply", self.on_apply)
        
        # page1
        self.page1 = gtk.Label("""

This process may take a few minutes.
If you have too many followings/followers, 
you should mind remaining API limit.
(Get 100 followings/followers per call)

""")
        
        # page2
        self.chkfr = gtk.CheckButton("Get all friends")
        self.chkfo = gtk.CheckButton("Get all followers")
        self.chkfr.connect("toggled", self.on_check_toggled)
        self.chkfo.connect("toggled", self.on_check_toggled)
        
        box = gtk.VBox(spacing = 10)
        box.pack_start(self.chkfr)
        box.pack_end(self.chkfo)
        self.page2 = box
        
        # page3
        buf = gtk.TextBuffer()
        view = gtk.TextView(buf)
        self.page3 = gtk.ScrolledWindow()
        self.page3.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.page3.add(view)
        view.set_editable(False)
        
        # page4
        self.page4 = gtk.Label("""Get followings/followers information successfully!
There will add to user selection after few seconds.""")
        
        self.append_page(self.page1)
        self.set_page_title(self.page1, "Get followings/followers")
        self.set_page_type(self.page1, gtk.ASSISTANT_PAGE_INTRO)
        self.set_page_complete(self.page1, True)
        
        self.append_page(self.page2)
        self.set_page_title(self.page2, "Get followings/followers")
        self.set_page_type(self.page2, gtk.ASSISTANT_PAGE_CONFIRM)
        
        self.append_page(self.page3)
        self.set_page_title(self.page3, "Getting...")
        self.set_page_type(self.page3, gtk.ASSISTANT_PAGE_PROGRESS)
        self.set_page_complete(self.page3, False)
        
        self.append_page(self.page4)
        self.set_page_title(self.page4, "Complete!")
        self.set_page_type(self.page4, gtk.ASSISTANT_PAGE_SUMMARY)
    
    # get users
    def _get_users_in_thread(self):
        def p(buf, text):
            gtk.gdk.threads_enter()
            buf.insert_at_cursor(text)
            gtk.gdk.threads_leave()
        
        users_n = 0
        ids_to_get = list()
        users_exist = set(self.twitter.users.keys())
        
        log = self.page3.get_child().get_buffer()
        
        if self.chkfr.get_active():            
            p(log, "=== Getting friedns ===\n")
            
            p(log, "GET: friends_ids...\n")
            self.twitter.get_following()
            ids_to_get += list(self.twitter.following.difference(users_exist))
            p(log, "Friends: %d users (Getting %d users)\n" % (
                    len(self.twitter.following), len(ids_to_get)))
            
        if self.chkfo.get_active():
            p(log, "=== Getting followers ===\n")
            
            p(log, "GET: followers_ids...\n")
            self.twitter.get_followers()
            ids = list(self.twitter.followers.difference(users_exist))
            ids_to_get += ids
            p(log, "Followers: %d users (Getting %d users)\n" % (
                    len(self.twitter.followers), len(ids)))
        
        p(log, "=== Getting user data ===\n")
        while ids_to_get:
            p(log, "GET: ")
            
            ids_now = ids_to_get[:100]
            ids_to_get = ids_to_get[100:]
            
            r = self.twitter.api_wrapper(self.twitter.api.user_lookup, user_id = ids_now)
            self.twitter.add_users(r)
            
            users_n += len(r)
            p(log, "%d users\n" % users_n)
        
        p(log, "\nDone.\n")
        gtk.gdk.threads_enter()
        self.set_page_complete(self.page3, True)
        gtk.gdk.threads_leave()
    
    def on_cancel_close(self, widget):
        widget.hide_all()
        widget.destroy()

    def on_apply(self, assistant):
        threading.Thread(target = self._get_users_in_thread).start()
    
    # page2 checkbox
    def on_check_toggled(self, check):
        if self.chkfr.get_active() or self.chkfo.get_active():
            self.set_page_complete(self.page2, True)
        else:
            self.set_page_complete(self.page2, False)
