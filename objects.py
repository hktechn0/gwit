#!/usr/bin/env python
#-*- coding: utf-8 -*-

class GtkObjects:
    def __init__(self, objs):
        for i in objs:
            try:
                setattr(self, i.name, i)
            except:
                setattr(self, i.get_name(), i)
