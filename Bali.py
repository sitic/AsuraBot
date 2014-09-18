#!/usr/bin/python
# -*- coding: utf-8 -*-
# MIT License
# Copyright (C) 2013-2014 sitic

import pywikibot
import mwparserfromhell
import re
import dateutil.parser as dateparser
import dateutil.relativedelta as datedelta
import datetime
import locale
import redis

redisServer = 'tools-redis'
redisPort = 6379
redisDB = 9

# openssl rand -base64 30
redSetMain = 'bceL8omhRhUIkx4KhGWPC6TLmq5IixQD7o5BId3x'

adtPageTitle = u'Wikipedia:Hauptseite/Artikel des Tages/{dayName}'
chronPageTitle = u'Wikipedia:Hauptseite/Artikel des Tages/Chronologie {year}'
editComment = u'Bot: heutiger AdT: [[{adt}]]{erneut}'
templateComment = u'Bot: dieser Artikel ist heute Artikel des Tages'
verwaltungTitle1 = u'Wikipedia:Hauptseite/Artikel des Tages/Verwaltung'
verwaltungTitle2 = u'Wikipedia:Hauptseite/Artikel des Tages/Verwaltung/Lesenswerte Artikel' # NOQA

talkPageHeading = u'\n\n== Fehler beim automatischen Eintragen des heutigen Adt ({date}) ==\n' # NOQA
talkPageErrorMsgDay = talkPageHeading + (u'<small>Dies ist '
        u'eine automatisch erstellte Fehlermeldung eines [[WP:Bots|Bots]].</small>\n\nDer Eintrag:\n*' # NOQA
        u'{line}\nenthält das aktuelle Tagesdatum, obwohl der heutige AdT [[{adt}]] ist. Der Fehler wurde ' # NOQA
        u'\'\'nicht\'\' berichtigt, bitte überprüfen. --~~~~')
talkPageErrorMsgTime = talkPageHeading + (u'<small>Dies ist '
        u'eine automatisch erstellte Fehlermeldung eines [[WP:Bots|Bots]].</small>\n\nDer Eintrag:\n*' # NOQA
        u'{line}\ndes heutigen AdT enthält ein Datum, das nicht das heutige ist, aber höchstens zwei Jahre ' # NOQA
        u'zurückliegt. Der Fehler wurde \'\'nicht\'\' berichtigt, bitte überprüfen (auch die Chronologie). --~~~~') # NOQA
talkPageErrorNotFound = talkPageHeading + (u'<small>Dies ist '
        u'eine automatisch erstellte Fehlermeldung eines [[WP:Bots|Bots]].</small>\n\nIch konnte den heutigen AdT ' # NOQA
        u'[[{adt}]] weder in der [[Wikipedia:Hauptseite/Artikel des Tages/Verwaltung|Verwaltung]] noch in ' # NOQA
        u'[[Wikipedia:Hauptseite/Artikel des Tages/Verwaltung/Lesenswerte Artikel|Verwaltung Lesenswerte]] finden. ' # NOQA
        u'Bitte überprüfen und ggf. berichtigen. --~~~~')
talkPageErrorComment = (u'neu /* Fehler beim automatischen Eintragen des '
                        u'heutigen Adt ({date}) */, manuelle Berichtigung '
                        u'notwendig')


