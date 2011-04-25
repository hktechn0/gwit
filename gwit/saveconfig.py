#!/usr/bin/env python
#-*- coding: utf-8 -*-

import os
from ConfigParser import SafeConfigParser

class Config(object):
    CONF_PATH = os.path.expanduser("~/.gwit/config")
    
    @staticmethod
    def _open():
        confp = SafeConfigParser()    
        if os.path.isfile(Config.CONF_PATH):
            confp.read(Config.CONF_PATH)
        return confp
    
    @staticmethod
    def _close(confp):
        fp = open(Config.CONF_PATH, "w")
        confp.write(fp)
        fp.close()
    
    @staticmethod
    def save(section, key, value):
        confp = Config._open()
        confp.set(section, key, value)
        Config._close(confp)
    
    @staticmethod
    def save_section(conftuple):
        confp = Config._open()
        for section, key, value in conftuple:
            confp.set(section, key, str(value))
        Config._close(confp)
    
    @staticmethod
    def get(section, keys):
        confp = Config._open()
        items = dict(confp.items(section))
        return items[keys]
    
    @staticmethod
    def get_section(section):
        confp = Config._open()
        return dict(confp.items(section))
