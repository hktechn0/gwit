#-*- coding: utf-8 -*-

import urllib
import urllib2
import json

class Bitly(object):
    apihost = "http://api.bitly.com/"
    login = "hktechno"
    apikey = "R_7e72e80b44a3f7c761575c71862f17f3"
    cache = dict()
    
    @classmethod
    def set_login(cls, login, apikey):
        cls.login = login
        cls.apikey = apikey
    
    @classmethod
    def shorten(cls, longurl):
        path = "v3/shorten"
        params = {"longUrl": longurl,
                  "login": cls.login,
                  "apikey": cls.apikey}
        
        c = cls.cache.get(hash(longurl))
        if c:
            return c
        else:
            c = urllib2.urlopen(cls.apihost + path, urllib.urlencode(params))
            r = json.loads(c.read())
            
            if r["status_code"] != 200: return
            
            shorturl = r["data"]["url"]
            cls.cache[hash(longurl)] = shorturl
            return shorturl
    
    # shorturls, hashes: string or sequence(list, tuple)
    @classmethod
    def expand(cls, shorturls = None, hashes = None):
        path = "v3/expand"
        
        params = {"login": cls.login,
                  "apikey": cls.apikey}
        
        if not shorturls:
            shorturls = tuple()
            
        if not hashes:
            hashes = tuple()
        
        try:
            iter(horturls)
        except TypeError:
            shorturls = (shorturls,)

        try:
            iter(hashes)
        except TypeError:
            hashes = (hashes,)
        
        params += [("shortUrl", i) for i in shorturls]
        params += [("hash", i) for i in hashes]
        
        c = cls.cache.get(hash(longurl))
        if c:
            return c
        else:
            c = urllib2.urlopen(cls.apihost + path, urllib.urlencode(params))
            r = json.loads(c.read())
            if r["status_code"] != 200: return
            
            longurls = list()
            
            for i in r["expand"]:
                longurl = i.get("long_url")
                shorturl = i.get("short_url")
                if shorturl:
                    cls.cache[hash(longurl)] = shorturl
                
                longurls.append(longurl)
            
            return longurls
