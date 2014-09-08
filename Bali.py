#!/usr/bin/python
# -*- coding: utf-8 -*-
# MIT License
# Copyright (C) 2013-2014 sitic

import pywikibot
import mwparserfromhell
import re
import dateutil.parser
from dateutil.relativedelta import *
import datetime
import locale
import redis

redisServer = 'tools-redis'
redisPort = 6379
redisDB = 9

redSetMain = 'bceL8omhRhUIkx4KhGWPC6TLmq5IixQD7o5BId3x' #openssl rand -base64 30

adtPageTitle = u'Wikipedia:Hauptseite/Artikel des Tages/{dayName}'
chronPageTitle = u'Wikipedia:Hauptseite/Artikel des Tages/Chronologie {year}'
editComment = u'Bot: heutiger AdT: [[{adt}]]{erneut}'
templateComment = u'Bot: dieser Artikel ist heute Artikel des Tages'
verwaltungTitle1 = u'Wikipedia:Hauptseite/Artikel des Tages/Verwaltung'
verwaltungTitle2 = u'Wikipedia:Hauptseite/Artikel des Tages/Verwaltung/Lesenswerte Artikel'

talkPageHeading = u'\n\n== Fehler beim automatischen Eintragen des heutigen Adt ({date}) ==\n'
talkPageErrorMsgDay = talkPageHeading + (u'<small>Dies ist '
        u'eine automatisch erstellte Fehlermeldung eines [[WP:Bots|Bots]].</small>\n\nDer Eintrag:\n*'
        u'{line}\nenthält das aktuelle Tagesdatum, obwohl der heutige AdT [[{adt}]] ist. Der Fehler wurde '
        u'\'\'nicht\'\' berichtigt, bitte überprüfen. --~~~~')
talkPageErrorMsgTime = talkPageHeading + (u'<small>Dies ist '
        u'eine automatisch erstellte Fehlermeldung eines [[WP:Bots|Bots]].</small>\n\nDer Eintrag:\n*'
        u'{line}\ndes heutigen AdT enthält ein Datum, das nicht das heutige ist, aber höchstens zwei Jahre '
        u'zurückliegt. Der Fehler wurde \'\'nicht\'\' berichtigt, bitte überprüfen (auch die Chronologie). --~~~~')
talkPageErrorNotFound = talkPageHeading + (u'<small>Dies ist '
        u'eine automatisch erstellte Fehlermeldung eines [[WP:Bots|Bots]].</small>\n\nIch konnte den heutigen AdT '
	u'[[{adt}]] weder in der [[Wikipedia:Hauptseite/Artikel des Tages/Verwaltung|Verwaltung]] noch in '
	u'[[Wikipedia:Hauptseite/Artikel des Tages/Verwaltung/Lesenswerte Artikel|Verwaltung Lesenswerte]] finden. '
	u'Bitte überprüfen und ggf. berichtigen. --~~~~')
talkPageErrorComment = (u'neu /* Fehler beim automatischen Eintragen des heutigen Adt ({date}) */, manuelle '
        u'Berichtigung notwendig')

