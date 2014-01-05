#!/usr/bin/python
# -*- coding: utf-8 -*-
# MIT License
# Copyright (C) 2013-2014 sitic

import pywikibot
import mwparserfromhell
import re
import dateutil.parser
import datetime
import locale
import redis

discPageTitle = u'Wikipedia Diskussion:Hauptseite/Artikel des Tages/Vorschläge'
erledigtTemplate = u'{{Erledigt|1=&nbsp;Gestriger AdT-Abschnitt, Baustein wurde [[WP:Bot|automatisch]] gesetzt. ~~~~}}\n\n'
erledigtComment = u'Bot: /* {section} */{andere} als erledigt markiert'

redisServer = 'tools-redis'
redisPort = 6379
redisDB = 9

rand_str = 'bceL8omhRhUIkx4KhGWPC6TLmq5IixQD7o5BId3x' #openssl rand -base64 30

class AdtMain():
    def __init__(self):
        self.site = pywikibot.Site()
        self.site.login()

        self.red = redis.StrictRedis(host=redisServer, port=redisPort, db=redisDB)

        locale.setlocale(locale.LC_ALL, 'de_DE.utf8')
        self.today = datetime.date.today()
        self.dayName = self.today.strftime('%A')
        self.monthName = self.today.strftime('%B')
        self.year = self.today.year
        self.adtDate = self.today.strftime('%d.%m.%Y') #31.12.2013
        self.snapDate = self.today.strftime('%d. %B %Y') #31. Dezember 2013
        pywikibot.output(u'\n\ninit complete: ' +\
                        datetime.datetime.now().strftime('%d. %B %Y, %H:%M:%S'))

        self.adt_disc()

    def adt_disc(self):
        discPage = pywikibot.Page(self.site, discPageTitle)
        section_count = 0
        line_count = -1
        header_line = None
        modsections = []

        line_list = discPage.text.splitlines(True)
        for text_line in line_list:
            line_count += 1
            s = re.match(r'==\s*(?P<sectionname>[^=]+?)\s*==\n', text_line)
            if s: #found section
                #check previous section for erle
                if header_line != None:
                    if not self.__erle_exists(line_list[header_line:line_count]):
                        line_list[line_count-1] += erledigtTemplate
                        modsections.append(sectionname)

                section_count += 1
                sectionname = s.group('sectionname')
                pywikibot.output(u'WD:AdT: Abschnitt gefunden: ' + sectionname)
                d = re.search(r'\d{1,2}\.\d{1,2}\.\d{2,4}\s?:', sectionname)
                if d:
                        date = dateutil.parser.parse(d.group()[:-1], dayfirst=True)
                        if date.date() <= self.today:
                                header_line = line_count
                                adt = re.search(r'\[\[(?P<adt>[^\|\]]*)\|?[^\]]*?\]\]', text_line)
                                if not adt:
                                    pywikibot.error(u'Abschnitt archiviert, konnte aber'
                                            u' nicht den AdT ermitteln!')
                                self.addto_redis(adt.group('adt'))
                if section_count > 4:
                        break

        pywikibot.output(u'WD:AdT: Abschnitt(e) ' + unicode(modsections) +\
                u' als erledigt markiert')
        if len(modsections) == 1:
            code = mwparserfromhell.parse(modsections[0])
            lead_section = code.strip_code(normalize=True, collapse=True)
            comment = erledigtComment.format(section=lead_section,
                    andere=u'')
        elif len(modsections) > 1:
            andere = u' sowie'
            for i in range(1,len(modsections)):
                code = mwparserfromhell.parse(modsections[i])
                section = code.strip_code(normalize=True, collapse=True)
                if i > 1:
                    andere += u','
                andere += u' [[#' + unicode(section) + ']]'

            code = mwparserfromhell.parse(modsections[0])
            lead_section = code.strip_code(normalize=True, collapse=True)
            comment = erledigtComment.format(section=lead_section,
                    andere=andere)

        if len(modsections) != 0:
            discPage.text = u''.join(line_list)
            discPage.save(comment=comment, botflag=False, minor=True)
    def __erle_exists(self, line_list):
        code = mwparserfromhell.parse(u''.join(line_list))
        for template in code.filter_templates(recursive=False):
            if template.name.matches("Erledigt"):
                return True
        return False

    def addto_redis(self, title):
        self.red.sadd(rand_str, title)
        pywikibot.output(u"Added " + title + u" to redis set " +\
                        rand_str.decode('utf8') + u'\n')

if __name__ == "__main__":
    try:
        AdtMain()
    finally:
        pywikibot.stopme()
