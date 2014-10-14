#!/usr/bin/python
# -*- coding: utf-8 -*-
# MIT License
# Copyright (C) 2013-2014 sitic

import pywikibot
import mwparserfromhell as mwparser
import re
import dateutil.parser as dateparser
import dateutil.relativedelta as datedelta
import datetime
import locale
import redis
import sys
from Bali import AdtMain

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


class AdT_Verwaltung():
    def __init__(self, do_hinweis):
        self.dry = False  # debug switch
        self.do_hinweis = do_hinweis

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
        self.snapDate = self.__format_date(self.today)

        self.props = []
        self.erl_props = []
        self.dates = []
        self.sections = []

        pywikibot.output(u'\n\ninit complete: ' +
                         datetime.datetime.now()
                         .strftime('%d. %B %Y, %H:%M:%S').decode('utf-8'))

        main_adt = AdtMain()
        try:
            main_adt.add_template()
        except Exception as inst:
            pywikibot.error(u'ERROR: ' + str(type(inst)))
            pywikibot.error(inst)

        try:
            self.adt_disc()
        except Exception as inst:
            pywikibot.error(u'ERROR: ' + str(type(inst)))
            pywikibot.error(inst)

        try:
            if self.do_hinweis:
                self.add_templates()
            else:
                self.cleanup_templates()
        except Exception as inst:
            pywikibot.error(u'ERROR: ' + str(type(inst)))
            pywikibot.error(inst)

    def adt_disc(self):  # NOQA
        discPage = pywikibot.Page(self.site, discPageTitle)
        section_count = 0
        line_count = -1
        header_line = None
        sectionname = None
        modsections = []
        date = self.today + datedelta.relativedelta(years=1000)

        line_list = discPage.text.splitlines(True)
        for text_line in line_list:
            line_count += 1
            s = re.match(r'==\s*(?P<sectionname>[^=]+?)\s*==\n', text_line)
            if s:  # found section
                # check previous section for AdT and erle
                if header_line is not None:
                    lines = line_list[header_line:line_count]
                    # adt = self.__find_adt(lines)
                    if date.date() <= self.today and section_count < 6:
                        try:
                            self.__cleanup(lines, sectionname, date)
                        except Exception as inst:
                            pywikibot.error(u'ERROR: ' + str(type(inst)))
                            pywikibot.error(inst)

                        if not self.__erle_exists(lines):
                            line_list[line_count-1] += erledigtTemplate
                            modsections.append(sectionname)
                    else:
                        self.check_template(lines, sectionname, date)

                section_count += 1
                sectionname = s.group('sectionname')
                code = mwparser.parse(sectionname)
                sectionname = code.strip_code(normalize=True, collapse=True)
                header_line = line_count

                d = re.search(r'\d{1,2}\.\d{1,2}\.\d{2,4}\s?:', sectionname)
                if d:
                    date = dateparser.parse(d.group()[:-1], dayfirst=True)
                else:
                    date = self.today + datedelta.relativedelta(years=1000)

        if self.do_hinweis:
            # don't do erle
            return

        pywikibot.output(u'WD:AdT: Abschnitt(e) ' + unicode(modsections) +
                         u' als erledigt markiert')
        if len(modsections) == 1:
            lead_section = modsections[0]
            comment = erledigtComment.format(section=lead_section, andere=u'')
        elif len(modsections) > 1:
            andere = u' sowie'
            for i in range(1, len(modsections)):
                section = modsections[i]
                if i > 1:
                    andere += u','
                andere += u' [[#' + unicode(section) + ']]'

            lead_section = modsections[0]
            comment = erledigtComment.format(section=lead_section,
                                             andere=andere)

        if len(modsections) != 0:
            discPage.text = u''.join(line_list)
            if not self.dry:
                discPage.save(comment=comment, botflag=True, minor=True)

    def __find_adt(self, line_list):
        lines = u''.join(line_list)
        code = mwparser.parse(lines)

        for template in code.filter_templates(recursive=False):
            if template.name.matches((u'AdT-Vorschlag', u'AdT-Vorschlag\n')):
                l = re.search(r'\s*(?P<adt>.*)\s*\n?',
                              unicode(template.get(u'LEMMA').value))
                d = re.search(r'\d{1,2}\.\d{1,2}\.\d{2,4}',
                              unicode(template.get(u'DATUM').value))
                date = None
                adtTitle = None
                if d:
                    date = dateparser.parse(d.group(), dayfirst=True).date()  #NOQA
                if l:
                    adtTitle = l.group('adt').strip()
                    pywikibot.output(u'AdT Vorschlag: ' + adtTitle)
                else:
                    pywikibot.error(u'Konnte AdT nicht finden in Abschnitt: ' +
                                    lines)
                return adtTitle

    def __erle_exists(self, line_list):
        code = mwparser.parse(u''.join(line_list))
        for template in code.filter_templates(recursive=False):
            if template.name.matches("Erledigt"):
                return True
        return False

    def __cleanup(self, lines, sectionname, date):
        adt = self.__find_adt(lines)
        if adt is not None:
            self.erl_props.append(adt)

    def check_template(self, lines, sectionname, date):
        if date == self.today + datedelta.relativedelta(years=1000):
            date = None
        adt = self.__find_adt(lines)

        if adt is not None:
            self.dates.append(date)
            self.props.append(adt)
            self.sections.append(sectionname)

    def cleanup_templates(self):
        for adt in self.erl_props:
            if adt in self.props:
                # mehrmals für AdT vorgeschlagen
                continue

            page = pywikibot.Page(self.site, adt, ns=1)

            if not page.exists():
                pywikibot.error(u'ERROR: disc for AdT-Vorschlag ' + adt
                                + u' does not exist!')
                return

            oldtext = page.text
            code = mwparser.parse(page.text)

            for template in code.filter_templates(recursive=False):
                if template.name.matches("AdT-Vorschlag Hinweis"):
                    code.remove(template)
                    pywikibot.output(adt +
                                     u': {{AdT-Vorschlag Hinweis}} '
                                     u'gefunden, entfernt')
            page.text = unicode(code)
            if page.text == oldtext:
                continue

            page.text = page.text.lstrip(u'\n')
            pywikibot.showDiff(oldtext, page.text)
            comment = u'Bot: [[Vorlage:AdT-Vorschlag Hinweis]] entfernt'
            if not self.dry:
                page.save(comment=comment, botflag=True, minor=True)

    def add_templates(self):  # NOQA
        for adt, section, date in zip(self.props, self.sections, self.dates):
            page = pywikibot.Page(self.site, adt, ns=1)
            if not page.exists():
                pywikibot.error(u'ERROR: disc for AdT-Vorschlag ' + adt
                                + u' does not exist!')
                return

            oldtext = page.text
            code = mwparser.parse(page.text)

            found = False
            for template in code.filter_templates(recursive=False):
                if template.name.matches("AdT-Vorschlag Hinweis"):
                    found = True
                    if not template.has(u'Abschnitt'):
                        template.add(u'Abschnitt', section)
                    if template.has(u'Datum'):
                        tdate = self.__date_parser(template.get(u'Datum').value)
                        if dateparser.parse(tdate, dayfirst=True) <= date:
                            continue
                        else:
                            template.get(u'Datum').value = self.__format_date(
                                date)
                            template.get(u'Abschnitt').value = section

            page.text = unicode(code)
            if not found:
                page.text = (u'{{AdT-Vorschlag Hinweis' +
                             self.__format_tempdate(date) +
                             u' | Abschnitt = ' + section + u'}}\n' +
                             page.text)

            if page.text == oldtext:
                continue

            comment = (u'Bot: Dieser Artikel wurde für den ' +
                       self.__format_date(date) +
                       u' zum Artikel des Tages vorgeschlagen ([[WD:AdT#' +
                       section + u'|Diskussion]])')
            pywikibot.showDiff(oldtext, page.text)
            if not self.dry:
                page.save(comment=comment, botflag=False, minor=False)

    def __format_date(self, date):
        return date.strftime('%-d. %B %Y').decode('utf-8')

    def __format_tempdate(self, date):
        if date is not None:
            return u'| Datum = ' + self.__format_date(date)
        else:
            return u''

    def __date_parser(self, date):
        date = unicode(date)
        dictionary = {
            u'Januar': 'January',
            u'Februar': 'February',
            u'März': 'March',
            u'Mai': 'May',
            u'Juni': 'June',
            u'Juli': 'July',
            u'Oktober': 'October',
            u'Dezember': 'December'
            }

        for lang, en in dictionary.items():
            date = date.replace(lang, en)
        return date

if __name__ == "__main__":
    try:
        if len(sys.argv) < 2:
            AdT_Verwaltung(False)
        else:
            AdT_Verwaltung(True)
    finally:
        pywikibot.stopme()
