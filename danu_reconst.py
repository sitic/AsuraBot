#!/usr/bin/python
# -*- coding: utf-8 -*-
# MIT License
# Copyright (C) 2013-2014 sitic

import pywikibot
import mwparserfromhell
import time
import locale
import re
import os #Linux only!
from datetime import datetime
from dateutil.relativedelta import *
from dateutil import tz

#what should be snapshoted?
mainPageTitle = {
    'en' : u'Main Page',
    'de' : u'Wikipedia:Hauptseite'
}
#will be added at the top of the snapshoted page
archivePageIntro = {
    'en' : u'',
    'de' : u'{{{{Wikipedia:Hauptseite/Archiv/Vorlage|Tag={day}|Monat={month}|Jahr={year}|rekonstruiert=Ja}}}}\n'
}
#where to put the snapshoted page
archiveTitlePrefix = {
    'en' : u'Wikipedia:Main Page history/',
    'de' : u'Wikipedia:Hauptseite/Archiv/'
}
#script will generate pages archiveTitlePrefix + localize(dateformat)
dateformat = {
    'en' : u'{year} {monthName} {day}',
    'de' : u'{day}. {monthName} {year}'
}
#where to update the template
templateTitle = {
    'en' : u'Template:Main Page history',
    'de' : u'Wikipedia:Hauptseite/Archiv'
}
archiveComment = {
    'en' : u'Bot: creating snapshot of the current [[Main Page]]',
    'de' : u'[[WP:Bot|Bot]]: erstelle Abbild der damaligen [[Wikipedia:Hauptseite|Hauptseite]]'
}
newMonthComment = {
    'en' : u'Bot: adding links to next month',
    'de' : u'[[WP:Bot|Bot]]: Vorbereitung für den nächsten Monat'
}

redlinksPage = u'Benutzer:AsuraBot/Hauptseite'
sump = u'|}'

