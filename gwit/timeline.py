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
import threading
import webbrowser

class timeline:
    color = (None, None, None, None, None)
    
    def __init__(self, api, icons, iconmode):
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
        self.scrwin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        
        self.treeview.set_headers_visible(False)
        self.treeview.set_rules_hint(True)
        self.treeview.connect("size-allocate", self.on_treeview_width_changed)
        self.treeview.connect("cursor-changed", self.on_treeview_cursor_changed)
        self.treeview.connect("row_activated", self.on_treeview_row_activated)
        
        # Setup icon column (visible is False if no-icon)
        cell_p = gtk.CellRendererPixbuf()
        col_icon = gtk.TreeViewColumn("Icon", cell_p, pixbuf = 0)
        col_icon.set_visible(iconmode)
        
        # Setup status column
        cell_t = gtk.CellRendererText()
        cell_t.set_property("wrap-mode", pango.WRAP_WORD)
        col_status = gtk.TreeViewColumn("Status", cell_t, markup = 1)
        
        col_icon.add_attribute(cell_p, "cell-background", 4)
        col_status.add_attribute(cell_t, "cell-background", 4)
        self.treeview.append_column(col_icon)
        self.treeview.append_column(col_status)
        
        # Auto scroll to top setup
        vadj = self.scrwin.get_vadjustment()
        self.vadj_upper = vadj.upper
        self.vadj_lock = False
        vadj.connect("changed", self.on_vadjustment_changed)
        
        # Tools setup
        self.twtools = twittertools.TwitterTools()
        self.noent_amp = re.compile("&(?![A-Za-z]+;)")
    
    # Start Sync Timeline (new twitter timeline thread create)
    def init_timeline(self, method, interval, counts, args, kwargs):
        self.timeline = self.twitter.create_timeline(method, interval, counts, args, kwargs)
        
        # Set Event Hander (exec in every get timeline
        self.timeline.reloadEventHandler = self.prepend_new_statuses    
        # Add timeline to IconStore
        self.icons.add_store(self.store, 3)
    
    def start_timeline(self):
        # Start Timeline sync thread
        self.timeline.start()
    
    # Reload Timeline
    def reload(self):
        if not self.timeline.lock.isSet():
            # lock flag set (unlock)
            self.timeline.lock.set()
    
    # Add popup menu
    def add_popup(self, menu):
        self.pmenu = menu
        self.treeview.connect("button-press-event", self.on_treeview_button_press)
    
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
        i = self.store[path][2]
        return self.twitter.statuses[i]
    
    # get status from mouse point
    def get_status_from_point(self, x, y):
        path = self.treeview.get_path_at_pos(x, y)
        it = self.store.get_iter(path[0])
        sid = self.store.get_value(it, 2)
        return self.twitter.statuses[sid]
    
    # Tweet menu setup
    def menu_setup(self, status):
        # Get Urls
        urls = self.twtools.get_urls(status.text if "retweeted_status" not in status.keys()
                                     else status.retweeted_status.text)
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
                item.connect("activate", self.on_menuitem_url_clicked, i)
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
                item.connect("activate", self.on_menuitem_user_clicked, i)
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

    def set_color(self, colortuple):
        self.color = tuple(colortuple)
    
    def destroy(self):
        self.timeline.destroy()
        self.icons.remove_store(self.store)
        self.scrwin.destroy()
        self.treeview.destroy()
    
    ########################################
    # Execute in Background Thread Methods

    # Prepend new statuses
    def prepend_new_statuses(self, new_ids):
        # Auto scroll lock if adjustment changed manually
        vadj = self.scrwin.get_vadjustment()
        self.vadj_lock = True if vadj.value != 0.0 else False
        
        # pack New Status
        statuses = [self.status_pack(i) for i in new_ids]
        
        # New Status Prepend to Liststore (Add row)
        gtk.gdk.threads_enter()
        for i in statuses:
            self.store.prepend(i)
        gtk.gdk.threads_leave()
        
        self.color_status()
    
    def status_pack(self, i):
        status = self.twitter.statuses[i]
        background = None
        
        name = status.user.screen_name
        
        if status.retweeted_status != None:
            rtstatus = status
            status = status.retweeted_status
            name = "%s <span foreground='#333333'><small>- Retweeted by %s</small></span>" % (
                status.user.screen_name, rtstatus.user.screen_name)
        
        # colord url
        text = self.twtools.get_colored_url(status.text)
        # replace no entity & -> &amp;
        text = self._replace_amp(text)
        
        if status.user.id in self.twitter.followers:
            # Bold screen_name if follower
            tmpl = "<b>%s</b>\n%s"
        else:
            # or gray
            tmpl = "<span foreground='#666666'><b>%s</b></span>\n%s"
        
        # Bold screen_name
        message = tmpl % (name, text)
        
        self.on_status_added(i)
        
        return (self.icons.get(status.user),
                message,
                long(i), long(status.user.id),
                background)
    
    # Color status
    def color_status(self, status = None):
        t = threading.Thread(target=self.color_status_in_thread, args=(status,))
        t.setName("color_status")
        t.start()
    
    def color_status_in_thread(self, status = None):
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
                bg = self.color[0]
            elif s.in_reply_to_user_id == myid or \
                    s.text.find("@%s" % myname) != -1:
                # Reply to me (Red)
                bg = self.color[1]
            
            if status:
                if s.id == status.in_reply_to_status_id:
                    # Reply to (Orange)
                    bg = self.color[2]
                elif u.id == status.in_reply_to_user_id:
                    # Reply to other (Yellow)
                    bg = self.color[3]
                elif u.id == status.user.id:
                    # Selected user (Green)
                    bg = self.color[4]
            
            gtk.gdk.threads_enter()
            self.store.set_value(i, 4, bg)
            gtk.gdk.threads_leave()
            
            i = self.store.iter_next(i)
    
    # dummy events and methods
    def on_status_added(self, *args, **kwargs): pass
    def on_status_selection_changed(self, *args, **kwargs): pass
    def on_status_activated(self, *args, **kwargs): pass
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
        
        def refresh_text():
            # Reset all data to change row height
            i = self.store.get_iter_first()
            while i:
                # Maybe no affects performance
                # if treeview.allocation.width != width:
                #     break
                txt = self.store.get_value(i, 1)
                
                gtk.gdk.threads_enter()
                self.store.set_value(i, 1, txt)
                gtk.gdk.threads_leave()
                
                i = self.store.iter_next(i)
        
            vadj = self.scrwin.get_vadjustment()
            self.vadj_upper = vadj.upper
        
        t = threading.Thread(target=refresh_text)
        t.setName("refresh_text")
        t.start()
    
    # Scroll to top if upper(list length) changed Event
    def on_vadjustment_changed(self, adj):
        if not self.vadj_lock and self.vadj_upper < adj.upper:
            if len(self.store):
                self.treeview.scroll_to_cell((0,))
            self.vadj_upper = adj.upper
    
    # Status Clicked
    def on_treeview_cursor_changed(self, treeview):
        status = self.get_selected_status()
        self.color_status(status)
        self.menu_setup(status)
        self.on_status_selection_changed(status)

    # Status double clicked
    def on_treeview_row_activated(self, treeview, path, view_column):
        status = self.get_status(path)
        self.on_status_activated(status)
    
    # Menu popup
    def on_treeview_button_press(self, widget, event):
        if event.button == 3:
            self.pmenu.popup(None, None, None, event.button, event.time)
    
    
    ########################################
    # Tweet menu event
    
    # Open Web browser if url menuitem clicked
    def on_menuitem_url_clicked(self, menuitem, url):
        webbrowser.open_new_tab(url)
    
    # Add user timeline tab if mentioned user menu clicked
    def on_menuitem_user_clicked(self, menuitem, sname):
        user = self.twitter.get_user_from_screen_name(sname)
        if user != None:
            self.new_timeline("@%s" % sname, "user_timeline", user = user.id)
        else:
            # force specify screen_name if not found
            self.new_timeline("@%s" % sname, "user_timeline", user = sname, sn = True)
        
        return True
