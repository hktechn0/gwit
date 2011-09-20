#-*- coding: utf-8 -*-

'''Show status detail widget
'''

################################################################################
#
# Copyright (c) 2010 University of Tsukuba Linux User Group
#
# This file is part of "gwit".
#
# "gwit" is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "gwit" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with "gwit".  If not, see <http://www.gnu.org/licenses/>.
#
################################################################################


import pygtk
pygtk.require('2.0')
import gtk
import gobject

import threading
from statusview import StatusView
from twittertools import TwitterTools

class StatusDetail(gtk.VPaned):
    twitter = None
    iconstore = None

    def __init__(self, status):
        gtk.VPaned.__init__(self)
        
        ico = gtk.image_new_from_pixbuf(self.iconstore.get(status.user))
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
        label_text = TwitterTools.replace_amp(label_text)
        text.set_markup(label_text)
        
        hbox = gtk.HBox()
        hbox.set_border_width(10)
        hbox.pack_start(ico, expand = False, fill = False)
        hbox.pack_start(text)

        self._box = gtk.VBox()
        self._box.pack_start(hbox)
        
        self.view = StatusView()
                
        win = gtk.ScrolledWindow()
        win.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        win.add(self.view)
        
        self.pack1(self._box, shrink = False)
        self.pack2(win)
        
        t = threading.Thread(target = self.get_conversation, args = (status,))
        t.setDaemon(True)
        t.start()
        
        self.show_all()
    
    def get_conversation(self, status):
        s = status
        i = s.in_reply_to_status_id
        lim = 0
        
        # Loading label
        loading = gtk.Label("Now Loading...")
        self._box.pack_end(loading)

        while i != None:
            if i in self.twitter.statuses:
                # already exists status
                self.view.prepend_new_statuses([i])
                s = self.twitter.statuses[i]
                i = s.in_reply_to_status_id
                lim = 0
            else:
                # not found in cache
                statuses = self.twitter.api_wrapper(
                    self.twitter.api.user_timeline,
                    s.in_reply_to_user_id, count = 20, max_id = i,
                    include_entities = 1)
                self.twitter.add_statuses(statuses)
                lim += 1

            if lim >= 3: break
        
        self._box.remove(loading)
