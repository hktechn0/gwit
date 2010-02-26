#!/usr/bin/env python
#-*- coding: utf-8 -*-

import os
from ConfigParser import SafeConfigParser

def save_config(section, key, value):
    confp = _open()    
    confp.set(section, key, value)
    _close(confp)

def save_configs(conftuple):
    confp = _open()    
    for section, key, value in conftuple:
        confp.set(section, key, str(value))
    _close(confp)

def get_config(section, keys):
    confp = _open()
    items = dict(confp.items(section))
    return items[keys]

def _open():
    confp = SafeConfigParser()
    conf_path = os.path.join(
        os.path.dirname(__file__), "gwit.conf")
    
    if os.path.isfile(conf_path):
        confp.read(conf_path)
    
    return confp

def _close(confp):
    conf_path = os.path.join(
        os.path.dirname(__file__), "gwit.conf")
    
    fp = open(conf_path, "w")
    confp.write(fp)
    fp.close()
