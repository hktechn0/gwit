#!/usr/bin/env python
#-*- coding: utf-8 -*-

import os

import pygtk
pygtk.require('2.0')
import gtk

import twoauth

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
        self.builder = builder
        builder.add_from_file(setupglade)
        builder.connect_signals(self)
        
        self.oauth = twoauth.oauth(*self.keys)
        self.rtoken = self.oauth.request_token()
        self.authurl = self.oauth.authorize_url(self.rtoken)
        
        # Unmask lbutt once clicked
        lbutt = gtk.LinkButton(self.authurl, "Please Allow This Application")
        lbutt.connect("clicked", self.show_and_enable_pin)
        
        self.get("table1").attach(lbutt, 1, 2, 0, 1)
    
    def main(self):
        self.get("window1").show_all()
        gtk.main()
    
    def close(self, widget):
        gtk.main_quit()

    def get(self, name):
        return self.builder.get_object(name)

    def show_and_enable_pin(self, widget):
        urldlg = gtk.MessageDialog(buttons = gtk.BUTTONS_OK, message_format = self.authurl)
        urldlg.connect("response", self.show_and_enable_pin_close)
        urldlg.run()
        self.get("entry1").set_sensitive(True)
    
    def show_and_enable_pin_close(self, dialog, response_id):
        dialog.destroy()
        
    def on_button1_clicked(self, widget):
        pin = int(self.get("entry1").get_text())
        
        try:
            token = self.oauth.access_token(self.rtoken, pin)
        except Exception, e:
            print "[Error] %s" % e
            return
        
        self.keys.append(token["oauth_token"])
        self.keys.append(token["oauth_token_secret"])
        
        self.screen_name = unicode(token["screen_name"])
        
        lbl = gtk.Label()
        lbl.set_markup("<b>%s</b>" % self.screen_name)
        
        self.get("table1").attach(lbl, 1, 2, 2, 3)
        self.get("table1").show_all()
        
        self.get("button1").set_sensitive(False)
        self.get("entry1").set_sensitive(False)
        self.get("button3").set_sensitive(True)
    
    def on_button3_clicked(self, widget):
        self.ok = True
        self.get("window1").destroy()
        gtk.main_quit()
    
    def on_entry1_changed(self, widget):
        pin = widget.get_text()
        if len(pin) == 7 and pin.isdigit():
            self.get("button1").set_sensitive(True)
        else:
            self.get("button1").set_sensitive(False)
