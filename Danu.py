#!/usr/bin/python
# -*- coding: utf-8 -*-
# MIT License
# Copyright (C) 2013-2014 sitic

import pywikibot
import pywikibot.date
import time

#what should be snapshoted?
mainPageTitle = {
    'en' : u'Main Page',
    'de' : u'Wikipedia:Hauptseite'
}
#will be added at the top of the snapshoted page
archivePageIntro = {
    'en' : u'',
    'de' : u'{{{{Wikipedia:Hauptseite/Archiv/Vorlage|Tag={day}|Monat={month}|Jahr={year}}}}}\n{{{{bots|denyscript=delinker}}}}\n'
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
    'de' : u'[[WP:Bot|Bot]]: erstelle Abbild der heutigen [[Wikipedia:Hauptseite|Hauptseite]]'
}
newMonthComment = {
    'en' : u'Bot: adding links to next month',
    'de' : u'[[WP:Bot|Bot]]: Vorbereitung für den nächsten Monat'
}

class SnapMain():
    def __init__(self):
        self.site = pywikibot.Site()
        self.site.login()

        self.day = time.localtime().tm_mday
	self.month = time.localtime().tm_mon
        self.monthName = pywikibot.date.monthName(self.site.language(),
                self.month)
        if self.month == 12: # end of the year?
            self.nextmonthName = pywikibot.date.monthName(self.site.language(),
                    1)
        else:
            self.nextmonthName = pywikibot.date.monthName(self.site.language(),
                    self.month + 1)
            
        self.year = time.localtime().tm_year
        self.nextyear = time.localtime().tm_year + 1

        self.snap()

        self.maxDays = pywikibot.date.getNumberOfDaysInMonth(
                time.localtime().tm_mon)
        if time.localtime().tm_mday == self.maxDays: #end of the month?
            pass
            #self.new_month()

    def format_date(self, day, monthName, year):
        """
        return a string with the formated date (e.g. u'31. Dezember 2013')
        """
        l_dateformat = pywikibot.translate(self.site, dateformat,
                fallback=False)
        return l_dateformat.format(day=day, monthName=monthName, year=year)

    def isleapyear(self, n):
        if n % 400 == 0:
            return True
        if n % 100 == 0:
            return False
        if n % 4 == 0:
            return True
        else:
            return False


    def snap(self):
        pywikibot.output(u'creating snapshot for today: ' +
                self.format_date(self.day, self.monthName, self.year))
        l_mainPageTitle      = pywikibot.translate(self.site, mainPageTitle,
                fallback=False)
        l_archiveTitlePrefix = pywikibot.translate(self.site,
                archiveTitlePrefix, fallback=False)
        l_archivePageIntro   = pywikibot.translate(self.site, archivePageIntro,
                fallback=False)
        l_archiveComment     = pywikibot.translate(self.site, archiveComment,
                fallback=False)

	l_archivePageIntro = l_archivePageIntro.format(day=time.strftime('%d'),
			month=time.strftime('%m'), year=self.year)

        mainPage = pywikibot.Page(self.site, l_mainPageTitle)
        date = self.format_date(self.day, self.monthName, self.year)
        archivePage = pywikibot.Page(self.site, l_archiveTitlePrefix + date)

        archivePage.text = pywikibot.textlib.removeLanguageLinks(mainPage.expand_text())
        archivePage.text = pywikibot.textlib.removeCategoryLinks(archivePage.text)
        archivePage.text = l_archivePageIntro + archivePage.text

        archivePage.save(comment=l_archiveComment, botflag=True, minor=False, force=True)

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
            if self.isleapyear(self.year) and time.localtime().tm_mon == 1:
                maxDays = 29
            else:
                maxDays = pywikibot.date.getNumberOfDaysInMonth(
                    time.localtime().tm_mon + 1)

	if self.format_date(1, self.nextmonthName, self.year) in templatePage.text:
		#template page is already up to date
		return

        templatePage.text = templatePage.text[:-1] + u'-\n| ' + self.nextmonthName

        for i in range(1, maxDays + 1):
            templatePage.text += u'|| [[' + l_archiveTitlePrefix +\
                    self.format_date(i, self.nextmonthName, self.year) +\
                    u'|' + i.__str__() + u']]'

        templatePage.text += u'\n|}'
        templatePage.save(comment=l_newMonthComment, botflag=True, minor=False)

if __name__ == "__main__":
    try:
        SnapMain()
    finally:
        pywikibot.stopme()
