#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk

import threading
import urllib2

class IconStore:
    def __init__(self):
        self.data = dict()
        self.stores = list()
    
    def get(self, user):
        if user.id in self.data:
            # if exist in cache
            return self.data[user.id]
        else:
            # or get new icon
            return self.new(user)
    
    def new(self, user):
        # New Icon thread start
        newico = NewIcon(user, self.stores, self.data)
        newico.start()
        
        self.data[user.id] = None
        
        # Return None
        #return gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, 48, 48)
        return None
    
    def add_store(self, store):
        self.stores.append(store)

class NewIcon(threading.Thread):
    def __init__(self, user, stores, icons):
        threading.Thread.__init__(self)
        self.user = user
        self.stores = stores
        self.icons = icons
        
    def run(self):
        # Icon Data Get
        ico = urllib2.urlopen(self.user.profile_image_url).read()
        
        # Load Pixbuf Loader and Create Pixbuf
        icoldr = gtk.gdk.PixbufLoader()
        icoldr.write(ico)
        icopix = icoldr.get_pixbuf()
        icoldr.close()
        
        # Resize
        if icopix != None and icopix.get_property("width") > 48:
            icopix = icopix.scale_simple(48, 48, gtk.gdk.INTERP_BILINEAR)
        
        # Add iconstore
        self.icons[self.user.id] = icopix
        
        # Icon Refresh
        gtk.gdk.threads_enter()
        for store in self.stores:
            for i, j in enumerate(iter(store)):
                if j[1] == self.user.screen_name:
                    store[(i,)] = (icopix, j[1], j[2])
        gtk.gdk.threads_leave()
