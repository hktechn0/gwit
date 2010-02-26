#!/usr/bin/env python
#-*- coding: utf-8 -*-

import re

class urlregex:
    urlpattern = u'''(?P<url>https?://[^\s　]*)'''
    
    def __init__(self):
        self.url = re.compile(self.urlpattern)
    
    def get_linked(self, string):
        return self.url.sub('<a href="\g<url>">\g<url></a>', string)

    def get_colored(self, string):
        url_iter = self.url.finditer(string)
        urls = list()
        for i in url_iter:
            urls.append(i.group('url'))
        
        string = self.url.sub('<span foreground="#0000FF" underline="single">\g<url></span>', string)
        
        return string, tuple(urls)
