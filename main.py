#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk

from objects import GtkObjects
from twitterapi import twitterapi

# Main Class
class Main:
    # Constractor
    def __init__(self, glade):
        # GtkBuilder instance
        builder = gtk.Builder()
        # Glade file input
        builder.add_from_file(glade)
        # Connect signals
        builder.connect_signals(self)
        
        # GtkObjects instance
        # usage: self.obj.`objectname`
        # ex) self.obj.button1
        self.obj = GtkObjects(builder.get_objects())

        # Setting TreeView Column
        cr_txt = gtk.CellRendererText()
        tcol = list()
        tcol.append(
            gtk.TreeViewColumn("Name", cr_txt, text = 0))
        tcol.append(
            gtk.TreeViewColumn("Text", cr_txt, text = 1))

        # Add Column
        for i in tcol:
            self.obj.treeview1.append_column(i)
    
    def main(self, keys):
        # Twitter class instance
        self.twitter = twitterapi(keys)
        # Set Event Hander (exec in every get home_timeline
        self.twitter.EventHandler = self.refresh
        
        self.obj.window1.show_all()
        
        # Gtk Multithread Setup
        gtk.gdk.threads_init()
        gtk.gdk.threads_enter()
        # Twitter class thread start
        self.twitter.start()
        # Start gtk main loop        
        gtk.main()
        gtk.gdk.threads_leave()
    
    # Refresh TreeView
    def refresh(self, *args):
        gtk.gdk.threads_enter()
        
        # Insert New Status
        for i in self.twitter.home:
            self.obj.liststore1.insert(
                0, (i.user.screen_name, i.text))
        
        self.obj.treeview1.show_all()
        self.obj.scrolledwindow1.show_all()
        self.obj.window1.show_all()
 
        gtk.gdk.flush()
        gtk.gdk.threads_leave()
        
        gtk.gdk.threads_enter()
        
        # Scroll to top
        vadj = self.obj.scrolledwindow1.get_vadjustment()
        vadj.set_value(0)
        self.obj.scrolledwindow1.set_vadjustment(vadj)

        gtk.gdk.threads_leave()
    
    # Window close event
    def close(self, widget):
        gtk.main_quit()
