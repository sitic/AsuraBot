#!/usr/bin/python
# -*- coding: utf-8 -*-
# MIT License
# Copyright (C) 2013-2014 sitic

import pywikibot
import mwparserfromhell as mwparser
import dateutil.parser as dateparser
import dateutil.relativedelta as datedelta
import datetime
import locale
import re
import sys

sgPageTitle = u'Wikipedia:Hauptseite/Schon gewusst/{dayName}'
sgVerwaltungTitle = u'Wikipedia Diskussion:Hauptseite/Schon gewusst'
templateComment = u"""Bot: dieser Artikel wird heute auf der [[Wikipedia:Hauptseite|Hauptseite]] unter [[WP:SG?|Schon gewusst?]] präsentiert"""  # NOQA
proposalComment = u"""Bot: dieser Artikel wurde für [[WP:SG?|Schon gewusst?]] vorgeschlagen ([[WD:SG?#{section}|Diskussion]])"""  # NOQA
sgTemplate = u"""{{{{Schon gewusst|{DiskussionsJahr}|{DiskussionsMonat}|{Ueberschrift}|{ListungsMonat}|{ListungsJahr}|{ListungsTag}}}}}"""  # NOQA

sgTemplates = (u'Schon gewusst', u'schon gewusst', u'SG')
regexDate = re.compile(
    r".*(?P<date>\d{2}:\d{2}, \d{1,2}\. \S{3}\. \d{4}) \(CES?T\).*?$",
    re.MULTILINE)


