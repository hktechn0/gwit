#-*- coding: utf-8 -*-

'''Useful functions for twitter
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


import re
import datetime
import htmlentitydefs

class TwitterTools:
    _urlpattern = u'''(?P<url>https?://[^\s　]*)'''
    _userpattern = u'''@(?P<user>\w+)'''
    reurl = re.compile(_urlpattern)
    reuser = re.compile(_userpattern)
    reentity = re.compile("&([A-Za-z]+);")
    reamp = re.compile("&(?P<after>((?P<name>[A-Za-z]+);)?[^&]*)")
    
    @classmethod
    def get_footer(cls, status):
        time = cls.get_time_hms(status.created_at)
        ago = cls.get_time_ago(status.created_at)
        
        if "source" in status.keys():
            source = status.source_name
            footer = u"[%s] %s via %s" % (
                time, ago, source)
        else:
            fotter = "DirectMessage?"
        
        return footer
    
    ## Status
    # URL
    @classmethod
    def get_colored_url(cls, string):
        return cls.reurl.sub(
            '<span foreground="#0000FF" underline="single">\g<url></span>',
            string)
    
    @classmethod
    def get_urls(cls, string):
        url_iter = cls.reurl.finditer(string)
        urls = list()
        for i in url_iter:
            urls.append(i.group('url'))
        
        return tuple(urls)
    
    # User
    @classmethod
    def get_users(cls, string):
        match = cls.reuser.finditer(string)
        
        users = list()
        for i in match:
            users.append(i.group('user'))
        
        return users
    
    # source
    @staticmethod
    def get_source_name(source):
        if source == "web":
            return u"web"
        else:
            i = source.find(">")
            if i != -1:
                return unicode(source[i + 1:-4])
            else:
                return unicode(source)
    
    ## Datetime
    @staticmethod
    def get_datetime(timestr):
        # Sample
        # Wed Nov 18 18:54:12 +0000 2009
        format = "%m %d %H:%M:%S +0000 %Y"
        m = {
            'Jan' : 1, 'Feb' : 2, 'Mar' : 3, 
            'Apr' : 4, 'May' : 5, 'Jun' : 6,
            'Jul' : 7, 'Aug' : 8, 'Sep' : 9, 
            'Oct' : 10, 'Nov' : 11, 'Dec' : 12
            }
        
        t = "%02d %s" % (m[timestr[4:7]], timestr[8:])
        dt = datetime.datetime.strptime(t, format)
        offset = time.altzone if time.daylight else time.timezone
        dt -= datetime.timedelta(seconds = offset)
        return dt
    
    @staticmethod
    def get_time_hms(dt):
        return dt.strftime("%H:%M:%S")
    
    @staticmethod
    def get_time_ago(dt):
        now = datetime.datetime.now()

        if now < dt:
            return "Just now!"
        
        ago = now - dt
        hours = ago.seconds / 3600
        minutes = ago.seconds / 60
        
        if ago.days:
            if ago.days == 1:
                return "1 day ago"
            else:
                return "%d days ago" % ago.days
        elif hours:
            if hours == 1:
                return "1 hour ago"
            else:
                return "%d hours ago" % hours
        elif minutes:
            if minutes == 1:
                return "1 minute ago"
            else:
                return "%d minutes ago" % minutes
        elif ago.seconds:
            if ago.seconds == 1:
                return "1 second ago"
            else:
                return "%d seconds ago" % ago.seconds
        else:
            return "Just now!"
        
    ## Retweet
    @staticmethod
    def isretweet(status):
        return "retweeted_status" in status.keys()
    
    ## Lists
    @staticmethod
    def get_listed_count(api, ret = None):
        listed = 0
        cursor = -1

        while True:
            lists = api.lists_memberships(cursor = cursor)
            cursor = int(lists["next_cursor"])
            listed += len(lists["lists"])
            if cursor <= 0:
                break
        
        if ret != None: ret = listed
        
        return listed
    
    @staticmethod
    def listed_count_background(api, ret):
        th = threading.Thread(target = listed_count, args = (api, ret))
        th.isDaemon()
        th.start()

    # Replace & -> &amp;
    @classmethod
    def replace_amp(cls, string):
        amp = string.find('&')
        if amp == -1:
            return string
        
        entity_match = cls.reamp.finditer(string)
        
        for m in entity_match:
            if m.group("name") not in ["gt", "lt", "amp"]:
                # cannot use htmlentitydefs cheeb(ry...
                string = string.replace(m.group(), m.expand("&amp;%s" % m.group("after")))
        
        return string
    
    @classmethod
    def replace_htmlentity(cls, string):
        amp = string.find('&')
        if amp == -1:
            return string
        
        entity_match = cls.reentity.findall(string)
        
        for name in entity_match:
            if name in htmlentitydefs.name2codepoint:
                c = htmlentitydefs.name2codepoint[name]
                string = string.replace("&%s;" % name, unichr(c))
        
        return string
