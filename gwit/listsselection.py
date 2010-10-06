#-*- coding: utf-8 -*-

'''Twitter "Lists" selection widget
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

class ListsView(gtk.ScrolledWindow):
    twitter = None
    iconstore = None
    
    def __init__(self, user = None, memberships = False):
        gtk.ScrolledWindow.__init__(self)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        
        self.store = gtk.ListStore(gtk.gdk.Pixbuf, str, gobject.TYPE_INT64, gobject.TYPE_INT64, gtk.gdk.Pixbuf, str)
        self.treeview = gtk.TreeView(self.store)
        self.treeview.set_headers_visible(False)
        self.treeview.set_rules_hint(True)
        self.treeview.connect("row-activated", self.on_treeview_row_activated)
        
        self.treeview.append_column(
            gtk.TreeViewColumn("Icon", gtk.CellRendererPixbuf(), pixbuf = 0))
        listname = gtk.TreeViewColumn("Lists", gtk.CellRendererText(), markup = 1)
        listname.set_expand(True)
        self.treeview.append_column(listname)
        self.treeview.append_column(
            gtk.TreeViewColumn("Private", gtk.CellRendererPixbuf(), pixbuf = 4))
        cell_count = gtk.CellRendererText()
        cell_count.set_property("xpad", 10)
        self.treeview.append_column(
            gtk.TreeViewColumn("Count", cell_count, markup = 5))
        
        self.btn_more = gtk.Button("Get your lists!")
        self.btn_more.connect("clicked", self.on_button_more_clicked)
        
        vbox = gtk.VBox()
        vbox.pack_start(self.treeview, expand = False)
        vbox.pack_start(self.btn_more, expand = False)
        self.add_with_viewport(vbox)
        
        if user == None:
            self.user = self.twitter.myname
        else:
            self.user = user
        
        self.memberships = memberships
        
        self.lists = dict()
        self._cursor = -1
        
        self.iconstore.add_store(self.store, 2)
    
    # Load Lists index
    def load(self):
        if self.memberships:
            data = self.twitter.api_wrapper(self.twitter.api.lists_memberships, self.user, cursor = self._cursor)
            lists = data["lists"]
        else:
            data = self.twitter.api_wrapper(self.twitter.api.lists_subscriptions, self.user, cursor = self._cursor)
            lists = data["lists"]
            
            # get all my lists if first load
            if self._cursor == -1:
                c = -1
                mylists = list()
                while c != 0:
                    mydata = self.twitter.api_wrapper(self.twitter.api.lists_index, self.user, cursor = c)
                    mylists.extend(mydata["lists"])
                    c = int(mydata["next_cursor"])
                lists[0:0] = mylists
        
        for l in reversed(lists):
            user = l["user"]
            userid = int(user["id"])
            screen_name = user["screen_name"]
            
            listid = int(l["id"])
            listname = l["name"]
            description = l["description"]

            text = "@%s/%s" % (screen_name, listname)
            if description != None:
                text += "\n<small><span foreground='#666666'>%s</span></small>" % description
            
            count = "Following: %s\nFollowers: %s" % (l["member_count"], l["subscriber_count"])
            
            if l["mode"] == "private":
                private_ico = self.render_icon("gtk-dialog-authentication", gtk.ICON_SIZE_BUTTON)
            else:
                private_ico = None
            
            self.twitter.add_user(user)
            self.lists[listid] = l
            self.store.append((self.iconstore.get(l["user"]),
                               text, userid, listid, private_ico, count))
        
        self._cursor = int(data["next_cursor"])
        
        if self._cursor == 0:
            self.btn_more.set_sensitive(False)
            self.btn_more.hide()
        else:
            self.btn_more.set_label("Get more 20 lists.")        
    
    ### Event
    def on_button_more_clicked(self, widget):
        self.load()
    
    def on_treeview_row_activated(self, treeview, path, view_column):
        listid = treeview.get_model()[path][3]
        l = self.lists[listid]
        listlabel = "@%s/%s" % (l["user"]["screen_name"], l["name"])
        auth = True if l["mode"] == "private" else False
        self.twitter.new_timeline("L: %s" % listlabel, "lists_statuses",
                                  list_id = l["id"], user = l["user"]["id"], auth = auth)


class ListsSelection(gtk.Notebook):
    def __init__(self):
        gtk.Notebook.__init__(self)
        
        sub = ListsView(memberships = False)
        mem = ListsView(memberships = True)
        
        self.append_page(sub, gtk.Label("Subscriptions"))
        self.append_page(mem, gtk.Label("Memberships"))

        self.show_all()