class AdtMain():
    def __init__(self):
        self.site = pywikibot.Site()
        self.site.login()

        self.red = redis.StrictRedis(host=redisServer, port=redisPort, db=redisDB)

        locale.setlocale(locale.LC_ALL, 'de_DE.utf8')
        self.today = datetime.date.today()
        self.dayName = self.today.strftime('%A').decode('utf-8')
        self.monthName = self.today.strftime('%B').decode('utf-8')
        self.year = self.today.year
        self.adtDate = self.today.strftime('%d.%m.%Y').decode('utf-8') #31.12.2013
        self.snapDate = self.today.strftime('%d. %B %Y').decode('utf-8') #31. Dezember 2013
        pywikibot.output(u'\n\ninit complete: ' +\
                        (datetime.datetime.now().strftime('%d. %B %Y, %H:%M:%S')).decode('utf-8'))

        self.adtErneut = None
        self.adtTitle = None

        self.get_adt()
        if self.adtTitle != None:
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
            #self.add_template()
            #self.cleanup_templates()

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
                if l and dateutil.parser.parse(d.group(),
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
            pywikibot.output(talkPageErrorNotFound.format(date=self.adtDate, adt=self.adtTitle))
            if talkPageHeading.format(date=self.adtDate) in talkpage.text:
                return

            talkpage.text += talkPageErrorNotFound.format(date=self.adtDate, adt=self.adtTitle)
            comment = talkPageErrorComment.format(date=self.adtDate)
            talkpage.save(comment=comment, botflag=False, minor=False)
    def __verwaltung(self, pageTitle):
        page = pywikibot.Page(self.site, pageTitle)
        oldtext = page.text ##debug
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
                        date = dateutil.parser.parse(r_date, dayfirst=True).date()
                        if date == self.today:
                            if len(r) == 1:
                                self.adtErneut = False
                            found = True
                            pywikibot.output(u'Verwaltung: AdT Datum war schon eingetragen' + pageTitle +\
                                    u' eingetragen')
                            break
                        elif date + relativedelta(years=2) > self.today:
                            talkpage = page.toggleTalkPage()
                            pywikibot.output(talkPageErrorMsgTime.format(date=self.adtDate, line=text_line, adt=self.adtTitle))
                            if not talkPageHeading.format(date=self.adtDate) in talkpage.text:
                                talkpage.text += talkPageErrorMsgTime.format(date=self.adtDate, line=text_line)
                                comment = talkPageErrorComment.format(date=self.adtDate)
                                talkpage.save(comment=comment, botflag=False, minor=False)
                    if not found:
                        text_line = text_line.rsplit('</small>', 1)[0]
                        text_line += u' + ' + self.adtDate + u'</small> -'
                else:
                    self.adtErneut = False
                    text_line = text_line.rsplit(u']]', 1)[0] + u']] <small>' + self.adtDate +\
                            u'</small> -'

                line_list[line_count] = text_line
            elif self.adtDate.strip() in text_line.strip():
                talkpage = page.toggleTalkPage()
                pywikibot.output(talkPageErrorMsgDay.format(date=self.adtDate, line=text_line, adt=self.adtTitle))
                if not talkPageHeading.format(date=self.adtDate) in talkpage.text:
                    talkpage.text += talkPageErrorMsgDay.format(date=self.adtDate, line=text_line, adt=self.adtTitle)
                    comment = talkPageErrorComment.format(date=self.adtDate)
                    talkpage.save(comment=comment, botflag=False, minor=False)

        if page.text != u'\n'.join(line_list):
            page.text = u'\n'.join(line_list)
            if self.adtErneut:
                comment = editComment.format(adt=self.adtTitle,erneut=u' (erneut)')
            else:
                comment = editComment.format(adt=self.adtTitle,erneut=u'')
            pywikibot.showDiff(oldtext,page.text) ##debug
            page.save(comment=comment, botflag=False, minor=True)
            return True
        elif found:
            return True
        else:
            pywikibot.output(u'Verwaltung: AdT nicht in ' + pageTitle + u' gefunden.')
            return False

    def addto_chron(self):
        title = chronPageTitle.format(year=self.year)
        chronPage = pywikibot.Page(self.site, title)
        oldtext = chronPage.text ##debug

        d = re.search(self.adtDate, chronPage.text)
        if d:
            pywikibot.output(u'Chronologie: AdT wurde schon eingetragen.')
            return

        r = re.search(r'\n===\s*' + self.monthName + r'\s*' +\
                unicode(self.year) + r'\s*===\n', chronPage.text)
        if not r: #neuer Monatsabschnitt erstellen?
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
            comment = editComment.format(adt=self.adtTitle,erneut=u' (erneut)')
        elif self.adtErneut == None:
            pywiki.warning(u'Konnte nicht feststellen, ob der AdT schonmal'
                    u'AdT war!')
        else:
            comment = editComment.format(adt=self.adtTitle,erneut=u'')

        text += u'\n' + part[1]

        chronPage.text = text
        pywikibot.showDiff(oldtext,text) ##debug
        chronPage.save(comment=comment, botflag=False, minor=False)

    def add_template(self):
        adtPage = pywikibot.Page(self.site, self.adtTitle, ns=1)
        code = mwparserfromhell.parse(adtPage.text)

        war_adt_added = False
        for template in code.filter_templates(recursive=False):
            if template.name.matches("wird AdT"):
                code.remove(template)
                self.red.srem(redSetMain, self.adtTitle)
                pywikibot.output(u'D:AdT: {{wird AdT}} gefunden, entfernt')
            if template.name.matches("war AdT"):
                pywikibot.output(u'D:AdT: {{war AdT}} gefunden, füge heute hinzu')
                template.add(str(len(template.params)+1), self.adtDate)
                war_adt_added = True

        if not war_adt_added:
            template = u'{{war AdT|1=' + self.adtDate + u'}}\n'
            adtPage.text = template + adtPage.text

        print adtPage.text ##debug
        #adtPage.save(comment=templateComment, botflag=False, minor=False)

    def cleanup_templates(self):
        pywikibot.output(u'\nÜberpürfe redis set ' + unicode(redSetMain))
        while True:
            title = self.red.spop(redSetMain)
            if title is None:
                break

            page = pywikibot.Page(self.site, title, ns=1)
            code = mwparserfromhell.parse(page.text)
            for template in code.filter_templates(recursive=False):
                if template.name.matches("wird AdT"):
                    param_tag = template.get(u'Tag').value
                    date = dateutil.parser.parse(param_tag, dayfirst=True).date()
                    if date <= self.today:
                        code.remove(template)
                        pywikibot.output(title + u': {{wird AdT}} gefunden,'
                                u' entfernt')
                    else:
                        pywikibot.output(title + u': {{wird AdT}} gefunden,'
                                u' belassen da für ' + unicode(date))

            if unicode(code) != page.text:
		    pass #page.save()

if __name__ == "__main__":
    try:
        AdtMain()
    finally:
        pywikibot.stopme()
