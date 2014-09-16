#!/usr/bin/python
# -*- coding: utf-8 -*-
# MIT License
# Copyright (C) 2014 sitic

import pywikibot
import re
import mwparserfromhell as mwparser
import datetime

PurgePage = u'Benutzer:AsuraBot/Purges'

rePurge = re.compile(r"""<!-- AsuraBot purge Liste Start -->
(.*?)<!-- AsuraBot purge Liste Ende -->""", re.DOTALL)

reLink = re.compile(r"""<!-- AsuraBot forcelinkupdate Liste Start -->
(.*?)<!-- AsuraBot forcelinkupdate Liste Ende -->""", re.DOTALL)

reRec = re.compile(r"""<!-- AsuraBot forcerecursivelinkupdate Liste Start -->
(.*?)<!-- AsuraBot forcerecursivelinkupdate Liste Ende -->""", re.DOTALL)

ListRegex = [rePurge, reLink, reRec]
ListOptions = [None,
               {'forcelinkupdate': 'true'},
               {'forcerecursivelinkupdate': 'true'}]


class Purger():
    def __init__(self):
        self.site = pywikibot.Site()
        self.site.login()

        pywikibot.output(u'\n\ninit complete: ' +
                         (datetime.datetime.now()
                          .strftime('%d. %B %Y, %H:%M:%S')).decode('utf-8'))

        page = pywikibot.Page(self.site, PurgePage)
        if not page.exists():
            pywikibot.output(u'\nERROR: page not found')
            raise pywikibot.NoSuchSite
        for regex, option in zip(ListRegex, ListOptions):
            self.parse(regex, page.expand_text(includecomments=True), option)

    def parse(self, regex, text, option):
        result = regex.search(text)
        if result:
            code = mwparser.parse(result.group())
            links = []
            for i in code.filter_wikilinks():
                links.append(i.title)
            if option is None:
                pywikibot.output('\npurging: ' + str(links))
            else:
                pywikibot.output('\n' + option.keys()[0] + u': ' + str(links))
            if links:
                self.purge(links, option)

    def purge(self, pagetitles, option):
        pages = []
        for t in pagetitles:
            pages.append(pywikibot.Page(self.site, t))
        if option is None:
            self.site.purgepages(pages)
        else:
            self.site.purgepages(pages, **option)

if __name__ == "__main__":
    try:
        Purger()
    finally:
        pywikibot.stopme()
