#!/usr/bin/env python
# type: ignore

import os
import json

PLUGIN_PATHS = ['picturesofultra/plugins']
PLUGINS = ['runningimages', 'sitemap']

LOAD_CONTENT_CACHE = False
DELETE_OUTPUT_DIRECTORY = True
AUTHOR = 'Pictures Of Ultra'
SITENAME = 'Pictures of Ultra'
SITEPITCH = 'An opinionated index of documentary films about running'
SITE_DESCRIPTION = 'More that 300 references on films about ultrarunning and trailrunning, From the 90\'s to today, from elite to back of the pack, if it was filmed, you will find it here.'
SITEURL = ''

PATH = 'content'

TIMEZONE = 'Europe/Paris'

DEFAULT_LANG = 'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (('Pelican', 'https://getpelican.com/'),
         ('Python.org', 'https://www.python.org/'),
         ('Jinja2', 'https://palletsprojects.com/p/jinja/'),
         ('You can modify those links in your config file', '#'),)

# Social widget
SOCIAL = (('You can add links in your config file', '#'),
          ('Another social link', '#'),)

DEFAULT_PAGINATION = 20
ARTICLE_ORDER_BY = "reversed-release_year"

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True

# Paths
ARCHIVES_SAVE_AS = ''
ARTICLE_PATHS = ['videos']
ARTICLE_EXCLUDES = []
ARTICLE_SAVE_AS = 'videos/{slug}.html'
ARTICLE_URL = 'videos/{slug}.html'
AUTHOR_SAVE_AS = ''
PAGE_SAVE_AS = '{slug}.html'
PAGE_URL = '{slug}.html'
TAG_SAVE_AS = 'tags/{slug}.html'
TAGS_SAVE_AS = 'tags.html'
TAG_URL = 'tags/{slug}.html'
CATEGORY_SAVE_AS = 'years/{slug}.html'
CATEGORIES_SAVE_AS = ''
CATEGORY_URL = 'years/{slug}.html'
INDEX_SAVE_AS = 'videos.html'

THEME = 'themes/runningimages'
THEME_CATEGORIES = {
    'x-1999':    { 'title': 'before 1999'},
    '2000-2004': { 'title': '2000 to 2005' },
    '2005-2009': { 'title': '2005 to 2009' },
    '2010-2014': { 'title': '2010 to 2014' },
    '2015': { 'title': '2015' },
    '2016': { 'title': '2016' },
    '2017': { 'title': '2017' },
    '2018': { 'title': '2018' },
    '2019': { 'title': '2019' },
    '2020': { 'title': '2020' },
    '2021': { 'title': '2021' }
}
THEME_CATEGORIES_ORDERED = ['x-1999', '2000-2004', '2005-2009', '2010-2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021']
with open('sitemeta.json') as f:
    sitemeta = json.load(f)
TAG_TYPES = sitemeta['tags']

# Github custom domain : https://docs.getpelican.com/en/latest/tips.html#copy-static-files-to-the-root-of-your-site
STATIC_PATHS = ['images', 'extra', 'extra', 'extra', 'extra']
EXTRA_PATH_METADATA = {
    'extra/CNAME': {'path': 'CNAME'},
    'extra/manifest.json': {'path': 'manifest.json'},
    'extra/browserconfig.xml': {'path': 'browserconfig.xml'},
    'extra/google0bdb78453461e14d.html': {'path': 'google0bdb78453461e14d.html'}
}

SITEMAP = {
    "format": "xml",
    "priorities": {
        "articles": 0.5,
        "indexes": 0.5,
        "pages": 0.5
    },
    "changefreqs": {
        "articles": "monthly",
        "indexes": "daily",
        "pages": "monthly"
    }
}

