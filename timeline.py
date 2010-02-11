#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango

class timeline:
    def __init__(self, api, icons):
        self.api = api
        self.icons = icons
        
        # Base scrolledwindow
        self.scrwin = gtk.ScrolledWindow()
        
        # Liststore column setting
        self.store = gtk.ListStore(
            gtk.gdk.Pixbuf,
            gobject.TYPE_STRING, gobject.TYPE_STRING)
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
        crpix_icon = gtk.CellRendererPixbuf()
        crtxt_name = gtk.CellRendererText()
        crtxt_text = gtk.CellRendererText()
        crtxt_text.set_property("wrap-mode", pango.WRAP_WORD)
        
        tcol = list()
        tcol.append(
            gtk.TreeViewColumn("Icon", crpix_icon, pixbuf = 0))
        tcol.append(
            gtk.TreeViewColumn("Name", crtxt_name, text = 1))
        tcol.append(
            gtk.TreeViewColumn("Text", crtxt_text, text = 2))
        
        # Add Column
        for i in tcol:
            self.treeview.append_column(i)
        
        # Add ListStore to IconStore
        self.icons.add_store(self.store)
        
        # Auto scroll to top setup
        vadj = self.scrwin.get_vadjustment()
        self.vadj_upper = vadj.upper
        self.vadj_lock = False
        vadj.connect("changed", self._vadj_changed)
    
    # Start Sync Timeline (new twitter timeline thread create)
    def start_sync(self, method, time):
        self.timeline = self.api.create_timeline(method, time)
        # Set Event Hander (exec in every get timeline
        self.timeline.reloadEventHandler = self._prepend_new_statuses
        self.timeline.start()
    
    # Add Notebook
    def add_notebook(self, notebook, name = None):
        label = gtk.Label(name)
        notebook.append_page(self.scrwin, label)
        gtk.gdk.threads_enter()
        notebook.show_all()
        gtk.gdk.threads_leave()
    
    
    ########################################
    # Gtk Signal Events
    
    # Treeview width changed Event (text-wrap-width change)
    def _treeview_width_changed(self, treeview, allocate):
        # Get Treeview Width
        width = treeview.get_allocation().width
        # Get Treeview Columns
        columns = treeview.get_columns()
        
        # Get !("Text") width
        width2 = 0
        for i in columns[:2]:
            width2 += i.get_property("width")
        
        # Set "Text" width
        cellr = columns[2].get_cell_renderers()
        cellr[0].set_property("wrap-width", width - width2 - 10)
        
        # Reset all data to change row height
        i = self.store.get_iter_first()
        while i:
            # Maybe no affects performance
            # if treeview.allocation.width != width:
            #     break
            txt = self.store.get_value(i, 2)
            self.store.set_value(i, 2, txt)
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
            # New Status Prepend to Liststore (Add row)
            gtk.gdk.threads_enter()
            self.store.prepend(
                (self.icons.get(i.user),
                 i.user.screen_name, i.text))
            gtk.gdk.threads_leave()
        
        #print self.timeline.timeline[-1].id
