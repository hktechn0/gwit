#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango

import re
import urlregex

import webbrowser

class timeline:
    def __init__(self, api, icons, iconmode = True):
        self.api = api
        self.icons = icons
        
        # Base scrolledwindow
        self.scrwin = gtk.ScrolledWindow()
        
        # Liststore column setting
        self.store = gtk.ListStore(
            gtk.gdk.Pixbuf, str,
            object, object, object, object,
            str, object)
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
                              self._treeview_width_changed)
        
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
                i.get_cell_renderers()[0], "cell-background", 6)
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
        self.timeline = self.api.create_timeline(
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
        self.treeview.connect(
            "button-press-event",
            self.on_treeview_button_press)

    # Get timeline list
    def get_timeline(self):
        return self.timeline.timeline
    
    # Get selected status
    def get_selected_status(self):
        return self.timeline.timeline[
            -1 - self.treeview.get_cursor()[0][0]]

    # Get status from treeview path
    def get_status(self, path):
        return self.timeline.timeline[-1 - path[0]]
    
    # Replace & -> &amp;
    def _replace_amp(self, string):
        amp = string.find('&')
        if amp == -1:
            return string
        
        entity_match = self.noent_amp.finditer(string)
        
        for i, e in enumerate(entity_match):
            string = "%s&amp;%s" % (
                string[:e.start() + (4 * i)],
                string[e.start() + (4 * i) + 1:])
        
        return string
    
    ########################################
    # Gtk Signal Events
    
    # Treeview width changed Event (text-wrap-width change)
    def _treeview_width_changed(self, treeview, allocate):
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
        if not self.vadj_lock and \
                self.vadj_upper < adj.upper:
            if len(self.store):
                self.treeview.scroll_to_cell((0,))
            self.vadj_upper = adj.upper
    
    # Prepend new statuses
    def _prepend_new_statuses(self, new_timeline):
        # Auto scroll lock if adjustment changed manually
        vadj = self.scrwin.get_vadjustment()
        self.vadj_lock = True if vadj.value != 0.0 else False
        
        # Insert New Status
        for i in new_timeline:
            # colord url
            text, urls = self.urlre.get_colored(i.text)
            # replace no entity & -> &amp;
            text = self._replace_amp(text)
            
            # Bold screen_name
            text = "<b>%s</b>\n%s" % (
                i.user.screen_name, text)
            
            # If my status, change background color
            if i.user.id == self.api.api.user.id:
                background = "#CCFFCC"
            elif i.in_reply_to_user_id == self.api.api.user.id or \
                    i.text.find(self.api.api.user.screen_name) != -1:
                background = "#FFCCCC"
            else:
                background = None
            
            # New Status Prepend to Liststore (Add row)
            gtk.gdk.threads_enter()
            self.store.prepend(
                (self.icons.get(i.user),
                 text,
                 i.id,
                 i.user.id,
                 i.in_reply_to_status_id,
                 i.in_reply_to_user_id,
                 background,
                 urls))
            gtk.gdk.threads_leave()
    
    # Menu popup
    def on_treeview_button_press(self, widget, event):
        if event.button == 3:
            # Get Urls
            it = self.store.get_iter(self.treeview.get_cursor()[0])
            urls = self.store.get_value(it, 7)
            
            m = gtk.Menu()
            
            if urls:
                # if exist url in text, add menu
                for i in urls:
                    if len(i) > 50:
                        label = "%s..." % i[:47]
                    else:
                        label = i
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
