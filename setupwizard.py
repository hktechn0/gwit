#!/usr/bin/env python
#-*- coding: utf-8 -*-

import os

import pygtk
pygtk.require('2.0')
import gtk

import twoauth
from objects import GtkObjects

class SetupWizard:
    ok = False
    keys = [
        "kcygnhE2KNS8U6kwmIlMQ",
        "l8yaXsNHtFviEZCXiv1OEVAZLe6TL8TPYX72TbcDc",
        ]

    def __init__(self):
        setupglade = os.path.join(
            os.path.dirname(__file__), "setupwizard.glade")
        
        builder = gtk.Builder()
        builder.add_from_file(setupglade)
        builder.connect_signals(self)
        self.obj = GtkObjects(builder.get_objects())
        
        self.oauth = twoauth.oauth(*self.keys)
        self.rtoken = self.oauth.request_token()
        authurl = self.oauth.authorize_url(self.rtoken)

        # Unmask lbutt once clicked
        lbutt = gtk.LinkButton(authurl, "Please Allow This Application")
        lbutt.connect("clicked", self.enable_pin_entry)


        self.obj.table1.attach(lbutt, 1, 2, 0, 1)
        
    def main(self):
        self.obj.window1.show_all()
        gtk.main()
    
    def close(self, widget):
        gtk.main_quit()

    def enable_pin_entry(self, widget):
        self.obj.entry1.set_sensitive(True)

    def on_button1_clicked(self, widget):
        pin = int(self.obj.entry1.get_text())
        
        try:
            token = self.oauth.access_token(self.rtoken, pin)
        except:
            return
        
        self.keys.append(token["oauth_token"])
        self.keys.append(token["oauth_token_secret"])
        
        self.screen_name = unicode(token["screen_name"])
        
        lbl = gtk.Label()
        lbl.set_markup("<b>%s</b>" % self.screen_name)
        
        self.obj.table1.attach(lbl, 1, 2, 2, 3)
        self.obj.table1.show_all()
        
        self.obj.button1.set_sensitive(False)
        self.obj.entry1.set_sensitive(False)
        self.obj.button3.set_sensitive(True)

    def on_button3_clicked(self, widget):
        self.ok = True
        self.obj.window1.destroy()
        gtk.main_quit()
    
    def on_entry1_changed(self, widget):
        pin = widget.get_text()
        if len(pin) == 7 and pin.isdigit():
            self.obj.button1.set_sensitive(True)
        else:
            self.obj.button1.set_sensitive(False)
