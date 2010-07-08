#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk
import gobject

import sys
import os.path
import threading
import random
import time
import uuid

from timeline import timeline
from twitterapi import twitterapi
from iconstore import IconStore
from saveconfig import save_configs, save_config, get_config
from userselection import UserSelection
from listsselection import ListsSelection
import twittertools

# Main Class
class Main:
    # init status timelines
    timelines = list()
    tlhash = dict()
    # status message fotter
    msgfooter = unicode()

    # Twitpic API Key (gwit)
    twitpic_apikey = "bf867400573d27a8fe61b09e3cbf5a50"
    
    # Constractor
    def __init__(self, keys, maxn = 200, iconmode = True):
        # Gtk Multithread Setup
        gtk.gdk.threads_init()
        gobject.threads_init()
        
        # Twitter class instance
        self.twitter = twitterapi(keys, maxn)
        self.twitter.init_twitpic(self.twitpic_apikey)
        
        # GtkBuilder instance
        self.builder = gtk.Builder()
        # Glade file input
        gladefile = os.path.join(os.path.dirname(__file__), "glade/gwit.glade")
        self.builder.add_from_file(gladefile)
        # Connect signals
        self.builder.connect_signals(self)
        
        self.notebook = self.builder.get_object("notebook1")
        self.textview = self.builder.get_object("textview1")
        self.textview.get_buffer().connect("changed", self.on_textbuffer_changed)
        self.btnupdate = self.builder.get_object("button1")
        self.charcount = self.builder.get_object("label1")
        
        # Set Default Mention Flag
        self.re = 0
        self.iconmode = iconmode
        
        # init icon store
        self.icons = IconStore(iconmode)
        # set tools
        self.twtools = twittertools.TwitterTools()
        
        self.initialize(keys, maxn)
    
    def main(self):
        gtk.gdk.threads_enter()
        window = self.builder.get_object("window1")
        
        # settings allocation
        try:
            alloc = get_config("DEFAULT", "allocation")
            alloc = eval(alloc)
            window.resize(alloc.width, alloc.height)
        except:
            print >>sys.stderr, "[warning] Window allocation not defined"
        
        window.show_all()

        # Start gtk main loop
        gtk.main()
        gtk.gdk.threads_leave()
    
    # Initialize Tabs (in another thread)
    def initialize(self, keys, maxn):
        # Set Status Views
        for i in (("Home", "home_timeline", 30),
                  ("Mentions", "mentions", 300)):
            # create new timeline and tab view
            self.new_timeline(*i)

        # Set statusbar (Show API Remaining)
        self.label_apilimit = gtk.Label()
        self.statusbar = self.builder.get_object("statusbar1")
        self.statusbar.pack_start(
            self.label_apilimit, expand = False, padding = 10)
        self.statusbar.show_all()        
        
        # Users tab append
        users = UserSelection(self.twitter, self.icons)
        users.new_timeline = self.new_timeline
        self.new_tab(users, "Users")
        
        # Lists tab append
        lists = ListsSelection(self.twitter, self.icons)
        lists.new_timeline = self.new_timeline
        self.new_tab(lists, "Lists")
        
        self.notebook.set_current_page(0)
    
    # Window close event
    def close(self, widget):
        # Save Allocation (window position, size)
        alloc = repr(widget.allocation)
        save_config("DEFAULT", "allocation", alloc)
        
        # All tab close
        for i in dict(self.tlhash).iterkeys():
            self.on_tabclose_clicked(None, i)
        
        gtk.main_quit()
    
    # Create new Timeline and append to notebook
    def new_timeline(self, label, method, sleep, *args, **kwargs):
        # Create Timeline Object
        tl = timeline(self.twitter, self.icons, self.iconmode)        
        menu = self.builder.get_object("menu_timeline")
        
        # Add Popup Menu
        tl.add_popup(menu)
        
        # Treeview double click signal connect
        tl.treeview.connect(
            "row-activated",
            self.on_treeview_row_activated)
        
        # Event handler and extern function set
        tl.new_timeline = self.new_timeline
        tl.on_status_selection_changed = self.on_status_selection_changed
        if method != "mentions":
            tl.on_status_added = self.on_status_added
        
        # Add Notebook (Tab view)
        self.new_tab(tl.scrwin, label, tl)
        
        # Start sync timeline
        tl.init_timeline(method, sleep, args, kwargs)
        tl.timeline.on_timeline_refresh = self.on_timeline_refresh
        tl.timeline.on_twitterapi_error = self.on_twitterapi_error
        tl.start_timeline()
    
    # Append Tab to Notebook
    def new_tab(self, widget, label, timeline = None):
        # close button
        button = gtk.Button()
        button.set_relief(gtk.RELIEF_NONE)
        icon = gtk.image_new_from_stock("gtk-close", gtk.ICON_SIZE_MENU)
        button.set_image(icon)
        
        uid = uuid.uuid4().int
        button.connect("clicked", self.on_tabclose_clicked, uid)
        n = self.notebook.get_n_pages()
        self.tlhash[uid] = n
        
        # Label
        lbl = gtk.Label(label)
        
        box = gtk.HBox()
        box.pack_start(lbl, True, True)
        box.pack_start(button, False, False)
        box.show_all()
        
        # append
        self.notebook.append_page(widget, box)
        self.notebook.show_all()
        self.notebook.set_current_page(n)
        self.timelines.append(timeline)
    
    def get_selected_status(self):
        n = self.notebook.get_current_page()
        return self.timelines[n].get_selected_status()
    
    def get_current_tab(self):
        return self.notebook.get_current_page()

    # Get text
    def get_textview(self):
        buf = self.textview.get_buffer()
        start, end = buf.get_start_iter(), buf.get_end_iter()
        return buf.get_text(start, end)
    
    # Set text
    def set_textview(self, txt, focus = False):
        buf = self.textview.get_buffer()
        buf.set_text(txt)
        if focus: self.textview.grab_focus()
    
    # Add text at cursor
    def add_textview(self, txt, focus = False):
        buf = self.textview.get_buffer()
        buf.insert_at_cursor(txt)    
        if focus: self.textview.grab_focus()
    
    # Clear text
    def clear_textview(self, focus = False):
        self.set_textview("", focus)
    
    # Reply to selected status
    def reply_to_selected_status(self):
        status = self.get_selected_status()
        self.re = status.id
        name = status.user.screen_name
        
        buf = self.textview.get_buffer()
        buf.set_text("@%s " % (name))
        self.textview.grab_focus()
    
    
    ########################################
    # Original Events
    
    # status added event
    def on_status_added(self, i):
        status = self.twitter.statuses[i]
        myname = self.twitter.myname
        if status.in_reply_to_screen_name == myname or \
                status.text.find("@%s" % myname) >= 0:
            self.timelines[1].timeline.add(set((status.id,)))
    
    # timeline refreshed event
    def on_timeline_refresh(self):
        if self.twitter.api.ratelimit_iplimit != -1:
            msg = "%d/%d %d/%d" % (
                self.twitter.api.ratelimit_remaining,
                self.twitter.api.ratelimit_limit,
                self.twitter.api.ratelimit_ipremaining,
                self.twitter.api.ratelimit_iplimit)
        else:
            msg = "%d/%d" % (
                self.twitter.api.ratelimit_remaining,
                self.twitter.api.ratelimit_limit)
        
        self.label_apilimit.set_text("API: %s" % msg)
    
    # status selection changed event
    def on_status_selection_changed(self, status):
        self.statusbar.pop(0)
        self.statusbar.push(0, self.twtools.get_footer(status))
    
    # show error on statusbar
    def on_twitterapi_error(self, timeline, e):
        if e.code == 400:
            message = "API rate limiting. Reset: %s" % self.twitter.api.ratelimit_reset.strftime("%H:%M:%S")
        elif e.code == 500 or e.code == 502:
            message = "Twitter something is broken. Try again later."
        elif e.code == 503:
            message = "Twitter is over capacity. Try again later."
        else:
            message = "Oops! Couldn't reload timeline."
        
        self.statusbar.pop(0)        
        self.statusbar.push(0, "[Error] %s %s (%s)" % (timeline.getName(), message, e.code))
    
    ########################################
    # Gtk Signal Events
    
    # Status Update
    def on_button1_clicked(self, widget):
        txt = self.get_textview()
        
        if txt != "":
            # Status Update
            self.twitter.status_update(txt, self.re, self.msgfooter)
        else:
            # Reload timeline if nothing in textview
            n = self.get_current_tab()
            if self.timelines[n] != None:
                self.timelines[n].reload()
        
        self.re = None
        self.clear_textview()
    
    # Update menu popup
    def on_button2_button_release_event(self, widget, event):
        menu = self.builder.get_object("menu_update")
        menu.popup(None, None, None, event.button, event.time)
    
    # Image upload for twitpic
    def on_menuitem_twitpic_activate(self, widget):
        dialog = gtk.FileChooserDialog("Upload Image...")
        dialog.add_button(gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        ret = dialog.run()
        filename = dialog.get_filename()
        dialog.destroy()
        
        if ret == gtk.RESPONSE_OK:
            f = open(filename)
            message = self.get_textview()
            res = self.twitter.twitpic.upload(f, message)
            self.add_textview(" %s" % res["url"])
    
    # Timeline Tab Close
    def on_tabclose_clicked(self, widget, uid):
        n = self.tlhash[uid]
        del self.tlhash[uid]
        
        self.notebook.remove_page(n)

        if self.timelines[n] != None:
            self.timelines[n].destroy()
        
        del self.timelines[n]
        
        for (i, m) in self.tlhash.iteritems():
            if m > n: self.tlhash[i] -= 1
    
    # Reply if double-clicked status
    def on_treeview_row_activated(self, treeview, path, view_column):
        self.reply_to_selected_status()
    
    def on_menuitem_reply_activate(self, menuitem):
        self.reply_to_selected_status()
    
    # Retweet menu clicked
    def on_menuitem_retweet_activate(self, memuitem):
        status = self.get_selected_status()
        self.twitter.api.status_retweet(status.id)
    
    # Retweet with comment menu clicked
    def on_menuitem_reteet_with_comment_activate(self, memuitem):
        status = self.get_selected_status()
        name = status.user.screen_name
        text = status.text
        
        self.re = None
        self.set_textview("RT @%s: %s" % (name, text), True)
    
    # Added user timeline tab
    def on_menuitem_usertl_activate(self, menuitem):
        status = self.get_selected_status()
        self.new_timeline("@%s" % status.user.screen_name,
                          "user_timeline", -1,
                          user = status.user.id)
    
    # favorite
    def on_menuitem_fav_activate(self, menuitem):
        status = self.get_selected_status()
        self.twitter.api.favorite_create(status.id)
    
    # Destroy status
    def on_Delete_activate(self, menuitem):
        status = self.get_selected_status()
        self.twitter.api.status_destroy(status.id)

    # key_press textview (for post status when press Ctrl + Enter)
    def on_textview1_key_press_event(self, textview, event):
        # Enter == 65293
        if event.keyval == 65293 and event.state & gtk.gdk.CONTROL_MASK:
            txt = self.get_textview()
            if len(txt) <= 140:
                self.twitter.status_update(txt, self.re, self.msgfooter)
                self.re = None
                self.clear_textview()

            return True
    
    # Character count
    def on_textbuffer_changed(self, textbuffer):
        n = textbuffer.get_char_count()
        if n <= 140:
            self.charcount.set_text(str(n))
            self.btnupdate.set_sensitive(True)
        else:
            self.charcount.set_markup("<b><span foreground='#FF0000'>%s</span></b>" % n)
            self.btnupdate.set_sensitive(False)
