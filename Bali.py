#!/usr/bin/python
# -*- coding: utf-8 -*-
# MIT License
# (C) sitic, 2013

import pywikibot
import mwparserfromhell
import re
import time
import locale

adtPageTitle = u'Wikipedia:Hauptseite/Artikel des Tages/{dayName}'
chronPageTitle = u'Wikipedia:Hauptseite/Artikel des Tages/Chronologie {year}'
editComment = u'Bot: heutiger AdT: [[{adt}]]{erneut}'
templateComment = u'Bot: dieser Artikel ist heute Artikel des Tages'
verwaltungTitle1 = u'Wikipedia:Hauptseite/Artikel des Tages/Verwaltung'
verwaltungTitle2 = u'Wikipedia:Hauptseite/Artikel des Tages/Verwaltung/Lesenswerte Artikel'

talkPageErrorMsg = (u'\n== Fehler beim automatischen Eintragen des heutigen Adt ({date}) ==\n<small>Dies ist'
        u'eine automatisch erstellte Fehlermeldung eines [[WP:Bots|Bots]]</small>\n\nDer Eintrag:\n*'
        u'{line}\nenthält das aktuelle Tagesdatum, obwohl der heutige AdT {adt} ist. Der Fehler wurde'
        u'\'\'nicht\'\' berichtigt, bitte überprüfen. --~~~~')
talkPageErrorComment = (u'neu /* Fehler beim automatischen Eintragen des heutigen Adt ({date}) */, manuelle'
        u'Berichtigung notwendig')

class AdtMain():
    def __init__(self):
        self.site = pywikibot.Site()
        self.site.login()

        locale.setlocale(locale.LC_ALL, 'de_DE.utf8')
        self.dayName = time.strftime('%A')
        self.monthName = time.strftime('%B')
        self.year = time.localtime().tm_year
        self.adtDate = time.strftime('%d.%m.%Y') #31.12.2013
        self.snapDate = time.strftime('%d. %B %Y') #31. Dezember 2013
        pywikibot.output(u'\n\ninit complete: ' + time.strftime('%d. %B %Y, %H:%M:%S'))

        self.adtErneut = None
        self.adtTitle = None

        self.get_adt()
        if self.adtTitle != None:
            self.addto_verwaltung()
            self.addto_chron()
            #self.add_template()

    def get_adt(self):
        title = adtPageTitle.format(dayName=self.dayName)
        adtPage = pywikibot.Page(self.site, title)
        code = mwparserfromhell.parse(adtPage.text)

        for template in code.filter_templates():
            if template.name.matches((u'AdT-Vorschlag', u'AdT-Vorschlag\n')):
                l = re.search(r'\s*(?P<adt>.*)\s*\n?',
                        unicode(template.get(u'LEMMA').value))
                d = re.search(r'\d{2}\.\d{2}\.\d{4}',
                        unicode(template.get(u'DATUM').value))
                if l and d.group() == self.adtDate:
                    self.adtTitle = l.group('adt')
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
            pywikibot.warning(u'Verwlatung: AdT nicht gefunden!')
    def __verwaltung(self, pageTitle):
        page = pywikibot.Page(self.site, pageTitle)
        oldtext = page.text ##debug
        line_list = page.text.splitlines()

        line_count = -1
        for text_line in line_list:
            line_count += 1
            adt = re.search(r'\[\[(?P<adt>[^\|\]]*)\|?[^\]]*?\]\]', text_line)
            if adt and adt.group('adt') == self.adtTitle:
                if self.adtDate.strip() in text_line.strip():
                    r = re.findall(r'\d{2}\.\d{2}\.\d{4}', text_line)
                    if len(r) > 1:
                        self.adtErneut = True
                    else:
                        self.adtErneut = False

                    text_line = text_line.replace(u'\'\'', u'')
                    if text_line != line_list[line_count]:
                        line_list[line_count] = text_line
                    else:
                        pywikibot.output(u'Verwaltung: AdT wurde schon in ' + pageTitle +\
                                u' eingetragen')
                        return True

                elif u'\'\'\'' in text_line: #neu
                    self.adtErneut = False

                    text_line = text_line.replace(u'\'\'\'', u'')
                    text_line = text_line.rsplit(u']]', 1)[0] + u']] <small>' + self.adtDate +\
                            u'</small> -'
                    line_list[line_count] = text_line
                else:
                    self.adtErneut = True

                    text_line = text_line.rsplit('</small>', 1)[0]
                    text_line += u' + ' + self.adtDate + u'</small> -'
                    line_list[line_count] = text_line
            elif self.adtDate.strip() in text_line.strip():
                talkpage = page.toggleTalkPage()
                talkpage.text += talkPageErrorMsg.format(date=self.adtDate, line=text_line, adt=self.adtTitle)
                comment = talkPageErrorComment.format(date=self.adtDate)
                talkpage.save(comment=comment, botlfag=False, minor=False)

        if page.text != u'\n'.join(line_list):
            page.text = u'\n'.join(line_list)
            if self.adtErneut:
                comment = editComment.format(adt=self.adtTitle,erneut=u' (erneut)')
            else:
                comment = editComment.format(adt=self.adtTitle,erneut=u'')
            pywikibot.showDiff(oldtext,page.text) ##debug
            page.save(comment=comment, botflag=False, minor=True)
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
            part[2] = u'\n' + part[2]
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
        for template in code.filter_templates(recursive=False):
            if template.name.matches("war AdT"):
                pywikibot.output(u'D:AdT: {{war AdT}} gefunden, füge heute hinzu')
                template.add(str(len(template.params)+1), self.adtDate)

        if unicode(code) == adtPage.text:
            template = u'{{war AdT|1=' + self.adtDate + u'}}\n'
            adtPage.text = template + adtPage.text

        print adtPage.text ##debug
        #adtPage.save(comment=templateComment, botflag=False, minor=False)

if __name__ == "__main__":
    try:
        AdtMain()
    finally:
        pywikibot.stopme()