class AdtMain():
    def __init__(self):
        self.dry = False  # debug
        self.site = pywikibot.Site()
        self.site.login()

        self.red = redis.StrictRedis(host=redisServer, port=redisPort,
                                     db=redisDB)

        locale.setlocale(locale.LC_ALL, 'de_DE.utf8')
        self.today = datetime.date.today()
        self.dayName = self.today.strftime('%A').decode('utf-8')
        self.monthName = self.today.strftime('%B').decode('utf-8')
        self.year = self.today.year

        # 1.12.2013
        self.adtDate = self.today.strftime('%d.%m.%Y').decode('utf-8')

        # 1. Dezember 2013
        self.snapDate = self.today.strftime('%-d. %B %Y').decode('utf-8')

        self.adtErneut = None
        self.adtTitle = None

        self.get_adt()

    def run(self):
        pywikibot.output(u'\n\ninit complete: ' +
                         (datetime.datetime.now()
                          .strftime('%d. %B %Y, %H:%M:%S')).decode('utf-8'))

        if self.adtTitle is not None:
            try:
                self.addto_verwaltung()
            except Exception as inst:
                pywikibot.output(u'ERROR: ' + str(type(inst)))
                pywikibot.output(inst)
            try:
                self.addto_chron()
            except Exception as inst:
                pywikibot.output(u'ERROR: ' + str(type(inst)))
                pywikibot.output(inst)
            try:
                self.add_template()
            except Exception as inst:
                pywikibot.output(u'ERROR: ' + str(type(inst)))
                pywikibot.output(inst)
            # self.cleanup_templates()

    def get_adt(self):
        title = adtPageTitle.format(dayName=self.dayName)
        adtPage = pywikibot.Page(self.site, title)
        code = mwparserfromhell.parse(adtPage.text)

        for template in code.filter_templates():
            if template.name.matches((u'AdT-Vorschlag', u'AdT-Vorschlag\n')):
                l = re.search(r'\s*(?P<adt>.*)\s*\n?',
                              unicode(template.get(u'LEMMA').value))
                d = re.search(r'\d{1,2}\.\d{1,2}\.\d{2,4}',
                              unicode(template.get(u'DATUM').value))
                if l and dateparser.parse(d.group(),
                                          dayfirst=True).date() == self.today:
                    self.adtTitle = l.group('adt').strip()
                    pywikibot.output(u'Heutiger AdT: ' + self.adtTitle)
                else:
                    pywikibot.error(u'Konnte heutigen AdT nicht finden!')
                    self.adtTitle = None
                return

    def addto_verwaltung(self):
        found = self.__verwaltung(verwaltungTitle1)
        if not found:
            found = self.__verwaltung(verwaltungTitle2)
        if not found:
            pywikibot.warning(u'Verwaltung: AdT nicht gefunden!')
            page = pywikibot.Page(self.site, verwaltungTitle1)
            talkpage = page.toggleTalkPage()
            pywikibot.output(talkPageErrorNotFound.format(date=self.adtDate,
                                                          adt=self.adtTitle))
            if talkPageHeading.format(date=self.adtDate) in talkpage.text:
                return

            talkpage.text += talkPageErrorNotFound.format(date=self.adtDate,
                                                          adt=self.adtTitle)
            comment = talkPageErrorComment.format(date=self.adtDate)
            if not self.dry:
                talkpage.save(comment=comment, botflag=False, minor=False)

    def __verwaltung(self, pageTitle):  # NOQA
        page = pywikibot.Page(self.site, pageTitle)
        oldtext = page.text  # debug
        line_list = page.text.splitlines()
        found = False

        line_count = -1
        for text_line in line_list:
            line_count += 1
            adt = re.search(r'\[\[(?P<adt>[^\|\]]*)\|?[^\]]*?\]\]', text_line)
            if adt and adt.group('adt') == self.adtTitle:
                text_line = text_line.replace(u'\'\'\'', u'')
                text_line = text_line.replace(u'\'\'', u'')

                r = re.findall(r'\d{1,2}\.\d{1,2}\.\d{2,4}', text_line)
                if r:
                    self.adtErneut = True
                    for r_date in r:
                        date = dateparser.parse(r_date, dayfirst=True).date()
                        if date == self.today:
                            if len(r) == 1:
                                self.adtErneut = False
                            found = True
                            pywikibot.output(u'Verwaltung: AdT Datum war schon'
                                             u' in ' + pageTitle +
                                             u' eingetragen')
                            break
                        elif date + datedelta.relativedelta(years=2) > self.today:  # NOQA
                            talkpage = page.toggleTalkPage()
                            pywikibot.output(talkPageErrorMsgTime
                                             .format(date=self.adtDate,
                                                     line=text_line,
                                                     adt=self.adtTitle))
                            if not talkPageHeading.format(date=self.adtDate) in talkpage.text: # NOQA
                                talkpage.text += talkPageErrorMsgTime.format(
                                    date=self.adtDate, line=text_line)
                                comment = talkPageErrorComment.format(
                                    date=self.adtDate)
                                if not self.dry:
                                    talkpage.save(comment=comment,
                                                  botflag=False,
                                                  minor=False)
                    if not found:
                        text_line = text_line.rsplit('</small>', 1)[0]
                        text_line += u' + ' + self.adtDate + u'</small> -'
                else:
                    self.adtErneut = False
                    text_line = text_line.rsplit(u']]', 1)[0] + u']] <small>' +\
                        self.adtDate + u'</small> -'

                line_list[line_count] = text_line
            elif self.adtDate.strip() in text_line.strip():
                talkpage = page.toggleTalkPage()
                pywikibot.output(talkPageErrorMsgDay.format(date=self.adtDate,
                                                            line=text_line,
                                                            adt=self.adtTitle))
                if not talkPageHeading.format(date=self.adtDate) in talkpage.text: # NOQA
                    talkpage.text += talkPageErrorMsgDay.format(
                        date=self.adtDate, line=text_line, adt=self.adtTitle)
                    comment = talkPageErrorComment.format(date=self.adtDate)
                    if not self.dry:
                        talkpage.save(comment=comment, botflag=False,
                                      minor=False)

        if page.text != u'\n'.join(line_list):
            page.text = u'\n'.join(line_list)
            if self.adtErneut:
                comment = editComment.format(adt=self.adtTitle,
                                             erneut=u' (erneut)')
            else:
                comment = editComment.format(adt=self.adtTitle,
                                             erneut=u'')
            pywikibot.showDiff(oldtext, page.text)  # debug
            if not self.dry:
                page.save(comment=comment, botflag=False, minor=True)
            return True
        elif found:
            return True
        else:
            pywikibot.output(u'Verwaltung: AdT nicht in ' +
                             pageTitle + u' gefunden.')
            return False

    def addto_chron(self):
        title = chronPageTitle.format(year=self.year)
        chronPage = pywikibot.Page(self.site, title)
        oldtext = chronPage.text  # debug

        d = re.search(self.adtDate, chronPage.text)
        if d:
            pywikibot.output(u'Chronologie: AdT wurde schon eingetragen.')
            return

        r = re.search(r'\n===\s*' + self.monthName + r'\s*' +
                      unicode(self.year) + r'\s*===\n', chronPage.text)
        if not r:  # neuer Monatsabschnitt erstellen?
            pywikibot.output(u'Chronologie: erstelle neuen Monatsabschnitt')
            part = chronPage.text.split(u'===', 1)
            part[0] += u'=== ' + self.monthName + u' ' +\
                unicode(self.year) + u' '
            part[1] = u'\n===' + part[1]
        else:
            part = chronPage.text.split(u'===\n', 1)

        text = part[0] + u'===\n* ' + self.adtDate +\
            u' [[' + self.adtTitle + u']]'
        if self.adtErneut:
            text += u' (erneut)'
            comment = editComment.format(adt=self.adtTitle, erneut=u' (erneut)')
        elif self.adtErneut is None:
            pywikibot.warning(u'Konnte nicht feststellen, ob der AdT schonmal'
                              u' AdT war!')
        else:
            comment = editComment.format(adt=self.adtTitle, erneut=u'')

        text += u'\n' + part[1]

        chronPage.text = text
        pywikibot.showDiff(oldtext, text)  # debug
        if not self.dry:
            chronPage.save(comment=comment, botflag=False, minor=False)

    def add_template(self):
        if self.adtTitle:
            return  # silently fail

        adtPage = pywikibot.Page(self.site, self.adtTitle, ns=1)
        code = mwparserfromhell.parse(adtPage.text)

        war_adt_added = False
        for template in code.filter_templates(recursive=False):
            if template.name.matches("AdT-Vorschlag Hinweis"):
                code.remove(template)
                pywikibot.output(u'D:AdT: {{AdT-Vorschlag Hinweis}} gefunden,'
                                 u'entfernt')
            if template.name.matches("war AdT"):
                pywikibot.output(u'D:AdT: {{AdT-Vorschlag Hinweis}} gefunden,'
                                 u' füge heute hinzu')
                if self.snapDate not in template.params:
                    template.add(str(len(template.params)+1), self.snapDate)
                war_adt_added = True
        text = unicode(code)
        if not war_adt_added:
            template = u'{{war AdT|1=' + self.snapDate + u'}}\n'
            text = template + text

        print text  # debug

        if adtPage.text != text:
            pass
        # adtPage.save(comment=templateComment, botflag=True, minor=True)

    def cleanup_templates(self):
        pywikibot.output(u'\nÜberpürfe redis set ' + unicode(redSetMain))
        while True:
            title = self.red.spop(redSetMain)
            if title is None:
                break

            page = pywikibot.Page(self.site, title, ns=1)
            code = mwparserfromhell.parse(page.text)
            for template in code.filter_templates(recursive=False):
                if template.name.matches("AdT-Vorschlag Hinweis"):
                    param_tag = template.get(u'Tag').value
                    date = dateparser.parse(param_tag, dayfirst=True).date()
                    if date <= self.today:
                        code.remove(template)
                        pywikibot.output(title + u': {{AdT-Vorschlag Hinweis}}'
                                         u' gefunden, entfernt.')
                    else:
                        pywikibot.output(title + u': {{AdT-Vorschlag Hinweis}}'
                                         u' gefunden, belassen da für ' +
                                         unicode(date))

            if unicode(code) != page.text:
                pass  # page.save()

if __name__ == "__main__":
    try:
        runner = AdtMain()
        runner.run()
    finally:
        pywikibot.stopme()
