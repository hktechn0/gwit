#!/usr/bin/env python
#-*- coding: utf-8 -*-

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

from timeline import Timeline
from twitterapi import TwitterAPI
from iconstore import IconStore
from saveconfig import save_configs, save_config, get_config, get_configs
from userselection import UserSelection
from listsselection import ListsSelection
from statusdetail import StatusDetail
import twittertools

# Main Class
class Main:
    # init status timelines
    timelines = list()
    tlhash = dict()
    
    # Default settings
    interval = (60, 300, -1)
    msgfooter = unicode()
    alloc = gtk.gdk.Rectangle(0, 0, 240, 320)
    scounts = (20, 200)
    iconmode = True
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
        gtk.gdk.threads_init()
        gobject.threads_init()
        
        # Twitter class instance
        self.twitter = TwitterAPI(screen_name, *keys)
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
        self.btnupdate = self.builder.get_object("button1")
        self.charcount = self.builder.get_object("label1")
        self.dsettings = self.builder.get_object("dialog_settings")
        
        menu_tweet = self.builder.get_object("menu_tweet")
        self.builder.get_object("menuitem_tweet").set_submenu(menu_tweet)
        menu_timeline = self.builder.get_object("menu_timeline")
        self.builder.get_object("menuitem_timeline").set_submenu(menu_timeline)
        
        # set tools
        self.twtools = twittertools.TwitterTools()
        
        self.initialize()
    
    def main(self):
        gtk.gdk.threads_enter()
        window = self.builder.get_object("window1")
        
        # settings allocation
        window.resize(self.alloc.width, self.alloc.height)        
        window.show_all()
        
        # Start gtk main loop
        gtk.main()
        gtk.gdk.threads_leave()
    
    # Initialize Tabs (in another thread)
    def initialize(self):
        try:
            # Read settings
            d = get_configs("DEFAULT")
            self.interval = eval(d["interval"])
            self.alloc = eval(d["allocation"])
            self.scounts = eval(d["counts"])
            self.iconmode = eval(d["iconmode"])
            self.status_color = eval(d["color"])
            u = get_configs(self.twitter.myname)
            self.msgfooter = u["footer"]
        except Exception, e:
            print "[Error] Read settings: %s" % e
        
        # init icon store
        self.icons = IconStore(self.iconmode)
        
        # Set Status Views
        for i in (("Home", "home_timeline"),
                  ("Mentions", "mentions")):
            # create new timeline and tab view
            self.new_timeline(*i)
        
        # Set statusbar (Show API Remaining)
        self.label_apilimit = gtk.Label()
        self.statusbar = self.builder.get_object("statusbar1")
        self.statusbar.pack_start(self.label_apilimit, expand = False, padding = 10)
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
    def new_timeline(self, label, method, *args, **kwargs):
        # Create Timeline Object
        tl = Timeline(self.twitter, self.icons, self.iconmode)
        
        interval = self.get_default_interval(method)
        
        # Start sync timeline
        tl.init_timeline(method, interval, self.scounts, args, kwargs)
        tl.new_timeline = self.new_timeline
        
        # Add Notebook (Tab view)
        self.new_tab(tl.scrwin, label, tl)

       # Set color
        tl.set_color(self.status_color)
        
        if method != "mentions":
            tl.on_status_added = self.on_status_added
        
        # Set API Limit label
        tl.timeline.on_timeline_refresh = self.on_timeline_refresh
        # Put error to statubar
        tl.timeline.on_twitterapi_error = self.on_twitterapi_error
        
        # Put tweet information to statusbar
        tl.on_status_selection_changed = self.on_status_selection_changed
        # Reply on double click
        tl.on_status_activated = self.on_status_activated
        
        tl.start_timeline()        
        tl.add_popup(self.builder.get_object("menu_tweet"))
    
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
        store.append((self.icons.get(status.user),
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
    
    def get_default_interval(self, method):
        if method == "home_timeline":
            interval = self.interval[0]
        elif method == "mentions":
            interval = self.interval[1]
        else:
            interval = self.interval[2]

        return interval
    
    
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
        self.builder.get_object("menuitem_tweet").set_sensitive(True)
        self.statusbar.pop(0)
        self.statusbar.push(0, self.twtools.get_footer(status))
    
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
            self.twitter.status_update(txt, self.re, self.msgfooter)
        else:
            # Reload timeline if nothing in textview
            n = self.get_current_tab()
            if self.timelines[n] != None:
                self.timelines[n].reload()
        
        self.re = None
        self.clear_textview()
    
    # key_press textview (for update status when press Ctrl + Enter)
    def on_textview1_key_press_event(self, textview, event):
        # Enter == 65293
        if event.keyval == 65293 and event.state & gtk.gdk.CONTROL_MASK:
            txt = self.get_textview()
            
            # if update button enabled (== len(text) <= 140
            if self.btnupdate.get_sensitive():
                self.twitter.status_update(txt, self.re, self.msgfooter)
                self.re = None
                self.clear_textview()
            
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

    # Tab right clicked
    def on_notebook_tabbar_button_press(self, widget, event):
        if event.button == 3:
            self.builder.get_object("menu_timeline").popup(None, None, None, event.button, event.time)
    
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
        tl = self.timelines[page_num]
        self.builder.get_object("menuitem_tweet").set_sensitive(False)
        menu_timeline = self.builder.get_object("menuitem_timeline")
        menu_timeline.set_sensitive(False)
        
        if tl != None:
            self._toggle_change_flg = True
            method = tl.timeline.api_method.func_name
            default = self.get_default_interval(method)
            
            if default == -1: default = None
            
            menu_default = self.builder.get_object("menuitem_time_default")
            menu_default.get_child().set_text("Default (%s)" % default)
            
            interval = tl.timeline.interval
            
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
            menu_timeline.set_sensitive(True)
    
    ########################################
    # Tweet menu event
    
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
                          "user_timeline", user = status.user.id)
    
    # Status detail
    def on_menuitem_detail_activate(self, menuitem):
        status = self.get_selected_status()
        detail = StatusDetail(status, self.twitter, self.icons)
        self.new_tab(detail, "S: %d" % status.id)
    
    # favorite
    def on_menuitem_fav_activate(self, menuitem):
        status = self.get_selected_status()
        self.twitter.api.favorite_create(status.id)
    
    # Destroy status
    def on_menuitem_destroy_activate(self, menuitem):
        status = self.get_selected_status()
        self.twitter.api.status_destroy(status.id)
    
    ########################################
    # Timeline menu Event
    
    def change_interval(self, interval):
        tl = self.timelines[self.get_current_tab()].timeline
        
        if interval == 0:
            method = tl.api_method.func_name
            interval = self.get_default_interval(method)
        
        if not self._toggle_change_flg:
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
        
        # footer
        self.builder.get_object("entry_footer").set_text(self.msgfooter)

        # OAuth information
        self.builder.get_object("entry_myname").set_text(self.twitter.myname)
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
                t.set_color(self.status_color)
        
        conf = (("DEFAULT", "interval", self.interval),
                ("DEFAULT", "counts", self.scounts),
                ("DEFAULT", "iconmode", self.iconmode),
                ("DEFAULT", "color", self.status_color),
                (self.twitter.myname, "footer", self.msgfooter))
        save_configs(conf)
        
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
