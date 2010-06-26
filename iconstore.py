#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk

import threading
import urllib2
import cStringIO

class IconStore:
    def __init__(self, iconmode = True):
        self.iconmode = iconmode
        self.data = dict()
        self.stores = list()
        self.semaphore = threading.BoundedSemaphore(5)
    
    def get(self, user):
        if user.id in self.data:
            # if exist in cache
            return self.data[user.id]
        else:
            # or get new icon
            return self.new(user)
    
    def new(self, user):
        # New Icon thread start
        newico = NewIcon(user, self.stores, self.data, self.semaphore)
        if self.iconmode:
            # start thread for wget icon if iconmode is True
            newico.start()
        
        self.data[user.id] = None
        
        # Return Nothing Image
        return gtk.gdk.Pixbuf(
            gtk.gdk.COLORSPACE_RGB, True, 8, 48, 48)
    
    def add_store(self, store, n):
        self.stores.append((store, n))

    def remove_store(self, store):
        for i in self.stores:
            if store == i[0]:
                self.stores.remove(i)

class NewIcon(threading.Thread):
    def __init__(self, user, stores, icons, semaphore):
        threading.Thread.__init__(self)
        self.setName("icon:%s" % user.screen_name)
        
        self.user = user
        self.stores = stores
        self.icons = icons
        self.semaphore = semaphore
    
    def _to_pixbuf(self, ico):
        # Load Pixbuf Loader and Create Pixbuf
        icoldr = gtk.gdk.PixbufLoader()
        icoldr.write(ico)
        icopix = icoldr.get_pixbuf()
        
        try: icoldr.close()
        except: icopix = None
        
        return icopix
    
    def run(self):
        # Icon Data Get
        self.semaphore.acquire()
        ico = urllib2.urlopen(self.user.profile_image_url).read()
        self.semaphore.release()
        icopix = self._to_pixbuf(ico)
        
        # Resize
        if icopix == None:
            # Try convert PIL, if installed Python Imaging Library
            try:
                import Image
            except:
                icopix = gtk.gdk.Pixbuf(
                    gtk.gdk.COLORSPACE_RGB, True, 8, 48, 48)
            else:
                img = Image.open(cStringIO.StringIO(ico))
                nimg = img.resize((48, 48))
                nico = cStringIO.StringIO()
                nimg.save(nico, "png")
                icopix = self._to_pixbuf(nico.getvalue())
        elif icopix.get_property("width") > 48:
            icopix = icopix.scale_simple(48, 48, gtk.gdk.INTERP_BILINEAR)
        
        # Add iconstore
        self.icons[self.user.id] = icopix
        
        # Icon Refresh
        for store, n in self.stores:
            i = store.get_iter_first()
            while i:
                uid = store.get_value(i, n)
                if uid == self.user.id:
                    gtk.gdk.threads_enter()
                    store.set_value(i, 0, icopix)
                    gtk.gdk.threads_leave()
                i = store.iter_next(i)
