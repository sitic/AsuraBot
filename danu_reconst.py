#!/usr/bin/python
# -*- coding: utf-8 -*-
# MIT License
# (C) sitic, 2013

import pywikibot
import mwparserfromhell
import time
import locale
import re
from datetime import datetime
from dateutil.relativedelta import *
from dateutil import tz

#what should be snapshoted?
mainPageTitle = {
    'en' : u'Main Page',
    'de' : u'Wikipedia:Hauptseite'
}
#will be added at the end of the snapshoted page
archivePageOutro = {
    'en' : u'',
    'de' : u'\n[[Kategorie:Wikipedia:Hauptseite Archiv]]'
}
#where to put the snapshoted page
archiveTitlePrefix = {
    'en' : u'Wikipedia:Main Page history/',
#    'de' : u'Wikipedia:Hauptseite/Archiv/'
    'de' : u'Benutzer:Sitic/'
}
#script will generate pages archiveTitlePrefix + localize(dateformat)
dateformat = {
    'en' : u'{year} {monthName} {day}',
    'de' : u'{day}. {monthName} {year}'
}
#where to update the template
templateTitle = {
    'en' : u'Template:Main Page history',
    'de' : u'Wikipedia:Hauptseite/Archiv/Vorlage'
}
archiveComment = {
    'en' : u'Bot: creating snapshot of the [[Main Page]]',
    'de' : u'[[WP:Bot|Bot]]: rekonstruiere Abbild der damaligen [[Wikipedia:Hauptseite|Hauptseite]]'
}
newMonthComment = {
    'en' : u'Bot: adding links to next month',
    'de' : u'[[WP:Bot|Bot]]: Vorbereitung für den nächsten Monat'
}

yearsPageIntro = (u'<noinclude>{{Kasten|Diese Seite wird in [[Wikipedia:Archiv der Hauptseite]] eingebunden und automatisch von [[Benutzer:AsuraBot]] verwaltet.}}</noinclude>\n')

