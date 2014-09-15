#!/usr/bin/python
# -*- coding: utf-8 -*-
# MIT License
# Copyright (C) 2013-2014 sitic

import pywikibot
import mwparserfromhell as mwparser
import re
import dateutil.parser as dateparser
import datetime
import locale
import redis

discPageTitle = u'Wikipedia Diskussion:Hauptseite/Artikel des Tages/Vorschläge'
erledigtTemplate = (u'{{Erledigt|1=&nbsp;Gestriger AdT-Abschnitt, Baustein'
                    u' wurde [[WP:Bot|automatisch]] gesetzt. ~~~~}}\n\n')
erledigtComment = u'Bot: /* {section} */{andere} als erledigt markiert'

re_adt1 = re.compile(r'\[\[(?P<adt>[^\|\]]*)\|?[^\]]*?\]\]')
re_adt2 = re.compile(r'\:\s*(?P<adt>[^\[\|\]]*?)\s*==\n')

redisServer = 'tools-redis'
redisPort = 6379
redisDB = 9

rand_str = 'bceL8omhRhUIkx4KhGWPC6TLmq5IixQD7o5BId3x'  # openssl rand -base64 30


class AdtMain():
    def __init__(self):
        self.site = pywikibot.Site()
        self.site.login()

        self.red = redis.StrictRedis(host=redisServer, port=redisPort,
                                     db=redisDB)

        locale.setlocale(locale.LC_ALL, 'de_DE.utf8')
        self.today = datetime.date.today()
        self.dayName = self.today.strftime('%A').decode('utf-8')
        self.monthName = self.today.strftime('%B').decode('utf-8')
        self.year = self.today.year

        # 31.12.2013
        self.adtDate = self.today.strftime('%d.%m.%Y').decode('utf-8')

        # 31. Dezember 2013
        self.snapDate = self.today.strftime('%d. %B %Y').decode('utf-8')
        pywikibot.output(u'\n\ninit complete: ' +
                         datetime.datetime.now()
                         .strftime('%d. %B %Y, %H:%M:%S').decode('utf-8'))

        self.adt_disc()

    def adt_disc(self):  # NOQA
        discPage = pywikibot.Page(self.site, discPageTitle)
        section_count = 0
        line_count = -1
        header_line = None
        modsections = []

        line_list = discPage.text.splitlines(True)
        for text_line in line_list:
            line_count += 1
            s = re.match(r'==\s*(?P<sectionname>[^=]+?)\s*==\n', text_line)
            if s:  # found section
                # check previous section for AdT and erle
                if header_line is not None:
                    lines = line_list[header_line:line_count]
                    adt = self.__find_adt(lines)
                    if adt is not None:
                        self.addto_redis(adt['title'])
                    if not self.__erle_exists(lines):
                        line_list[line_count-1] += erledigtTemplate
                        modsections.append(sectionname) # NOQA

                section_count += 1
                sectionname = s.group('sectionname')

                pywikibot.output(u'WD:AdT: Abschnitt gefunden: ' + sectionname)
                d = re.search(r'\d{1,2}\.\d{1,2}\.\d{2,4}\s?:', sectionname)
                if d:
                        date = dateparser.parse(d.group()[:-1], dayfirst=True)
                        if date.date() <= self.today and section_count < 6:
                                header_line = line_count
                        else:
                            break

        pywikibot.output(u'WD:AdT: Abschnitt(e) ' + unicode(modsections) +
                         u' als erledigt markiert')
        if len(modsections) == 1:
            code = mwparser.parse(modsections[0])
            lead_section = code.strip_code(normalize=True, collapse=True)
            comment = erledigtComment.format(section=lead_section, andere=u'')
        elif len(modsections) > 1:
            andere = u' sowie'
            for i in range(1, len(modsections)):
                code = mwparser.parse(modsections[i])
                section = code.strip_code(normalize=True, collapse=True)
                if i > 1:
                    andere += u','
                andere += u' [[#' + unicode(section) + ']]'

            code = mwparser.parse(modsections[0])
            lead_section = code.strip_code(normalize=True, collapse=True)
            comment = erledigtComment.format(section=lead_section,
                                             andere=andere)

        if len(modsections) != 0:
            discPage.text = u''.join(line_list)
            discPage.save(comment=comment, botflag=True, minor=True)

    def __find_adt(self, lines):
        code = mwparser.parse(lines)

        for template in code.filter_templates():
            if template.name.matches((u'AdT-Vorschlag', u'AdT-Vorschlag\n')):
                l = re.search(r'\s*(?P<adt>.*)\s*\n?',
                              unicode(template.get(u'LEMMA').value))
                d = re.search(r'\d{1,2}\.\d{1,2}\.\d{2,4}',
                              unicode(template.get(u'DATUM').value))
                if d:
                    date = dateparser.parse(d.group(), dayfirst=True).date()
                if l:
                    adtTitle = l.group('adt').strip()
                    pywikibot.output(u'Heutiger AdT: ' + self.adtTitle)
                else:
                    pywikibot.error(u'Konnte AdT nicht finden in Abschnitt: ' +
                                    lines)
                    adtTitle = None
                    return dict(title=adtTitle, date=date)

    def __erle_exists(self, line_list):
        code = mwparser.parse(u''.join(line_list))
        for template in code.filter_templates(recursive=False):
            if template.name.matches("Erledigt"):
                return True
        return False

    def addto_redis(self, title):
        self.red.sadd(rand_str, title)
        pywikibot.output(u"Added " + title + u" to redis set " +
                         rand_str.decode('utf8') + u'\n')

if __name__ == "__main__":
    try:
        AdtMain()
    finally:
        pywikibot.stopme()
