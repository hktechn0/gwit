#-*- coding: utf-8 -*-

'''Treeview for timeline statuses
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
import pango

import re
from twittertools import TwitterTools

import time
import threading
import webbrowser

class StatusView(gtk.TreeView):
    color = (None, None, None, None, None)
    pmenu = None
    
    favico_y = None
    favico_n = None
    
    twitter = None
    iconstore = {}
    iconmode = True
    
    def __init__(self):
        gtk.TreeView.__init__(self)
        
        self.store = gtk.ListStore(
            gtk.gdk.Pixbuf, str,
            gobject.TYPE_INT64, gobject.TYPE_INT64, str,
            gtk.gdk.Pixbuf)
        self.store.set_sort_column_id(2, gtk.SORT_DESCENDING)
        
        self.set_model(self.store)
        self.set_headers_visible(False)
        self.set_rules_hint(True)
        self.connect("size-allocate", self.on_treeview_width_changed)
        self.connect("cursor-changed", self.on_treeview_cursor_changed)
        self.connect("row_activated", self.on_treeview_row_activated)
        self.connect("motion-notify-event", self.on_treeview_motion_notify)
        self.connect("leave-notify-event", self.on_treeview_leave_notify)
        self.connect("destroy", self.on_treeview_destroy)
        self.connect("button-press-event", self.on_treeview_button_press)
        
        # Setup icon column (visible is False if no-icon)
        cell_p = gtk.CellRendererPixbuf()
        col_icon = gtk.TreeViewColumn("Icon", cell_p, pixbuf = 0)
        col_icon.set_visible(self.iconmode)
        
        # Setup status column
        cell_t = gtk.CellRendererText()
        cell_t.set_property("wrap-mode", pango.WRAP_CHAR)
        col_status = gtk.TreeViewColumn("Status", cell_t, markup = 1)
        col_status.set_property("sizing", gtk.TREE_VIEW_COLUMN_FIXED)
        col_status.set_expand(True)
        
        # Setup fav column
        cell_fav = gtk.CellRendererPixbuf()
        col_fav = gtk.TreeViewColumn("Fav", cell_fav, pixbuf = 5)
        col_fav.set_property("sizing", gtk.TREE_VIEW_COLUMN_FIXED)
        col_fav.set_property("fixed-width", 40)
        
        # Add background color at column_id 4
        col_icon.add_attribute(cell_p, "cell-background", 4)
        col_status.add_attribute(cell_t, "cell-background", 4)
        col_fav.add_attribute(cell_fav, "cell-background", 4)
        self.append_column(col_icon)
        self.append_column(col_status)
        self.append_column(col_fav)
    
        # Add timeline to IconStore 
        if self.iconmode:
            self.iconstore.add_store(self.store, 3)
        
        self.added = False
        
        # for motion notify
        self._old_path = None
        # for width changed
        self._old_width = None
    
    # Get selected status
    def get_selected_status(self):
        path, column = self.get_cursor()
        return self.get_status(path) if path != None else None
    
    # Get status from treeview path
    def get_status(self, path):
        i = self.store[path][2]
        return self.twitter.statuses[i]
    
    # get status from mouse point
    def get_status_from_point(self, x, y):
        path = self.get_path_at_pos(x, y)
        return self.get_status(path) if path != None else None

    def favorite_selected_status(self, path):
        path, column = self.get_cursor()
        return self.favorite_status(path)
    
    def favorite_status(self, path):
        status = self.get_status(path)
        
        # Toggle favorited
        if status.favorited:
            self.twitter.api_wrapper(
                self.twitter.api.favorite_destroy, status.id)
            self.store[path][5] = self.favico_y
        else:
            self.twitter.api_wrapper(
                self.twitter.api.favorite_create, status.id)
            self.store[path][5] = self.favico_n

        status.favorited = not status.favorited
    
    # Set background color
    def set_color(self, colortuple):
        self.color = tuple(colortuple)
    
    # Tweet menu setup
    def menu_setup(self, status):
        # Get Urls
        urls = TwitterTools.get_urls(status.text if "retweeted_status" not in status.keys()
                                     else status.retweeted_status.text)
        # Get mentioned users
        users = TwitterTools.get_users(status.text)
        
        # URL Menu
        m = gtk.Menu()
        if urls:
            # if exist url in text, add menu
            for i in urls:
                label = "%s..." % i[:47] if len(i) > 50 else i
                
                # Menuitem create
                item = gtk.ImageMenuItem(label)
                item.set_image(gtk.image_new_from_stock("gtk-new", gtk.ICON_SIZE_MENU))
                # Connect click event (open browser)
                item.connect("activate", self.on_menuitem_url_clicked, i)
                # append to menu
                m.append(item)
        else:
            # not, show None
            item = gtk.MenuItem("None")
            item.set_sensitive(False)
            m.append(item)
        
        # urls submenu append
        self.pmenu.get_children()[-1].set_submenu(m)
        
        # Mentioned User Menu
        mm = gtk.Menu()
        if users:
            for i in users:
                # Menuitem create
                item = gtk.ImageMenuItem("@%s" % i.replace("_", "__"))
                item.set_image(gtk.image_new_from_stock("gtk-add", gtk.ICON_SIZE_MENU))
                # Connect click event (add tab)
                item.connect("activate", self.on_menuitem_user_clicked, i)
                # append to menu
                mm.append(item)
        else:
            # not, show None
            item = gtk.MenuItem("None")
            item.set_sensitive(False)
            mm.append(item)
        
        self.pmenu.get_children()[-2].set_submenu(mm)
        
        # Show popup menu
        m.show_all()
        mm.show_all()
    
    
    ########################################
    # Execute in Background Thread Methods    
    
    # Prepend new stat uses
    def prepend_new_statuses(self, new_ids):
        # pack New Status
        statuses = (self.status_pack(i) for i in new_ids)
        
        # Set added flag (for auto scroll
        self.added = True
        
        # New Status Prepend to Liststore (Add row)
        for i in statuses:
            gtk.gdk.threads_enter()
            self.store.prepend(i)
            gtk.gdk.threads_leave()
        
        self.color_status()
    
    def status_pack(self, i):
        status = self.twitter.statuses[i]
        background = None
        
        name = status.user.screen_name
        
        if status.retweeted_status != None:
            rtstatus = status
            status = status.retweeted_status
            name = "%s <span foreground='#333333'><small>- Retweeted by %s</small></span>" % (
                status.user.screen_name, rtstatus.user.screen_name)
        
        if status.user.id in self.twitter.followers or self.twitter.followers == None:
            # Bold screen_name if follower
            tmpl = "<b>%s</b>\n%s"
        else:
            # or gray
            tmpl = "<span foreground='#666666'><b>%s</b></span>\n%s"
        
        # colord url
        text = TwitterTools.get_colored_url(status.text)
        # screen_name + text
        message = tmpl % (name, text)
        
        # replace no entity & -> &amp;
        message = TwitterTools.replace_amp(message)
        
        # Favorite
        favico = self.favico_y if status.favorited else self.favico_n
        
        # call main method, mentions check
        self.on_status_added(i)
        
        return (self.iconstore.get(status.user),
                message,
                long(i), long(status.user.id),
                background, favico)
    
    # Color status
    def color_status(self, status = None):
        t = threading.Thread(target=self.color_status_in_thread, args=(status,))
        t.setName("color_status")
        t.start()
    
    def color_status_in_thread(self, status = None):
        myname = self.twitter.myname
        myid = self.twitter.me.id if self.twitter.me != None else -1
        
        # if not set target status
        if status == None:
            status = self.get_selected_status()
        
        for row in self.store:
            bg = None
            
            status_id = row[2]
            s = self.twitter.statuses[status_id]
            u = s.user
            
            if u.id == myid:
                # My status (Blue)
                bg = self.color[0]
            elif s.in_reply_to_user_id == myid or \
                    s.text.find("@%s" % myname) != -1:
                # Reply to me (Red)
                bg = self.color[1]
            
            if status:
                if s.id == status.in_reply_to_status_id:
                    # Reply to (Orange)
                    bg = self.color[2]
                elif u.id == status.in_reply_to_user_id:
                    # Reply to other (Yellow)
                    bg = self.color[3]
                elif u.id == status.user.id:
                    # Selected user (Green)
                    bg = self.color[4]
            
            gtk.gdk.threads_enter()
            self.store[row.path][4] = bg
            gtk.gdk.threads_leave()
    
    
    ########################################
    # Gtk Signal Events    
    
    # Status Clicked
    def on_treeview_cursor_changed(self, treeview):
        status = self.get_selected_status()
        self.color_status(status)
        if self.pmenu != None:
            self.menu_setup(status)
        self.on_status_selection_changed(status)
    
    # Status double clicked
    def on_treeview_row_activated(self, treeview, path, view_column):
        status = self.get_status(path)
        self.on_status_activated(status)
    
    # Menu popup
    def on_treeview_button_press(self, widget, event):
        if event.button == 3 and self.pmenu != None:
            self.pmenu.show_all()
            if self.get_selected_status().user.screen_name != self.twitter.myname:
                self.pmenu.get_children()[4].hide()
            self.pmenu.popup(None, None, None, event.button, event.time)
        elif event.button == 1:
            # fav button
            path_at_pos = self.get_path_at_pos(int(event.x), int(event.y))
            if path_at_pos == None: return
            path, column = path_at_pos[:2]
            
            if self.get_columns().index(column) == 2:
                self.favorite_status(path)
    
    def reset_favico(self, path):
        if path != None:
            status = self.get_status(path)
            if not status.favorited:
                self.store[path][5] = self.favico_n
    
    def on_treeview_motion_notify(self, widget, event):
        # blink fav icon when mouse over
        path_at_pos = self.get_path_at_pos(int(event.x), int(event.y))
        if path_at_pos == None: return
        path, column = path_at_pos[:2]
        
        if self.get_columns().index(column) == 2:
            self.store[path][5] = self.favico_y
        else:
            self.reset_favico(path)
        
        if self._old_path != path:
            self.reset_favico(self._old_path)
            self._old_path = path
    
    def on_treeview_leave_notify(self, widget, event):
        self.reset_favico(self._old_path)
        self._old_path = None
    
    # Treeview width changed Event (text-wrap-width change)
    def on_treeview_width_changed(self, treeview, allocate):
        # Get Treeview Width
        width = treeview.get_allocation().width
        
        # Get Treeview Columns
        columns = treeview.get_columns()
        
        # Get !("Status") width
        width2 = 0
        for i in columns[:1] + columns[2:]:
            width2 += i.get_property("width")
        
        # -10 is margin
        text_width = width - width2 - 10
        
        # Really changed?
        # (this event is called when add statuses too.)
        if self._old_width == text_width:
            return
        else:
            self._old_width = text_width
        
        # Set "Status" width
        cellr = columns[1].get_cell_renderers()
        cellr[0].set_property("wrap-width", text_width)
        
        def refresh_text():
            # Reset all data to change row height
            for row in self.store:
                # Maybe no affects performance
                # if treeview.allocation.width != width:
                #     break
                status_id = row[2]
                packed_row = self.status_pack(status_id)
                
                gtk.gdk.threads_enter()
                self.store[row.path] = packed_row
                gtk.gdk.threads_leave()
            
            self.color_status_in_thread()
        
        t = threading.Thread(target=refresh_text)
        t.setName("refresh_text")
        t.start()
    
    def on_treeview_destroy(self, treeview):
        self.iconstore.remove_store(self.store)
    
    # dummy events and methods
    def on_status_added(self, *args, **kwargs): pass
    def on_status_selection_changed(self, *args, **kwargs): pass
    def on_status_activated(self, *args, **kwargs): pass
    def new_timeline(self, *args, **kwargs): pass
    
    ########################################
    # Tweet menu event
    
    # Open Web browser if url menuitem clicked
    def on_menuitem_url_clicked(self, menuitem, url):
        webbrowser.open_new_tab(url)
    
    # Add user timeline tab if mentioned user menu clicked
    def on_menuitem_user_clicked(self, menuitem, sname):
        user = self.twitter.get_user_from_screen_name(sname)
        if user != None:
            self.new_timeline("@%s" % sname, "user_timeline", user = user.id)
        else:
            # force specify screen_name if not found
            self.new_timeline("@%s" % sname, "user_timeline", user = sname, sn = True)
        
        return True
