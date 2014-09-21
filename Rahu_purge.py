#!/usr/bin/env python
# -*- coding: utf-8 -*-
# MIT License
# Copyright (C) 2014 sitic

import pywikibot
import time

sandboxTitle = u'Wikipedia:Spielwiese'
timeformat = '%d. %B %Y, %H:%M:%S: '

class Purger:
  def __init__(self):
    self.site = pywikibot.Site()
    self.site.login()
    self.sandboxPage = pywikibot.Page(self.site, sandboxTitle)
    self.sandboxPage.purge()

if __name__ == "__main__":
  try:
    Purger()
  except KeyboardInterrupt:
    pywikibot.output("u\n\n\03{lightred}Shutting down ...\03{default}")
    pywikibot.stopme()
