#!/usr/bin/python
# -*- coding: utf-8 -*-
# MIT License
# (C) sitic, 2013
import pywikibot
import mwparserfromhell
import re
import time
import locale

discPageTitle = u'Wikipedia Diskussion:Hauptseite/Artikel des Tages/Vorschläge'
erledigtTemplate = u'{{Erledigt|1=&nbsp;Gestriger AdT-Abschnitt, Baustein wurde [[WP:Bot|automatisch]] gesetzt. ~~~~}}\n\n'
erledigtComment = u'Bot: /* {section} */ {andere}als erledigt markiert'

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
        pywikibot.output(u'init complete: ' + time.strftime('%d. %B %Y, %H:%M:%S'))

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
                d = re.search(r'\d{2}\.\d{2}\.\d{4}\s?:', sectionname)
                if d and self.adtDate in d.group() and section_count < 5:
                    header_line = line_count
                else:
                    break

        pywikibot.output(u'WD:AdT: Abschnitt(e) ' + unicode(modsections) +\
                u' als erledigt markiert')
        if len(modsections) == 1:
            comment = erledigtComment.format(section=modsections[0],\
                    andere=u'')
        elif len(modsections) > 1:
            andere = u'sowie'
            for i in range(1,len(modsections)):
                code = mwparserfromhell.parse(modsections[i])
                section = code.strip_code(normalize=True, collapse=True)
                andere += u' [[#' + unicode(section) + ']]'
                if i > 1:
                    andere += u','
            comment = erledigtComment.format(section=modsections[0],\
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

if __name__ == "__main__":
    try:
        AdtMain()
    finally:
        pywikibot.stopme()
