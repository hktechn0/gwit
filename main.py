#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk

class Main:
    def __init__(self):
        glade = "gwit.glade"

        builder = gtk.Builder()
        builder.add_from_file(glade)
        builder.connect_signals(self)
        mainwin = builder.get_object("window1")
        mainwin.show_all()
        gtk.main()

if __name__ == "__main__":
    Main()
