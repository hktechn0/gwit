#!/usr/bin/env python

from distutils.core import setup

setup(name = "gwit",
      version = "0.9.2",
      description = "Powerful Twitter client for Linux using PyGTK.",
      author = "University of Tsukuba Linux User Group",
      author_email = "staff@tsukuba-linux.org",
      url = "http://gwit.sourceforge.jp/",
      packages = ["gwitlib", "twoauth"],
      scripts = ["gwit"],
      package_data = {"gwitlib": ["images/*", "ui/*"]}
      )