class SgMain():
    def __init__(self):
        self.dry = False  # debug
        self.site = pywikibot.Site()
        self.site.login()

        locale.setlocale(locale.LC_ALL, 'de_DE.utf8')
        self.today = datetime.date.today()
        self.dayName = self.today.strftime('%A').decode('utf-8')
        self.monthName = self.today.strftime('%B').decode('utf-8')

        self.sgs = []
        self.proposed_sgs = []
        self.get_sgs()

    def run(self, do_propsed=False):
        pywikibot.output(u'\n\ninit complete: ' +
                         (datetime.datetime.now()
                          .strftime('%d. %B %Y, %H:%M:%S')).decode('utf-8'))

        pywikibot.output(u'SGs: ' + str(self.sgs))
        for sg in self.sgs:
            try:
                self.add_sg_template(sg)
            except Exception as e:
                import traceback
                top = traceback.extract_tb(sys.exc_info()[2])[-1]
                pywikibot.output(u'ERROR: ' + str(type(e).__name__) +
                                 u'at line:' + str(top[1]))
        try:
            # Purge yesterdays SG disc pages
            self.sgs = []
            yesterday = self.today - datedelta.relativedelta(days=1)
            self.get_sgs(yesterday)
            for sg in self.sgs:
                page = pywikibot.Page(self.site, sg, ns=1)
                page.purge()
        except Exception as e:
            import traceback
            top = traceback.extract_tb(sys.exc_info()[2])[-1]
            pywikibot.output(u'ERROR: ' + str(type(e).__name__) +
                             u'at line:' + str(top[1]))

        if not do_propsed:
            return
        try:
            self.get_proposed_sgs()
            for title, section_date, section_title in self.proposed_sgs:
                pywikibot.output(u'Vorgeschlagen fur SG: ' + title)
                self.add_proposed_sg_template(title,
                                              section_date,
                                              section_title)
        except Exception as e:
            import traceback
            top = traceback.extract_tb(sys.exc_info()[2])[-1]
            pywikibot.output(u'ERROR: ' + str(type(e).__name__) +
                             u'at line:' + str(top[1]))

    def get_sgs(self, date=None):
        if date is None:
            date = self.today
        dayName = date.strftime('%A').decode('utf-8')
        title = sgPageTitle.format(dayName=dayName)
        sgPage = pywikibot.Page(self.site, title)
        code = mwparser.parse(sgPage.text)

        for tag in code.filter_tags(recursive=True):
            if tag.tag == u'onlyinclude':
                for link in tag.contents.filter_wikilinks():
                    if self.check_ns(unicode(link.title)):
                        title = link.title.strip_code(normalize=True,
                                                      collapse=True)
                        # Replace non-breaking space with space
                        title = unicode(title).replace(u'\xa0', u' ')
                        self.sgs.append(title)

    def cleanup_sectionlink(self, section_title):
        code = mwparser.parse(section_title)
        template = code.filter_templates()
        if len(template) == 1 and template[0].name.matches(('Erl', 'erl')):
            section_title = template[0].get(1)

        title = mwparser.parse(unicode(section_title))
        clean_title = title.strip_code(normalize=True, collapse=True).strip()
        return clean_title

    def create_sg_template(self, discdate, discsection, sg_date=None):
        if not all([discdate, discsection]):
            raise NotImplementedError

        # {{Schon gewusst | DiskussionsJahr | DiskussionsMonat | Überschrift |
        # ListungsMonat | ListungsJahr | ListungsTag}}
        params = None
        if sg_date is None:
            params = [discdate.year,
                      discdate.strftime("%m"),
                      self.cleanup_sectionlink(discsection)]

        else:
            params = [discdate.year,
                      discdate.strftime("%m"),
                      self.cleanup_sectionlink(discsection),
                      sg_date.strftime("%m"),
                      sg_date.year,
                      sg_date.day]

        sg_template = mwparser.nodes.Template(sgTemplates[0], params)
        return sg_template

    def add_sg_template(self, title, date=None):
        if date is None:
            date = self.today
        page = pywikibot.Page(self.site, title, ns=1)
        if not page.toggleTalkPage().exists():
            raise NotImplementedError

        [discdate, discsection] = self.check_disc(title)
        sg_template = self.create_sg_template(discdate, discsection, date)

        text = None
        if page.exists():
            code = mwparser.parse(page.text)
            found = False

            for template in code.filter_templates(recursive=False):
                if template.name.matches(sgTemplates):
                    if len(template.params) < len(sg_template.params):
                        code.replace(template, sg_template)
                    found = True
            text = unicode(code)

            if not found:
                text = unicode(sg_template) + u'\n' + text
        else:
            page.text = u''
            text = unicode(sg_template)

        if page.text != text:
            pywikibot.showDiff(page.text, text)  # debug
            page.text = text
            if not self.dry:
                page.save(comment=templateComment, botflag=True, minor=True)

    def add_proposed_sg_template(self, title, discdate, discsection):
        page = pywikibot.Page(self.site, title, ns=1)
        if not page.toggleTalkPage().exists():
            raise NotImplementedError

        sg_template = self.create_sg_template(discdate, discsection)

        text = None
        if page.exists():
            code = mwparser.parse(page.text)
            for template in code.filter_templates(recursive=False):
                if template.name.matches(sgTemplates):
                    return
            text = unicode(sg_template) + u'\n' + page.text
        else:
            page.text = u''
            text = unicode(sg_template)

        if page.text != text:
            pywikibot.showDiff(page.text, text)  # debug
            page.text = text
            if not self.dry:
                comment = proposalComment.format(
                    section=self.cleanup_sectionlink(discsection)
                )

                page.save(comment=comment, botflag=False, minor=True)

    def check_disc(self, title, date=None):
        infos = self.get_section_infos()
        # print repr(title)
        for section_date, section_title in infos:
            # print repr(unicode(section_title))
            if title in unicode(section_title):
                return [section_date, section_title]

        raise NotImplementedError

    def get_proposed_sgs(self, date=None):
        infos = self.get_section_infos()
        for section_date, section_title in infos:
            code = mwparser.parse(section_title)
            title = None
            for link in code.filter_wikilinks():
                if self.check_ns(link.title):
                    title = unicode(link.title)
            sg = [title, section_date, section_title]
            if all(sg):
                self.proposed_sgs.append(sg)

    def get_section_infos(self, date=None):
        page = pywikibot.Page(self.site, sgVerwaltungTitle)
        code = mwparser.parse(page.text)
        infos = []
        for section in code.get_sections([2]):
            title = section.filter_headings()[0].title
            date = self.get_discdate(section)
            infos.append([date, title])
        return infos

    def get_discdate(self, section):
        section = unicode(section)
        datestr = regexDate.search(section)

        date = None
        if datestr:
            date = datestr.group('date')
            date = self.date_parser(date)
        return date

    def date_parser(self, date):
        dictionary = {
            u'Jan.': 'January',
            u'Feb.': 'February',
            u'Mär.': 'March',
            u'Apr.': 'April',
            u'Mai.': 'May',
            u'Jun.': 'June',
            u'Jul.': 'July',
            u'Okt.': 'October',
            u'Nov.': 'November',
            u'Dez.': 'December'
            }

        for lang, en in dictionary.items():
            date = date.replace(lang, en)

        date = dateparser.parse(date, dayfirst=True)
        return date

    def check_ns(self, title, ns=0):
        page = pywikibot.Page(self.site, title)
        if page.namespace() == ns:
            return True
        else:
            return False

if __name__ == "__main__":
    try:
        runner = SgMain()
        if len(sys.argv) < 2:
            runner.run()
        else:
            runner.run(True)
    finally:
        pywikibot.stopme()
