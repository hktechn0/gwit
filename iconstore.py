#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk

import urllib2

class IconStore:
    def __init__(self):
        self.data = dict()
    
    def get(self, user):
        if user.id in self.data:
            # if exist in cache
            return self.data[user.id]
        else:
            # or get new icon
            return self.new(user)
    
    def new(self, user):
        # Icon Data Get
        ico = urllib2.urlopen(user.profile_image_url).read()

        # Load Pixbuf Loader and Create Pixbuf
        icoldr = gtk.gdk.PixbufLoader()
        icoldr.write(ico)
        icopix = icoldr.get_pixbuf()
        icoldr.close()
        
        # Resize
        if icopix != None and icopix.get_property("width") > 48:
            icopix = icopix.scale_simple(48, 48, gtk.gdk.INTERP_BILINEAR)

        # Cache usericon pixbuf
        self.data[user.id] = icopix
        
        return icopix
