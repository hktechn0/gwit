#!/usr/bin/env python
#-*- coding: utf-8 -*-

import os
from ConfigParser import SafeConfigParser

CONF_PATH = os.path.expanduser("~/.gwit/config")

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

def get_configs(section):
    confp = _open()
    return dict(confp.items(section))

def _open():
    confp = SafeConfigParser()    
    if os.path.isfile(CONF_PATH):
        confp.read(CONF_PATH)
    
    return confp

def _close(confp):
    fp = open(CONF_PATH, "w")
    confp.write(fp)
    fp.close()
