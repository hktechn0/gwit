#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango

import re
import urlregex

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
            gtk.gdk.Pixbuf, str, long, long, str, object)
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
        vadj.connect("changed", self._vadj_changed)

        # Regex setup
        self.urlre = urlregex.urlregex()
        self.noent_amp = re.compile("&(?![A-Za-z]+;)")
    
    # Start Sync Timeline (new twitter timeline thread create)
    def start_sync(self, method, time, args, kwargs):
        self.timeline = self.twitter.create_timeline(
            method, time, args, kwargs)

        # Set Event Hander (exec in every get timeline
        self.timeline.reloadEventHandler = self._prepend_new_statuses
        self.timeline.start()
        
        # Add timeline to IconStore
        self.icons.add_store(self.store)
    
    # Add Notebook
    def add_notebook(self, notebook, name = None):
        label = gtk.Label(name)
        notebook.append_page(self.scrwin, label)
        notebook.show_all()
    
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
        path = self.treeview.get_cursor()[0]
        return self.get_status(path)
    
    # Get status from treeview path
    def get_status(self, path):
        id = self.store[path][2]
        return self.twitter.statuses[id]

    # Reload Timeline
    def reload(self):
        if not self.timeline.lock.isSet():
            # lock flag set (unlock)
            self.timeline.lock.set()
    
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
    
    # Color status
    def color_status(self, status = None):
        me = self.twitter.users[self.twitter.myid]
        
        i = self.store.get_iter_first()
        while i:
            bg = None            
            
            id = self.store.get_value(i, 2)
            s = self.twitter.statuses[id]
            u = s.user
            
            if u.id == me.id:
                # My status (Blue)
                bg = "#CCCCFF"
            elif status and s.id == status.in_reply_to_status_id:
                # Reply to (Orange)
                bg = "#FFCC99"
            elif s.in_reply_to_user_id == me.id or \
                    s.text.find("@%s" % me.screen_name) != -1:
                # Reply to me (Red)
                bg = "#FFCCCC"
            elif status:
                if u.id == status.in_reply_to_user_id:
                    # Reply to other (Yellow)
                    bg = "#FFFFCC"
                elif u.id == status.user.id:
                    # Selected user (Green)
                    bg = "#CCFFCC"
            
            self.store.set_value(i, 4, bg)
            i = self.store.iter_next(i)
    
    
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
    def _vadj_changed(self, adj):
        if not self.vadj_lock and self.vadj_upper < adj.upper:
            if len(self.store):
                self.treeview.scroll_to_cell((0,))
            self.vadj_upper = adj.upper
    
    # Prepend new statuses
    def _prepend_new_statuses(self, new_ids):
        # Auto scroll lock if adjustment changed manually
        vadj = self.scrwin.get_vadjustment()
        self.vadj_lock = True if vadj.value != 0.0 else False
        
        myname = self.twitter.users[self.twitter.myid].screen_name
        
        # Insert New Status
        for i in new_ids:
            status = self.twitter.statuses[i]
            
            # colord url
            text, urls = self.urlre.get_colored(status.text)
            # replace no entity & -> &amp;
            text = self._replace_amp(text)
            
            # Bold screen_name
            text = "<b>%s</b>\n%s" % (
                status.user.screen_name, text)
            
            # New Status Prepend to Liststore (Add row)
            gtk.gdk.threads_enter()
            self.store.prepend(
                (self.icons.get(status.user),
                 text,
                 long(status.id), long(status.user.id),
                 None, # background
                 urls))
            gtk.gdk.threads_leave()
        
        self.color_status()
    
    # Menu popup
    def on_treeview_button_press(self, widget, event):
        if event.button == 3:
            # get path from point
            path = self.treeview.get_path_at_pos(int(event.x), int(event.y))
            
            # Get Urls
            it = self.store.get_iter(path[0])
            urls = self.store.get_value(it, 5)
            
            m = gtk.Menu()
            
            if urls:
                # if exist url in text, add menu
                for i in urls:
                    label = "%s..." % i[:47] if len(i) > 50 else i
                    
                    # Menuitem create
                    item = gtk.MenuItem(label)
                    # Connect click event (open browser)
                    item.connect("activate",
                                 self._menuitem_url_clicked, i)
                    # append to menu
                    m.append(item)
            else:
                # not, show None
                item = gtk.MenuItem("None")
                item.set_sensitive(False)
                m.append(item)
            
            # urls submenu append
            self.pmenu.get_children()[-1].set_submenu(m)
            
            # Show popup menu
            m.show_all()
            self.pmenu.popup(None, None, None, event.button, event.time)
    
    # Open Web browser if url menuitem clicked
    def _menuitem_url_clicked(self, menuitem, url):
        webbrowser.open_new_tab(url)

    # Status Clicked
    def on_treeview_cursor_changed(self, treeview):
        status = self.get_selected_status()
        self.color_status(status)
