#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango

import re
import twittertools

import time
import webbrowser

class timeline:
    def __init__(self, api, icons, iconmode = True):
        self.twitter = api
        self.icons = icons
        
        # Base scrolledwindow
        self.scrwin = gtk.ScrolledWindow()
        
        # Liststore column setting
        self.store = gtk.ListStore(
            gtk.gdk.Pixbuf, str,
            gobject.TYPE_INT64, gobject.TYPE_INT64, str)
        self.store.set_sort_column_id(2, gtk.SORT_DESCENDING)
        self.treeview = gtk.TreeView(self.store)
        
        # Add treeview to scrolledwindow
        self.scrwin.add(self.treeview)
        self.scrwin.set_shadow_type(gtk.SHADOW_IN)
        # Scrollbar policy
        self.scrwin.set_policy(
            gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        
        self.treeview.set_headers_visible(False)
        self.treeview.set_rules_hint(True)
        self.treeview.connect("size-allocate",
                              self.on_treeview_width_changed)
        self.treeview.connect("cursor-changed",
                              self.on_treeview_cursor_changed)
        
        # Setting TreeView Column
        crpix = gtk.CellRendererPixbuf()
        crtxt = gtk.CellRendererText()
        crtxt.set_property("wrap-mode", pango.WRAP_WORD)
        
        tcol = list()
        tcol.append(
            gtk.TreeViewColumn("Icon", crpix, pixbuf = 0))
        # visible is False if no-icon
        tcol[-1].set_visible(iconmode)
        tcol.append(
            gtk.TreeViewColumn("Status", crtxt, markup = 1))
        
        # Add Column
        for i in tcol:
            i.add_attribute(
                i.get_cell_renderers()[0], "cell-background", 4)
            self.treeview.append_column(i)
        
        # Auto scroll to top setup
        vadj = self.scrwin.get_vadjustment()
        self.vadj_upper = vadj.upper
        self.vadj_lock = False
        vadj.connect("changed", self.on_vadjustment_changed)
        
        # Tools setup
        self.twtools = twittertools.TwitterTools()
        self.noent_amp = re.compile("&(?![A-Za-z]+;)")
    
    # Start Sync Timeline (new twitter timeline thread create)
    def init_timeline(self, method, time, args, kwargs):
        self.timeline = self.twitter.create_timeline(
            method, time, args, kwargs)
        
        # Set Event Hander (exec in every get timeline
        self.timeline.reloadEventHandler = self.prepend_new_statuses    
        # Add timeline to IconStore
        self.icons.add_store(self.store, 3)
    
    def start_timeline(self):
        # Start Timeline sync thread
        self.timeline.start()
    
    # Add Notebook
    def add_notebook(self, notebook, name = None):
        label = gtk.Label(name)
        notebook.append_page(self.scrwin, label)
        notebook.show_all()
    
    # Reload Timeline
    def reload(self):
        if not self.timeline.lock.isSet():
            # lock flag set (unlock)
            self.timeline.lock.set()
    
    # Add popup menu
    def add_popup(self, menu):
        self.pmenu = menu
        self.treeview.connect("button-press-event",
                              self.on_treeview_button_press)
    
    # Get timeline ids
    def get_timeline_ids(self):
        return self.timeline.timeline
    
    # Get selected status
    def get_selected_status(self):
        path, column = self.treeview.get_cursor()
        if path == None:
            return None
        else:
            return self.get_status(path)
    
    # Get status from treeview path
    def get_status(self, path):
        id = self.store[path][2]
        return self.twitter.statuses[id]

    # get status from mouse point
    def get_status_from_point(self, x, y):
        path = self.treeview.get_path_at_pos(x, y)
        it = self.store.get_iter(path[0])
        sid = self.store.get_value(it, 2)
        return self.twitter.statuses[sid]
    
    # Color status
    def color_status(self, status = None):
        myname = self.twitter.myname
        myid = self.twitter.me.id if self.twitter.me != None else -1
        
        # if not set target status
        if status == None:
            status = self.get_selected_status()
        
        i = self.store.get_iter_first()
        while i:
            bg = None   
            
            id = self.store.get_value(i, 2)
            s = self.twitter.statuses[id]
            u = s.user
            
            if u.id == myid:
                # My status (Blue)
                bg = "#CCCCFF"
            elif s.in_reply_to_user_id == myid or \
                    s.text.find("@%s" % myname) != -1:
                # Reply to me (Red)
                bg = "#FFCCCC"
            
            if status:
                if s.id == status.in_reply_to_status_id:
                    # Reply to (Orange)
                    bg = "#FFCC99"
                elif u.id == status.in_reply_to_user_id:
                    # Reply to other (Yellow)
                    bg = "#FFFFCC"
                elif u.id == status.user.id:
                    # Selected user (Green)
                    bg = "#CCFFCC"
            
            self.store.set_value(i, 4, bg)
            i = self.store.iter_next(i)
    
    # Prepend new statuses
    def prepend_new_statuses(self, new_ids):
        # Auto scroll lock if adjustment changed manually
        vadj = self.scrwin.get_vadjustment()
        self.vadj_lock = True if vadj.value != 0.0 else False
        
        gtk.gdk.threads_enter()
        # Insert New Status
        for i in new_ids:
            self.add_status(i)
        gtk.gdk.threads_leave()
        
        self.color_status()
    
    def add_status(self, i):
        status = self.twitter.statuses[i]
        background = None
        
        # colord url
        text = self.twtools.get_colored_url(status.text)
        # replace no entity & -> &amp;
        text = self._replace_amp(text)
        
        if status.user.id in self.twitter.followers:
            # Bold screen_name if follwer
            tmpl = "<b>%s</b>\n%s"
        else:
            # or gray
            tmpl = "<span foreground='#666666'><b>%s</b></span>\n%s"
        
        # Bold screen_name
        message = tmpl % (
            status.user.screen_name, text)
        
        # New Status Prepend to Liststore (Add row)
        self.store.prepend(
            (self.icons.get(status.user),
             message,
             long(status.id), long(status.user.id),
             background))
        
        self.on_status_added(i)
    
    # Replace & -> &amp;
    def _replace_amp(self, string):
        amp = string.find('&')
        if amp == -1: return string
        
        entity_match = self.noent_amp.finditer(string)
        
        for i, e in enumerate(entity_match):
            string = "%s&amp;%s" % (
                string[:e.start() + (4 * i)],
                string[e.start() + (4 * i) + 1:])
        
        return string

    # dummy events and methods
    def on_status_added(self, *args, **kwargs): pass
    def on_status_selection_changed(self, *args, **kwargs): pass
    def new_timeline(self, *args, **kwargs): pass
    
    
    ########################################
    # Gtk Signal Events
    
    # Treeview width changed Event (text-wrap-width change)
    def on_treeview_width_changed(self, treeview, allocate):
        # Get Treeview Width
        width = treeview.get_allocation().width
        # Get Treeview Columns
        columns = treeview.get_columns()
        
        # Get !("Status") width
        width2 = 0
        for i in columns[:1]:
            width2 += i.get_property("width")
        
        # Set "Status" width
        cellr = columns[1].get_cell_renderers()
        cellr[0].set_property("wrap-width", width - width2 - 10)
        
        # Reset all data to change row height
        i = self.store.get_iter_first()
        while i:
            # Maybe no affects performance
            # if treeview.allocation.width != width:
            #     break
            txt = self.store.get_value(i, 1)
            self.store.set_value(i, 1, txt)
            i = self.store.iter_next(i)
        
        vadj = self.scrwin.get_vadjustment()
        self.vadj_upper = vadj.upper
    
    # Scroll to top if upper(list length) changed Event
    def on_vadjustment_changed(self, adj):
        if not self.vadj_lock and self.vadj_upper < adj.upper:
            if len(self.store):
                self.treeview.scroll_to_cell((0,))
            self.vadj_upper = adj.upper
    
    # Menu popup
    def on_treeview_button_press(self, widget, event):
        if event.button == 3:
            # Get status
            status = self.get_status_from_point(
                int(event.x), int(event.y))
            # Get Urls
            urls = self.twtools.get_urls(status.text)
            # Get mentioned users
            users = self.twtools.get_users(status.text)
            
            # URL Menu
            m = gtk.Menu()
            if urls:
                # if exist url in text, add menu
                for i in urls:
                    label = "%s..." % i[:47] if len(i) > 50 else i
                    
                    # Menuitem create
                    item = gtk.ImageMenuItem(label)
                    item.set_image(gtk.image_new_from_stock("gtk-new", gtk.ICON_SIZE_MENU))
                    # Connect click event (open browser)
                    item.connect("activate",
                                 self.on_menuitem_url_clicked, i)
                    # append to menu
                    m.append(item)
            else:
                # not, show None
                item = gtk.MenuItem("None")
                item.set_sensitive(False)
                m.append(item)            
            # urls submenu append
            self.pmenu.get_children()[-1].set_submenu(m)
            
            # Mentioned User Menu
            mm = gtk.Menu()
            if users:
                for i in users:
                    # Menuitem create
                    item = gtk.ImageMenuItem("@%s" % i.replace("_", "__"))
                    item.set_image(gtk.image_new_from_stock("gtk-add", gtk.ICON_SIZE_MENU))
                    # Connect click event (add tab)
                    item.connect("activate",
                                 self.on_menuitem_user_clicked, i)
                    # append to menu
                    mm.append(item)
            else:
                # not, show None
                item = gtk.MenuItem("None")
                item.set_sensitive(False)
                mm.append(item)
            self.pmenu.get_children()[-2].set_submenu(mm)
            
            # Show popup menu
            m.show_all()
            mm.show_all()
            self.pmenu.popup(None, None, None, event.button, event.time)
    
    # Open Web browser if url menuitem clicked
    def on_menuitem_url_clicked(self, menuitem, url):
        webbrowser.open_new_tab(url)

    # Add user timeline tab if mentioned user menu clicked
    def on_menuitem_user_clicked(self, menuitem, sname):
        user = self.twitter.get_user_from_screen_name(sname)
        if user != None:
            self.new_timeline("@%s" % sname, "user_timeline", -1,
                              user = user.id)
        else:
            # force specify screen_name if not found
            self.new_timeline("@%s" % sname, "user_timeline", -1,
                              user = sname, sn = True)
        return True
    
    # Status Clicked
    def on_treeview_cursor_changed(self, treeview):
        status = self.get_selected_status()
        self.color_status(status)
        self.on_status_selection_changed(status)
