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
        self.default_icon = gtk.gdk.pixbuf_new_from_file("none.png")
    
    def get(self, user):
        if user.id in self.data:
            # if exist in cache
            return self.data[user.id]
        elif self.iconmode:
            # or get new icon
            self.new(user)
        
        # Return Default Image
        return self.default_icon
    
    def new(self, user):
        # New Icon thread start if iconmode is True
        self.data[user.id] = self.default_icon
        newico = NewIcon(user, self.stores, self.data, self.semaphore)
        newico.start()
    
    def add_store(self, store, n):
        self.stores.append((store, n))

    def remove_store(self, store):
        for i in self.stores:
            if store == i[0]:
                self.stores.remove(i)

class NewIcon(threading.Thread):
    def __init__(self, user, stores, icons, semaphore):
        threading.Thread.__init__(self)
        self.setDaemon(True)
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
        # Icon Data Get (if can get semaphore or block)
        self.semaphore.acquire()
        ico = urllib2.urlopen(self.user.profile_image_url).read()
        self.semaphore.release()
        icopix = self._to_pixbuf(ico)
        
        # Resize
        if icopix == None:
            # Try convert PIL, if installed Python Imaging Library
            try:
                import Image
            except: return
            else:
                img = Image.open(cStringIO.StringIO(ico))
                nimg = img.resize((48, 48))
                nico = cStringIO.StringIO()
                nimg.save(nico, "png")
                icopix = self._to_pixbuf(nico.getvalue())
        elif icopix.get_property("width") > 48:
            icopix = icopix.scale_simple(48, 48, gtk.gdk.INTERP_BILINEAR)
        
        if icopix == None: return
        
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
