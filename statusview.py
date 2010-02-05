#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango

class statusview:
    def __init__(self):
        self.scrwin = gtk.ScrolledWindow()
        
        # Liststore column setting
        self.store = gtk.ListStore(
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
                              self.treeview_width_changed)
        
        # Setting TreeView Column
        crtxt_name = gtk.CellRendererText()
        crtxt_text = gtk.CellRendererText()
        crtxt_text.set_property("wrap-mode", pango.WRAP_WORD)
        tcol = list()
        tcol.append(
            gtk.TreeViewColumn("Name", crtxt_name, text = 0))
        tcol.append(
            gtk.TreeViewColumn("Text", crtxt_text, text = 1))
        
        # Add Column
        for i in tcol:
            self.treeview.append_column(i)
        
        # Auto scroll to top setup
        vadj = self.scrwin.get_vadjustment()
        vadj.connect("changed", self.vadj_changed)
        self.vadj_upper = vadj.upper
    
    def add(self, notebook, name = None):
        label = gtk.Label(name)
        notebook.append_page(self.scrwin, label)
    
    def vadj_changed(self, adj):
        # Scroll to top if upper(list length) changed
        if self.vadj_upper < adj.upper:
            self.vadj_upper = adj.upper
            adj.set_value(0)

    def treeview_width_changed(self, treeview, allocate):
        # Get Treeview Width
        width = treeview.get_allocation().width

        columns = treeview.get_columns()

        # Get "Name" width
        width2 = columns[0].get_property("width")

        # Set "Text" width
        cellr = columns[1].get_cell_renderers()
        cellr[0].set_property("wrap-width", width - width2)
