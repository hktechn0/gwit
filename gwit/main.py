#-*- coding: utf-8 -*-

'''gwit Main class
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

import sys
import os.path
import threading
import random
import time
import uuid

try:
    import pynotify
except ImportError:
    USE_NOTIFY = False
else:
    USE_NOTIFY = True

from timeline import Timeline
from statusview import StatusView
from timelinethread import BaseThread
from twitterapi import TwitterAPI
from iconstore import IconStore
from saveconfig import Config
from userselection import UserSelection
from listsselection import ListsSelection, ListsView
from statusdetail import StatusDetail
from twittertools import TwitterTools
from getfriendswizard import GetFriendsWizard

# Main Class
class Main(object):
    # Default settings
    interval = (300, 300, -1)
    msgfooter = u""
    alloc = gtk.gdk.Rectangle(0, 0, 240, 320)
    scounts = (20, 200)
    iconmode = True
    userstream = True
    # My status, Mentions to me, Reply to, Reply to user, Selected user
    status_color = ("#CCCCFF", "#FFCCCC", "#FFCC99", "#FFFFCC", "#CCFFCC")
    
    # Set Default Mention Flag
    re = None
    
    _toggle_change_flag = False
    
    # Twitpic API Key (gwit)
    twitpic_apikey = "bf867400573d27a8fe61b09e3cbf5a50"
    
    # Constractor
    def __init__(self, screen_name, keys):
        # Gtk Multithread Setup
        if sys.platform == "win32":
            gobject.threads_init()
        else:
            gtk.gdk.threads_init()
        
        # force change gtk icon settings
        settings = gtk.settings_get_default()
        if not getattr(settings.props, 'gtk_button_images', True):
            settings.props.gtk_button_images = True
        
        # init status timelines
        self.timelines = list()
        self.tlhash = dict()
        self.timeline_mention = None
        
        # Twitter class instance
        self.twitter = TwitterAPI(screen_name, *keys)
        self.twitter.init_twitpic(self.twitpic_apikey)
        self.twitter.on_tweet_event = self.refresh_tweet
        self.twitter.on_notify_event = self.notify
        
        self.read_settings()
        
        # set event (show remaining api count)
        self.twitter.on_twitterapi_requested = self.on_timeline_refresh
        self.twitter.new_timeline = self.new_timeline
        
        # Get users
        self.twitter.get_followers_bg()
        if not self.userstream: self.twitter.get_following_bg()
        
        # init icon store
        IconStore.iconmode = self.iconmode
        self.iconstore = IconStore()
        
        # GtkBuilder instance
        self.builder = gtk.Builder()
        # Glade file input
        gladefile = os.path.join(os.path.dirname(__file__), "glade/gwit.glade")
        self.builder.add_from_file(gladefile)
        # Connect signals
        self.builder.connect_signals(self)
        
        self.notebook = self.builder.get_object("notebook1")
        self.textview = self.builder.get_object("textview1")
        self.btnupdate = self.builder.get_object("button1")
        self.charcount = self.builder.get_object("label1")
        self.dsettings = self.builder.get_object("dialog_settings")
        
        self.menu_tweet = self.builder.get_object("menu_tweet")
        self.builder.get_object("menuitem_tweet").set_submenu(self.menu_tweet)
        self.menu_timeline = self.builder.get_object("menu_timeline")
        self.builder.get_object("menuitem_timeline").set_submenu(self.menu_timeline)
        
        # set class variables
        Timeline.twitter = self.twitter
        StatusView.twitter = self.twitter
        StatusView.iconstore = self.iconstore
        StatusView.iconmode = self.iconmode
        StatusView.pmenu = self.menu_tweet
        BaseThread.twitter = self.twitter
        StatusView.favico_y = self.notebook.render_icon("gtk-about", gtk.ICON_SIZE_MENU)
        StatusView.favico_n = None
        StatusDetail.twitter = self.twitter
        StatusDetail.iconstore = self.iconstore
        ListsView.twitter = self.twitter
        ListsView.iconstore = self.iconstore
        UserSelection.twitter = self.twitter
        UserSelection.iconstore = self.iconstore
        GetFriendsWizard.twitter = self.twitter
        
        self.initialize()
    
    def main(self):
        window = self.builder.get_object("window1")
        
        # settings allocation
        window.resize(self.alloc.width, self.alloc.height)        
        window.show_all()
        
        # Start gtk main loop
        gtk.main()
    
    def read_settings(self):
        try:
            # Read settings
            d = Config.get_section("DEFAULT")
            self.interval = eval(d["interval"])
            self.alloc = eval(d["allocation"])
            self.scounts = eval(d["counts"])
            self.iconmode = eval(d["iconmode"])
            self.userstream = eval(d["userstream"])
            self.status_color = eval(d["color"])
            u = Config.get_section(self.twitter.my_name)
            self.msgfooter = u["footer"]
        except Exception, e:
            print "[Error] Read settings: %s" % e
    
    # Initialize Tabs (in another thread)
    def initialize(self):
        # Set Status Views
        for i in (("Home", "home_timeline", self.userstream),
                  ("@Mentions", "mentions")):
            # create new timeline and tab view
            self.new_timeline(*i)
        
        # Set statusbar (Show API Remaining)
        self.label_apilimit = gtk.Label()
        self.statusbar = self.builder.get_object("statusbar1")
        self.statusbar.pack_start(self.label_apilimit, expand = False, padding = 10)
        self.statusbar.show_all()
        
        # Users tab append
        users = UserSelection()
        self.new_tab(users, "Users")
        
        # Lists tab append
        lists = ListsSelection()
        self.new_tab(lists, "Lists")
        
        self.notebook.set_current_page(0)
    
    # Window close event
    def close(self, widget):
        # Save Allocation (window position, size)
        alloc = repr(self.builder.get_object("window1").allocation)
        Config.save("DEFAULT", "allocation", alloc)
        
        self.save_settings()
        
        for i in self.timelines:
            if i != None:
                i.destroy()
                if i.timeline != None: i.timeline.join(1)
                if i.stream != None: i.stream.join(1)
        
        gtk.main_quit()
    
    # Create new Timeline and append to notebook
    def new_timeline(self, label, method, userstream = False, *args, **kwargs):
        # Create Timeline Object
        tl = Timeline()
        
        if method == "filter":
            tl.set_stream("filter", kwargs)
        else:
            interval = self.get_default_interval(method)        
            tl.set_timeline(method, interval, self.scounts, args, kwargs)
            # Put error to statubar
            tl.timeline.on_twitterapi_error = self.on_twitterapi_error
        
        # for Event
        tl.view.new_timeline = self.new_timeline
        
        # Add Notebook (Tab view)
        uid = self.new_tab(tl, label, tl)
        
        # Set color
        tl.view.set_color(self.status_color)
        
        if method == "mentions":
            self.timeline_mention = uid
            tl.on_status_added = self.on_mentions_added
        else:
            tl.on_status_added = self.on_status_added
        
        # Put tweet information to statusbar
        tl.view.on_status_selection_changed = self.on_status_selection_changed
        # Reply on double click
        tl.view.on_status_activated = self.on_status_activated
       
        # Set UserStream parameter
        if userstream:
            tl.set_stream("user")
        
        tl.start_stream()
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
        self.timelines.append(timeline)
        
        # Label
        lbl = gtk.Label(label)
        
        box = gtk.HBox()
        box.pack_start(lbl, True, True)
        box.pack_start(button, False, False)
        box.show_all()
        
        if timeline != None:
            button.connect("button-press-event", self.on_notebook_tabbar_button_press)
        
        # append
        self.notebook.append_page(widget, box)
        self.notebook.show_all()
        self.notebook.set_current_page(n)

        return uid
    
    def get_selected_status(self):
        tab = self.get_current_tab()
        if tab != None:
            return tab.view.get_selected_status()
    
    def get_current_tab_n(self):
        return self.notebook.get_current_page()
    
    def get_current_tab(self):
        return self.timelines[self.notebook.get_current_page()]
    
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
        self.reply_to_status(status)
    
    def reply_to_status(self, status):
        self.re = status.id
        name = status.user.screen_name
        
        buf = self.textview.get_buffer()
        buf.set_text("@%s " % (name))
        self.textview.grab_focus()
    
    # Color selection dialog run for settings
    def color_dialog_run(self, title, color, entry):
        # Sample treeview setup
        store = gtk.ListStore(gtk.gdk.Pixbuf, str, str)
        treeview = gtk.TreeView(store)
        cellp = gtk.CellRendererPixbuf()
        colp = gtk.TreeViewColumn("icon", cellp, pixbuf = 0)
        cellt = gtk.CellRendererText()
        cellt.set_property("wrap-mode", pango.WRAP_CHAR)
        colt = gtk.TreeViewColumn("status", cellt, markup = 1)
        colp.add_attribute(cellp, "cell-background", 2)
        colt.add_attribute(cellt, "cell-background", 2)
        treeview.append_column(colp)
        treeview.append_column(colt)
        
        status = self.twitter.statuses.values()[0]
        store.append((self.iconstore.get(status.user),
                      "<b>%s</b>\n%s" % (status.user.screen_name, status.text),
                      color))
        
        def on_changed_cursor(view):
            view.get_selection().unselect_all()
        
        treeview.set_property("can-focus", False)
        treeview.set_headers_visible(False)
        treeview.connect("cursor-changed", on_changed_cursor)
        treeview.show()
        
        swin = gtk.ScrolledWindow()
        swin.add(treeview)
        swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_NEVER)
        swin.show()
        
        label = gtk.Label("Sample")
        label.set_justify(gtk.JUSTIFY_LEFT)
        label.set_padding(0, 10)
        label.set_alignment(0, 0.5)
        label.show()
        
        def on_colorselection_color_changed(colorselection, liststore):
            strcolor = colorselection.get_current_color().to_string()
            liststore.set_value(liststore.get_iter_first(), 2, strcolor)
        
        # Dialog setup
        dialog = gtk.ColorSelectionDialog(title)
        selection = dialog.get_color_selection()
        selection.set_current_color(gtk.gdk.color_parse(color))
        selection.connect("color-changed", on_colorselection_color_changed, store)
        
        selection.pack_start(label)
        selection.pack_start(swin)
        
        dialog.show_all()
        
        if dialog.run() == -5:
            color = selection.get_current_color().to_string()
            entry.set_text(color)
        else:
            color = None
        
        dialog.destroy()
        
        return color
    
    def status_update_thread(self, status):
        t = threading.Thread(target = self._status_update, args = (status,))
        t.start()
    
    def _status_update(self, status):
        args = dict()

        gtk.gdk.threads_enter()
        self.textview.set_sensitive(False)
        self.btnupdate.set_sensitive(False)
        gtk.gdk.threads_leave()
        
        if self.re != None:
            args["in_reply_to_status_id"] = self.re
        elif self.msgfooter != "":
            status = u"%s %s" % (status, self.msgfooter)
        
        resp = self.twitter.api_wrapper(self.twitter.api.status_update,
                                        status, **args)
        
        gtk.gdk.threads_enter()
        if resp != None:
            self.clear_textview()
            self.re = None
        
        self.textview.set_sensitive(True)
        self.btnupdate.set_sensitive(True)
        self.textview.grab_focus()
        gtk.gdk.threads_leave()
    
    def get_default_interval(self, method):
        if method == "home_timeline":
            interval = self.interval[0]
        elif method == "mentions":
            interval = self.interval[1]
        else:
            interval = self.interval[2]

        return interval

    def save_settings(self):
        conf = (("DEFAULT", "interval", self.interval),
                ("DEFAULT", "counts", self.scounts),
                ("DEFAULT", "iconmode", self.iconmode),
                ("DEFAULT", "userstream", self.userstream),
                ("DEFAULT", "color", self.status_color),
                (self.twitter.my_name, "footer", self.msgfooter))
        Config.save_section(conf)

    # desktop notify
    def notify(self, title, text, icon_user = None):
        if USE_NOTIFY:
            notify = pynotify.Notification(title, text)
            if icon_user:
                icon = self.iconstore.get(icon_user)
                notify.set_icon_from_pixbuf(icon)
            notify.show()
    
    def refresh_tweet(self, i):
        for tl in self.timelines:
            if tl: tl.view.reset_status_text()
    
    
    ########################################
    # Original Events
    
    # status added event
    def on_status_added(self, i):
        status = self.twitter.statuses[i]
        myid = self.twitter.my_id
        myname = self.twitter.my_name
        
        if status.in_reply_to_user_id == myid or status.text.find("@%s" % myname) >= 0:
            # add mentions tab
            mentiontab = self.timelines[self.tlhash[self.timeline_mention]]
            if status.id not in mentiontab.get_timeline_ids():
                mentiontab.timeline.add_statuses(((status,)))
    
    def on_mentions_added(self, i):
        status = self.twitter.statuses[i]
        self.notify("@%s mentioned you." % status.user.screen_name,
                    status.text, status.user)
    
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
        self.builder.get_object("menuitem_tweet").set_sensitive(True)
        self.statusbar.pop(0)
        self.statusbar.push(0, TwitterTools.get_footer(status))
    
    # status activated event (to Reply
    def on_status_activated(self, status):
        self.reply_to_status(status)
    
    # show error on statusbar
    def on_twitterapi_error(self, timeline, e):
        if e.code == 400:
            message = "API rate limiting. Reset: %s" % (
                self.twitter.api.ratelimit_reset.strftime("%H:%M:%S"))
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
            self.status_update_thread(txt)
        else:
            # Reload timeline if nothing in textview
            n = self.get_current_tab_n()
            self.re = None
            if self.timelines[n] != None:
                self.timelines[n].reload()
    
    # key_press textview (for update status when press Ctrl + Enter)
    def on_textview1_key_press_event(self, textview, event):
        # Enter == 65293
        if event.keyval == 65293 and event.state & gtk.gdk.CONTROL_MASK:
            txt = self.get_textview()
            
            # if update button enabled (== len(text) <= 140
            if self.btnupdate.get_sensitive() and txt != "":
                self.status_update_thread(txt)
            
            return True
    
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
            self.textview.set_sensitive(False)
            self.btnupdate.set_sensitive(False)
            
            message = self.get_textview()
            
            t = threading.Thread(target = self._twitpic_upload, args = (filename, message))
            t.start()
    
    def _twitpic_upload(self, filename, message):
        res = self.twitter.twitpic.upload(filename, message)
        
        try:
            gtk.gdk.threads_enter()
            self.add_textview(" %s" % res["url"])
        except KeyError:
            print >>sys.stderr, "[Error] Cannot upload Twitpic.\n%s" % (res)
        finally:
            self.textview.set_sensitive(True)
            self.btnupdate.set_sensitive(True)
            gtk.gdk.threads_leave()
    
    # Timeline Tab Close
    def on_tabclose_clicked(self, widget, uid):
        n = self.tlhash[uid]
        del self.tlhash[uid]

        if self.timeline_mention == uid:
            self.timeline_mention = None
        
        self.notebook.remove_page(n)
        
        if self.timelines[n] != None:
            self.timelines[n].destroy()
        
        del self.timelines[n]
        
        for i, m in self.tlhash.iteritems():
            if m > n: self.tlhash[i] -= 1
        
        p = self.notebook.get_current_page()
        self.on_notebook1_switch_page(self.notebook, self.notebook.get_nth_page(p), p)
    
    # Tab right clicked
    def on_notebook_tabbar_button_press(self, widget, event):
        if event.button == 3:
            self.menu_timeline.popup(None, None, None, event.button, event.time)
    
    # Character count
    def on_textbuffer1_changed(self, textbuffer):
        n = textbuffer.get_char_count()

        if self.re == None and self.msgfooter != "":
            n += len(self.msgfooter) + 1
        
        if n <= 140:
            self.charcount.set_text(str(n))
            self.btnupdate.set_sensitive(True)
        else:
            self.charcount.set_markup("<b><span foreground='#FF0000'>%s</span></b>" % n)
            self.btnupdate.set_sensitive(False)
    
    # Help - About menu
    def on_menuitem_about_activate(self, menuitem):
        self.builder.get_object("dialog_about").show_all()
        return True

    # About dialog closed
    def on_dialog_about_response(self, dialog, response_id):
        dialog.hide_all()
    
    # disable menu when switched tab
    def on_notebook1_switch_page(self, notebook, page, page_num):
        self.builder.get_object("menuitem_tweet").set_sensitive(False)
        menuitem_timeline = self.builder.get_object("menuitem_timeline")
        menuitem_timeline.set_sensitive(False)
        if page_num < 0: return False
        
        tab = self.timelines[page_num]
        if tab != None and tab.timeline != None:
            self._toggle_change_flg = True
            tl = tab.timeline
            method = tl.method
            default = self.get_default_interval(method)
            
            if default == -1: default = None
            
            menu_default = self.builder.get_object("menuitem_time_default")
            menu_default.get_child().set_text("Default (%s)" % default)
            
            interval = tl.interval
            
            if interval == default:
                menu_default.set_active(True)
            elif interval == -1:
                self.builder.get_object("menuitem_time_none").set_active(True)
            elif interval == 600:
                self.builder.get_object("menuitem_time_600").set_active(True)
            elif interval == 300:
                self.builder.get_object("menuitem_time_300").set_active(True)
            elif interval == 120:
                self.builder.get_object("menuitem_time_120").set_active(True)
            elif interval == 60:
                self.builder.get_object("menuitem_time_60").set_active(True)
            elif interval == 30:
                self.builder.get_object("menuitem_time_30").set_active(True)
            
            self._toggle_change_flg = False
            menuitem_timeline.set_sensitive(True)
    
    # Streaming API tab
    def on_menuitem_streaming_activate(self, menuitem):
        dialog = gtk.MessageDialog(buttons = gtk.BUTTONS_OK)
        dialog.set_markup("Please enter track keywords.")
        dialog.format_secondary_markup("Examples: <i>hashtag, username, keyword</i>\n(Split comma. Unnecessary #, @)")
        entry = gtk.Entry()
        dialog.vbox.pack_start(entry)
        dialog.show_all()
        dialog.run()
        text = entry.get_text()
        dialog.destroy()
        
        params = {"track" : text.split(",")}
        self.new_timeline("Stream: %s" % text, "filter", track = params)

    def on_menuitem_shorten_activate(self, menuitem):
        self.textview.set_sensitive(False)
        self.btnupdate.set_sensitive(False)
        
        text = self.get_textview()
        text = TwitterTools.url_shorten(text)
        self.clear_textview()
        self.add_textview(text)
        
        self.textview.set_sensitive(True)
        self.btnupdate.set_sensitive(True)
    
    ########################################
    # Tweet menu event
    
    def on_menuitem_reply_activate(self, menuitem):
        self.reply_to_selected_status()
    
    # Retweet menu clicked
    def on_menuitem_retweet_activate(self, memuitem):
        status = self.get_selected_status()
        self.twitter.api_wrapper(self.twitter.api.status_retweet, status.id)
        
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
                          "user_timeline", user = status.user.id)
    
    # Status detail
    def on_menuitem_detail_activate(self, menuitem):
        status = self.get_selected_status()
        detail = StatusDetail(status)
        self.new_tab(detail, "S: %d" % status.id)
    
    # favorite
    def on_menuitem_fav_activate(self, menuitem):
        self.get_current_tab().favorite_selected_status()
    
    # Destroy status
    def on_menuitem_destroy_activate(self, menuitem):
        status = self.get_selected_status()
        self.twitter.api_wrapper(self.twitter.api.status_destroy, status.id)
    
    ########################################
    # Timeline menu Event
    
    def change_interval(self, interval):
        if self._toggle_change_flg: return
        
        tl = self.get_current_tab().timeline
        
        if interval == 0:
            method = tl.api_method.func_name
            interval = self.get_default_interval(method)
        
        old = tl.interval
        tl.interval = interval
        if old == -1: tl.lock.set()
    
    def on_menuitem_time_600_toggled(self, menuitem):
        if menuitem.get_active() == True:
            self.change_interval(600) 
    def on_menuitem_time_300_toggled(self, menuitem):
        if menuitem.get_active() == True:
            self.change_interval(300)
    def on_menuitem_time_120_toggled(self, menuitem):
        if menuitem.get_active() == True:
            self.change_interval(120)
    def on_menuitem_time_60_toggled(self, menuitem):
        if menuitem.get_active() == True:
            self.change_interval(60)
    def on_menuitem_time_30_toggled(self, menuitem):
        if menuitem.get_active() == True:
            self.change_interval(30)
    def on_menuitem_time_default_toggled(self, menuitem):
        if menuitem.get_active() == True:
            self.change_interval(0)
    def on_menuitem_time_none_toggled(self, menuitem):
        if menuitem.get_active() == True:
            self.change_interval(-1)
    
    ########################################
    # Settings dialog event
    
    # Settings
    def on_imageitem_settings_activate(self, menuitem):
        home, mentions, other = self.interval
        
        # interval
        if home == -1:
            self.builder.get_object("checkbutton_home").set_active(False)
        if mentions == -1:
            self.builder.get_object("checkbutton_mentions").set_active(False)
        if other == -1:
            self.builder.get_object("checkbutton_other").set_active(False)        
        self.builder.get_object("spinbutton_home").set_value(home)
        self.builder.get_object("spinbutton_mentions").set_value(mentions)
        self.builder.get_object("spinbutton_other").set_value(other)
        
        # status counts
        self.builder.get_object("spinbutton_firstn").set_value(self.scounts[0])
        self.builder.get_object("spinbutton_maxn").set_value(self.scounts[1])
        # show icons
        self.builder.get_object("checkbutton_showicon").set_active(self.iconmode)
        # userstream
        self.builder.get_object("checkbutton_userstream").set_active(self.userstream)
        
        # footer
        self.builder.get_object("entry_footer").set_text(self.msgfooter)

        # OAuth information
        self.builder.get_object("entry_myname").set_text(self.twitter.my_name)
        self.builder.get_object("entry_ckey").set_text(self.twitter.api.oauth.ckey)
        self.builder.get_object("entry_csecret").set_text(self.twitter.api.oauth.csecret)
        self.builder.get_object("entry_atoken").set_text(self.twitter.api.oauth.atoken)
        self.builder.get_object("entry_asecret").set_text(self.twitter.api.oauth.asecret)
        
        # Color
        color_entrys = (self.builder.get_object("entry_color_mytweet"),
                        self.builder.get_object("entry_color_mentions"),
                        self.builder.get_object("entry_color_replyto"),
                        self.builder.get_object("entry_color_replyto_user"),
                        self.builder.get_object("entry_color_selected_user"))
        for i, entry in enumerate(color_entrys):
            entry.set_text(self.status_color[i])
        
        self.dsettings.show()
    
    # Close or Cancel
    def on_dialog_settings_close(self, widget):
        self.dsettings.hide()
    
    # OK
    def on_dialog_settings_ok(self, widget):
        # interval
        if self.builder.get_object("checkbutton_home").get_active():
            home = self.builder.get_object("spinbutton_home").get_value_as_int()
        else:
            self.charcount.set_markup("<b><span foreground='#FF0000'>%s</span></b>" % n)
            self.btnupdate.set_sensitive(False)
            home = -1
        if self.builder.get_object("checkbutton_mentions").get_active():
            mentions = self.builder.get_object("spinbutton_mentions").get_value_as_int()
        else:
            mentions = -1
        if self.builder.get_object("checkbutton_other").get_active():
            other = self.builder.get_object("spinbutton_other").get_value_as_int()
        else:
            other = -1

        self.interval = (home, mentions, other)
        
        # status counts
        self.scounts = (
            self.builder.get_object("spinbutton_firstn").get_value_as_int(),
            self.builder.get_object("spinbutton_maxn").get_value_as_int())
        
        # show icons
        self.iconmode = self.builder.get_object("checkbutton_showicon").get_active()
        
        # userstream
        self.userstream = self.builder.get_object("checkbutton_userstream").get_active()
        
        # footer
        self.msgfooter = unicode(self.builder.get_object("entry_footer").get_text())
        
        # Color
        self.status_color = (self.builder.get_object("entry_color_mytweet").get_text(),
                             self.builder.get_object("entry_color_mentions").get_text(),
                             self.builder.get_object("entry_color_replyto").get_text(),
                             self.builder.get_object("entry_color_replyto_user").get_text(),
                             self.builder.get_object("entry_color_selected_user").get_text())
        for t in self.timelines:
            if t != None:
                t.view.set_color(self.status_color)
        
        self.save_settings()
        self.dsettings.hide()
    
    # toggle checkbox
    def on_checkbutton_home_toggled(self, checkbutton):
        sb = self.builder.get_object("spinbutton_home")
        sb.set_sensitive(checkbutton.get_active())
    def on_checkbutton_mentions_toggled(self, checkbutton):
        sb = self.builder.get_object("spinbutton_mentions")
        sb.set_sensitive(checkbutton.get_active())
    def on_checkbutton_other_toggled(self, checkbutton):
        sb = self.builder.get_object("spinbutton_other")
        sb.set_sensitive(checkbutton.get_active())
    
    def on_entry_color_changed(self, entry):
        entry.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(entry.get_text()))
    
    # Color selection dialog open    
    def on_button_color1_clicked(self, widget):
        entry = self.builder.get_object("entry_color_mytweet")
        self.color_dialog_run("My status", entry.get_text(), entry)
    def on_button_color2_clicked(self, widget):
        entry = self.builder.get_object("entry_color_mentions")
        self.color_dialog_run("Mentions to me", entry.get_text(), entry)
    def on_button_color3_clicked(self, widget):
        entry = self.builder.get_object("entry_color_replyto")
        self.color_dialog_run("Reply to", entry.get_text(), entry)
    def on_button_color4_clicked(self, widget):
        entry = self.builder.get_object("entry_color_replyto_user")
        self.color_dialog_run("Reply to user", entry.get_text(), entry)
    def on_button_color5_clicked(self, widget):
        entry = self.builder.get_object("entry_color_selected_user")
        self.color_dialog_run("Selected user", entry.get_text(), entry)
