#!/usr/bin/python
# -*- coding: utf-8 -*-
import pywikibot
import time

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
    'en' : u'Bot: creating snapshot of the current [[Main Page]]',
    'de' : u'[[WP:Bot|Bot]]: erstelle Abbild der heutigen [[Wikipedia:Hauptseite|Hauptseite]]'
}
newMonthComment = {
    'en' : u'Bot: adding links to next month',
    'de' : u'[[WP:Bot|Bot]]: Vorbereitung für den nächsten Monat'
}

yearsPageIntro = (u'<noinclude>{{Kasten|Diese Seite wird in [[Wikipedia:'
        u'Archiv der Hauptseite]] eingebunden und automatisch von [[Benutzer:'
        u'AsuraBot]] verwaltet.}}</noinclude>\n')

class SnapMain():
    def __init__(self):
        self.site = pywikibot.Site()
        self.site.login()

        self.day = time.localtime().tm_mday
        self.monthName = pywikibot.date.monthName(self.site.language(),
                time.localtime().tm_mon)
        if time.localtime().tm_mon == 12: # end of the year?
            self.nextmonthName = pywikibot.date.monthName(self.site.language(),
                    1)
        else:
            self.nextmonthName = pywikibot.date.monthName(self.site.language(),
                    time.localtime().tm_mon + 1)
            
        self.year = time.localtime().tm_year
        self.nextyear = time.localtime().tm_year + 1

        self.snap()

        self.maxDays = pywikibot.date.getNumberOfDaysInMonth(
                time.localtime().tm_mon)
        if time.localtime().tm_mday == self.maxDays: #end of the month?
            self.new_month()

        ##debug
        #self.new_month()

    def format_date(self, day, monthName, year):
        """
        return a string with the formated date (e.g. u'31. Dezember 2013')
        """
        l_dateformat = pywikibot.translate(self.site, dateformat,
                fallback=False)
        return l_dateformat.format(day=day, monthName=monthName, year=year)

    def isleapyear(n):
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
        l_archivePageOutro   = pywikibot.translate(self.site, archivePageOutro,
                fallback=False)
        l_archiveComment     = pywikibot.translate(self.site, archiveComment,
                fallback=False)

        mainPage = pywikibot.Page(self.site, l_mainPageTitle)
        date = self.format_date(self.day, self.monthName, self.year)
        archivePage = pywikibot.Page(self.site, l_archiveTitlePrefix + date)

        archivePage.text = pywikibot.removeLanguageLinks(mainPage.expand_text())
        archivePage.text = pywikibot.removeCategoryLinks(archivePage.text)
        archivePage.text += l_archivePageOutro

        print archivePage.text
        #archivePage.save(comment=l_archiveComment, botflag=False, minor=False)

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