class SnapMain():
    def __init__(self):
        self.site = pywikibot.Site()
        self.site.login()

        self.localtz = tz.gettz('Europe/Berlin')
        startdate = datetime(2013,  2,  1, 23, 59, 59, tzinfo=self.localtz)
        enddate   = datetime(2013,  1,  1, 23, 59, 59, tzinfo=self.localtz)

        l_mainPageTitle = pywikibot.translate(self.site, mainPageTitle,
                fallback=False)
        self.mainPage = pywikibot.Page(self.site, l_mainPageTitle)
        self.mainversions = self.mainPage.getVersionHistory()
        print len(self.mainversions)

        day = startdate
        while day != enddate:
            self.snap(day)
            day -= relativedelta(days=1)

    def snap(self, date):
        locale.setlocale(locale.LC_ALL, 'de_DE.utf8')
        monthName = pywikibot.date.monthName(self.site.language(), date.month)
        pywikibot.output(u'creating snapshot for ' +
                self.format_date(date.day, monthName, date.year))
        l_mainPageTitle      = pywikibot.translate(self.site, mainPageTitle,
                fallback=False)
        l_archiveTitlePrefix = pywikibot.translate(self.site,
                archiveTitlePrefix, fallback=False)
        l_archivePageOutro   = pywikibot.translate(self.site, archivePageOutro,
                fallback=False)
        l_archiveComment     = pywikibot.translate(self.site, archiveComment,
                fallback=False)

        title = self.format_date(date.day, monthName, date.year)
        archivePage = pywikibot.Page(self.site, l_archiveTitlePrefix + title)

        i = -1
        while True:
            i += 1
            laststamp = self.mainversions[i][1]
            laststamp = laststamp.replace(tzinfo=tz.tzutc()).astimezone(self.localtz)
            if laststamp < date:
                revid = self.mainversions[i][0]
                text = self.mainPage.getOldVersion(revid)
                break

        text = text.replace(u'{{LOCALDAY}}', unicode(date.day))
        text = text.replace(u'{{LOCALDAYNAME}}', date.strftime('%A'))
        text = text.replace(u'{{LOCALMONTHNAME}}', monthName)
        text = text.replace(u'{{LOCALYEAR}}', unicode(date.year))
        text = text.replace(u'{{/Interwikis}}', u'')

        #templates in main page subspace
        templates = re.findall(u'{{/([^}]*?)}}', text) 
        print templates
        for t in templates:
            t_text = self.replace_template(l_mainPageTitle + u'/' + t, date)
            text = text.replace(u'{{/' + t + u'}}', t_text)

        templates = [u'Hauptseite Verstorbene'] #templates in Template: namespace
        for t in templates:
            t_text = self.replace_template( u'Vorlage:' + t, date)
            text = text.replace(u'{{' + t + u'}}', t_text)

        text = text.replace(u'{{LOCALDAY}}', unicode(date.day))
        text = text.replace(u'{{LOCALDAYNAME}}', date.strftime('%A'))
        text = text.replace(u'{{LOCALMONTHNAME}}', monthName)
        text = text.replace(u'{{LOCALYEAR}}', unicode(date.year))

        code = mwparserfromhell.parse(text)
        for template in code.filter_templates():
            pywikibot.output(unicode(template.name))

        archivePage.text = text
        archivePage.text = pywikibot.removeLanguageLinks(archivePage.expand_text())
        archivePage.text = pywikibot.removeCategoryLinks(archivePage.text)
        archivePage.text += l_archivePageOutro

        #print archivePage.text
        #archivePage.save(comment=l_archiveComment, botflag=False, minor=False)

    def replace_template(self, title, date):
        """get versions of templated, find visible version and find visible text"""

        page = pywikibot.Page(self.site, title)
        self.site.loadrevisions(page=page, total=50,
                starttime=date.astimezone(tz.tzutc()).replace(tzinfo=None))
        versions = page.fullVersionHistory()
        print len(versions)
        i = -1
        while True:
            i += 1
            laststamp = versions[i][1]
            laststamp = laststamp.replace(tzinfo=tz.tzutc()).astimezone(self.localtz)
            if laststamp < date:
                revid = versions[i][0]
                text = page.getOldVersion(revid)
                break

        onlyinc = re.findall(u'<onlyinclude>([\S\s]+?)</onlyinclude>', text)
        if len(onlyinc):
            text = u''
        for i in onlyinc:
            text += i

        noinc = re.findall(u'<noinclude>(\n*?.*?)</noinclude>', text)
        for n in noinc:
            text = text.replace(u'<noinclude>' + n + u'</noinclude>', u'')

        text = text.replace(u'<includeonly>', u'')
        text = text.replace(u'</includeonly>', u'')

        return text

    def format_date(self, day, monthName, year):
        """
        return a string with the formated date (e.g. u'31. Dezember 2013')
        """
        l_dateformat = pywikibot.translate(self.site, dateformat,
                fallback=False)
        return l_dateformat.format(day=day, monthName=monthName, year=year)

    def new_month(self):
        pywikibot.output(u'new month, updating template')
        l_archiveTitlePrefix = pywikibot.translate(self.site,
                archiveTitlePrefix, fallback=False)
        l_templateTitle   = pywikibot.translate(self.site, templateTitle,
                fallback=False)
        l_newMonthComment = pywikibot.translate(self.site, newMonthComment,
                fallback=False)

        templatePage = pywikibot.Page(self.site, l_templateTitle)
        if time.localtime().tm_mon == 12: # end of the year?
            newYearTable = u'\n\n\n{{|\n|+ \'\'\'{year}\'\'\'\n|}}'
            templatePage.text += newYearTable.format(year=self.nextyear)

            self.year = self.nextyear
            maxDays = 31 #January
        else:
            #check for leap year, getNumberOfDaysInMonth() does not do that
            if isleapyear(self.year) and time.localtime().tm_mon == 1:
                maxDays = 29
            else:
                maxDays = pywikibot.date.getNumberOfDaysInMonth(
                    time.localtime().tm_mon + 1)

        templatePage.text = templatePage.text[:-1] + u'-\n| ' + self.nextmonthName

        for i in range(1, maxDays + 1):
            templatePage.text += u'|| [[' + l_archiveTitlePrefix +\
                    self.format_date(i, self.nextmonthName, self.year) +\
                    u'|' + i.__str__() + u']]'

        templatePage.text += u'\n|}'
        print templatePage.text
        #templatePage.save(comment=l_newMonthComment, botflag=False)

if __name__ == "__main__":
    try:
        SnapMain()
    finally:
        pywikibot.stopme()
