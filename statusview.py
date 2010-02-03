#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk

class statusview:
    def __init__(self):
        self.scrwin = gtk.ScrolledWindow()
        self.treeview = gtk.TreeView()

        self.scrwin.add(self.treeview)
        self.scrwin.set_shadow_type(gtk.SHADOW_IN)
        self.scrwin.set_policy(
            gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        
        self.treeview.set_headers_visible(False)
        self.treeview.set_rules_hint(True)
        
        # Setting TreeView Column
        cr_txt = gtk.CellRendererText()
        tcol = list()
        tcol.append(
            gtk.TreeViewColumn("Name", cr_txt, text = 0))
        tcol.append(
            gtk.TreeViewColumn("Text", cr_txt, text = 1))
        
        # Add Column
        for i in tcol:
            self.treeview.append_column(i)
        
        # Auto scroll to top setup
        vadj = self.scrwin.get_vadjustment()
        vadj.connect("changed", self.vadj_changed)
        self.vadj_upper = vadj.get_upper()
    
    def add(self, notebook, name = None):
        label = gtk.Label(name)
        notebook.append_page(self.scrwin, label)
    
    def vadj_changed(self, adj):
        # Scroll to top if upper(list length) changed
        if self.vadj_upper < adj.get_upper():
            self.vadj_upper = adj.get_upper()
            adj.set_value(0)
