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

class TwitterTools(object):
    _urlpattern = u'''(?P<url>https?://[^\s　]*)'''
    _userpattern = u'''@(?P<user>\w+)'''
    _hashpattern = u'''#(?P<hashtag>\w+)'''
    
    reurl = re.compile(_urlpattern)
    reuser = re.compile(_userpattern)
    rehash = re.compile(_hashpattern)
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
    # Text decoration
    @classmethod
    def get_decoration_text(cls, status):
        text = status.text
        
        # replace hashtags
        for h in cls.get_hashtags(status):
            text = text.replace(
                "#" + h,'<span foreground="#666666">#%s</span>' % h)
        
        # replace URL
        if not status.entities:
            text = cls.reurl.sub(
                '<span foreground="#0000FF" underline="single">\g<url></span>', text)
        else:
            urls = status.entities.urls
            if status.entities.get("media", None):
                urls.extend(status.entities.media)
            for i in urls:
                url = i.display_url if i.expanded_url else i.url
                text = text.replace(
                    i.url,'<span foreground="#0000FF" underline="single">%s</span>' % url)
        
        return text
    
    @classmethod
    def get_urls_from_text(cls, text):
        url_iter = cls.reurl.finditer(text)
        # shorten_url, display_url
        return [(i.group('url'), i.group('url')) for i in url_iter]
    
    @classmethod
    def get_urls(cls, status):
        if cls.isretweet(status):
            status = status.retweeted_status
        
        if status.entities:
            return [(i.url, i.display_url if i.expanded_url else i.url) 
                    for i in status.entities.urls]
        else:
            return cls.get_urls_from_text(status.text)
    
    @classmethod
    def get_media_urls(cls, status):
        if cls.isretweet(status):
            status = status.retweeted_status
        
        if status.entities and status.entities.get("media", None):
            return [(i.url, i.display_url if i.expanded_url else i.url) 
                    for i in status.entities.media]
        else:
            return []
    
    # User
    @classmethod
    def get_user_mentions(cls, status):
        if status.entities:
            return [i.screen_name for i in status.entities.user_mentions]
        else:
            match = cls.reuser.finditer(status.text)      
            return [i.group('user') for i in match]
    
    # Hashtags
    @classmethod
    def get_hashtags(cls, status):
        if cls.isretweet(status):
            status = status.retweeted_status
        
        if status.entities:
            return [i.text for i in status.entities.hashtags]
        else:
            match = cls.rehash.finditer(status.text)
            return [i.group('hashtag') for i in match]
    
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
        return bool(status.get("retweeted_status"))
    
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
    def replace_amp(cls, text):
        amp = text.find('&')
        if amp == -1:
            return text
        
        entity_match = cls.reamp.finditer(text)
        n = 0
        
        for m in entity_match:
            mname = m.groupdict().get("name", None)
            if mname not in ["gt", "lt", "amp"]:
                # cannot use htmlentitydefs cheeb(ry...
                startp = m.start("after") + n - 1
                endp = m.end("after") + n
                text = text[:startp] + m.expand("&amp;\g<after>") + text[endp:]
                n += 4
        
        return text
    
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

    @classmethod
    def get_tweet_length(cls, text, num_media = 0,
                         url_length = 20, https_url_length = 21,
                         media_length = 21):
        urls = cls.get_urls_from_text(text)
        num_url = len(urls)
        
        for url, _ in urls:
            text = text.replace(url, u"")
        
        return len(text) + url_length * num_url + media_length * num_media
