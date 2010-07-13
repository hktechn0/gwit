#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk
import gobject

import threading

class StatusDetail(gtk.VPaned):
    _old_alloc = None
    
    def __init__(self, status, twitterapi, icons):
        gtk.VPaned.__init__(self)
        
        ico = gtk.image_new_from_pixbuf(icons.get(status.user))
        markup = "<big><b>%s</b></big> - %s\n%s\n<small><span foreground='#666666'>%s via %s</span></small>"
        text = gtk.Label()
        text.set_padding(30, 10)
        text.set_alignment(0, 0.5)
        text.set_line_wrap(True)
        label_text = markup % (
            status.user.screen_name,
            status.user.name,
            status.text,
            status.created_at.strftime("%Y/%m/%d %H:%M:%S"),
            status.source_name)
        text.set_markup(label_text)
        
        hbox = gtk.HBox()
        hbox.set_border_width(10)
        hbox.pack_start(ico, expand = False, fill = False)
        hbox.pack_start(text)
        
        self.store = gtk.ListStore(gtk.gdk.Pixbuf, str, gobject.TYPE_INT64)
        treeview = gtk.TreeView(self.store)
        treeview.set_headers_visible(False)
        treeview.set_rules_hint(True)
        treeview.append_column(gtk.TreeViewColumn("Icon", gtk.CellRendererPixbuf(), pixbuf = 0))
        treeview.append_column(gtk.TreeViewColumn("Status", gtk.CellRendererText(), markup = 1))
        
        win = gtk.ScrolledWindow()
        win.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        win.add(treeview)
        
        self.pack1(hbox, shrink = False)
        self.pack2(win)
        
        self.twitter = twitterapi
        self.icons = icons
        
        t = threading.Thread(target = self.get_conversation, args = (status,))
        t.setDaemon(True)
        t.start()

        self.show_all()
    
    def get_conversation(self, status):
        s = status
        i = s.in_reply_to_status_id
        
        while i != None:
            if i in self.twitter.statuses:
                s = self.twitter.statuses[i]
                self.store.append(
                    (self.icons.get(s.user),
                     "<b>%s</b>\n%s" % (s.user.screen_name, s.text),
                     s.user.id))
                i = s.in_reply_to_status_id
            else:
                statuses = self.twitter.api_wrapper(
                    self.twitter.api.user_timeline,
                    s.in_reply_to_user_id, count = 200, max_id = i)
                self.twitter.add_statuses(statuses)