class SnapMain():
    def __init__(self):
        self.site = pywikibot.Site()
        self.site.login()

        self.commons = self.site.image_repository()

        self.localtz = tz.gettz('Europe/Berlin')
        startdate = datetime(2013,  12, 31, 23, 59, 59, tzinfo=self.localtz)
        enddate   = datetime(2013,  12, 26, 23, 59, 59, tzinfo=self.localtz)

        self.reportPage = pywikibot.Page(self.site, redlinksPage)

        l_mainPageTitle = pywikibot.translate(self.site, mainPageTitle,
                fallback=False)
        self.mainPage = pywikibot.Page(self.site, l_mainPageTitle)
        self.mainversions = self.mainPage.getVersionHistory()

        day = startdate
        while day != enddate:
            self.snap(day)
            day -= relativedelta(days=1)

        #print sump.encode('utf-8')
        print self.reportPage.text.encode('utf-8')
        #self.reportPage.save()

    def snap(self, date):
        locale.setlocale(locale.LC_ALL, 'de_DE.utf8')
        monthName = pywikibot.date.monthName(self.site.language(), date.month)
        pywikibot.output(u'\n\ncreating snapshot for ' +
                self.format_date(date.day, monthName, date.year))
        l_mainPageTitle      = pywikibot.translate(self.site, mainPageTitle,
                fallback=False)
        l_archiveTitlePrefix = pywikibot.translate(self.site,
                archiveTitlePrefix, fallback=False)
        l_archivePageIntro   = pywikibot.translate(self.site, archivePageIntro,
                fallback=False)
        l_archiveComment     = pywikibot.translate(self.site, archiveComment,
                fallback=False)

	l_archivePageIntro = l_archivePageIntro.format(day=date.strftime('%d'),
			month=date.strftime('%m'), year=date.strftime('%Y'))

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
        replaced_templates = [l_mainPageTitle]
        templates = re.findall(u'{{/([^}]*?)}}', text) 
        for t in templates:
            t_text = self.replace_template(l_mainPageTitle + u'/' + t, date)
            text = text.replace(u'{{/' + t + u'}}', t_text)
            replaced_templates.append(l_mainPageTitle + u'/' + t)

        templates = [u'Hauptseite Verstorbene'] #templates in Template: namespace
        for t in templates:
            t_text = self.replace_template( u'Vorlage:' + t, date)
            text = text.replace(u'{{' + t + u'}}', t_text)
            replaced_templates.append(t)
        pywikibot.output(u'Replaced templates: ' + unicode(replaced_templates))

        text = text.replace(u'{{LOCALDAY}}', unicode(date.day))
        text = text.replace(u'{{LOCALDAYNAME}}', date.strftime('%A'))
        text = text.replace(u'{{LOCALMONTHNAME}}', monthName)
        text = text.replace(u'{{LOCALYEAR}}', unicode(date.year))

        remaining = []
        code = mwparserfromhell.parse(text)
        for template in code.filter_templates():
            remaining.append(unicode(template.name))
        pywikibot.output(u'\nRemaining templates: ' + unicode(remaining))

        archivePage.text = text
        archivePage.text = pywikibot.removeLanguageLinks(archivePage.expand_text())
        archivePage.text = pywikibot.removeCategoryLinks(archivePage.text)
        archivePage.text = l_archivePageIntro + archivePage.text


        #print archivePage.text
        #archivePage.save(comment=l_archiveComment, botflag=True, minor=False)

        self.redlinks(archivePage, date, monthName)

    def replace_template(self, title, date):
        """get versions of templated, find visible version and find visible text"""

        page = pywikibot.Page(self.site, title)
        if not page.exists():
            pywikibot.output(u'Fatal Error: ' + title + u' does not exist!')
            os._exit(1)

        self.site.loadrevisions(page=page, total=50,
                starttime=date.astimezone(tz.tzutc()).replace(tzinfo=None))
        versions = page.fullVersionHistory()

        i = -1
        while True:
            i += 1
            if i == len(versions) - 1:
                pywikibot.output(u'Fatal Error: Old versions of ' + title + u' do not exist!')
                os._exit(1)

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

    def redlinks(self, snap_page, date, monthName):
        oldtext = self.reportPage.text
        linkgen = snap_page.linkedPages()
        for page in linkgen:
            if not page.exists():
                pywikibot.output(u'Pagelink ' + page.title() + ' is dead')
                self.reportPage.text = u'* [[' + page.title() + u']]\n' +\
                        self.reportPage.text

        imagegen = snap_page.imagelinks()
        for image in imagegen:
            commonspage = pywikibot.ImagePage(self.commons, image.title(withNamespace=False))
            if not image.exists() and not commonspage.exists():
                pywikibot.output(u'Image ' + image.title() + ' is dead')
                commonsurl = self.commns.getUrl() + u'/' + commonspage.title()
                self.reportPage.text = u'* [[:' + image.title() + u']] ([[:commons:' +\
                        commonspage.title() + u']])\n' + self.reportPage.text

        if self.reportPage.text != oldtext:
            self.reportPage.text = u';' + self.format_date(date.day,
                    monthName, date.year) + u'\n' + self.reportPage.text

        if date.day == 1:
            self.reportPage.text = u'=== ' + monthName + u' ===\n' +\
                    self.reportPage.text
            
            if date.month == 1:
                self.reportPage.text = u'== ' + unicode(date.year) + u' ==\n' +\
                        self.reportPage.text
            
    def format_date(self, day, monthName, year):
        """
        return a string with the formated date (e.g. u'31. Dezember 2013')
        """
        l_dateformat = pywikibot.translate(self.site, dateformat,
                fallback=False)
        return l_dateformat.format(day=day, monthName=monthName, year=year)

    def new_month(self, date):
        pywikibot.output(u'new month, updating template')
        l_archiveTitlePrefix = pywikibot.translate(self.site,
                archiveTitlePrefix, fallback=False)
        l_templateTitle   = pywikibot.translate(self.site, templateTitle,
                fallback=False)
        l_newMonthComment = pywikibot.translate(self.site, newMonthComment,
                fallback=False)

        if date.month == 12:
            self.nextmonthName = pywikibot.date.monthName(self.site.language(), 1)
        else:
            self.nextmonthName = pywikibot.date.monthName(self.site.language(), date.month + 1)
        global sump
        #templatePage = pywikibot.Page(self.site, l_templateTitle)
        if date.month == 12: # end of the year?
            newYearTable = u'\n\n\n{{|\n|+ \'\'\'{year}\'\'\'\n|}}'
            sump += newYearTable.format(year=date.year + 1)

            year = date.year + 1
            maxDays = 31 #January
        else:
            #check for leap year, getNumberOfDaysInMonth() does not do that
            year = date.year
            if self.isleapyear(date.year) and date.month == 1:
                maxDays = 29
            else:
                maxDays = pywikibot.date.getNumberOfDaysInMonth(
                    date.month + 1)

        sump = sump[:-1] + u'-\n| ' + self.nextmonthName

        for i in range(1, maxDays + 1):
            sump += u'|| [[' + l_archiveTitlePrefix +\
                    self.format_date(i, self.nextmonthName, year) +\
                    u'|' + i.__str__() + u']]'

        sump += u'\n|}'
#        print sump
        #templatePage.save(comment=l_newMonthComment, botflag=False)

    def isleapyear(self, n):
        if n % 400 == 0:
            return True
        if n % 100 == 0:
            return False
        if n % 4 == 0:
            return True
        else:
            return False

if __name__ == "__main__":
    try:
        SnapMain()
    finally:
        pywikibot.stopme()
