#!/usr/bin/env python
# -*- coding: utf-8 -*-
# MIT License
# Copyright (C) 2013-2014 sitic

import pywikibot
from threading import Thread
import time
import irc.bot
import irc.strings
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr

contactUser = u'Sitic' #used in IRC
sandboxTitle = u'Wikipedia:Spielwiese'
sandboxTemplate = u'{{Bitte erst NACH dieser Zeile schreiben! (Begrüßungskasten)}}'
textTitle = u'Vorlage:Bitte erst NACH dieser Zeile schreiben! (Begrüßungskasten)/Text'
sandboxDefault = sandboxTemplate + u'\n{{subst:' + textTitle + u'}}'

revIdDoku = u'<noinclude>{{Dokumentation/Unterseite}}</noinclude>'
revIdEmptyTitle = u'Vorlage:Bitte erst NACH dieser Zeile schreiben! (Begrüßungskasten)/Revid Leer'
revIdEmptyAddon = (u'<noinclude>\n{{Kasten|Diese Zahl ist die Revisions-ID zu'
        u' einer Revision einer leeren Spielwiese (enthält nur den'
        u' Begrüßungskasten). Sie wird nach dem Löschen der Spielwiese'
        u' automatisch von [[Benutzer:AsuraBot]] aktualisiert.}}</noinclude>')
revIdTextTitle = u'Vorlage:Bitte erst NACH dieser Zeile schreiben! (Begrüßungskasten)/Revid Text'
revIdTextAddon = (u'<noinclude>\n{{Kasten|Diese Zahl ist die Revisions-ID zu'
        u' einer unveränderten Revision Spielwiese (<code><nowiki>{{Bitte erst'
        u' NACH dieser Zeile schreiben! (Begrüßungskasten)}}{{subst:Bitte erst'
        u' NACH dieser Zeile schreiben! (Begrüßungskasten)/Text}}</nowiki>'
        u'</code>). Sie wird nach dem Löschen der Spielwiese automatisch von '
        u'[[Benutzer:AsuraBot]] aktualisiert.}}</noinclude>')

revIdComment = u'Bot: neue Revisions ID'
sandboxResetComment = u'[[WP:Bots|Bot]]: Spielwiese gemäht (zurückgesetzt) ([[Benutzer:Sitic/WL#Neugestaltung|Pilotphase]])'
sandboxTemplateInsertComment = u'[[WP:Bots|Bot]]: Begrüßungskasten am Einfang eingefügt' +\
        u', bitte erst nach dieser Zeile schreiben.'
sandboxTextComment = sandboxResetComment + \
        u', neue Version des [['+ textTitle + '|Standardtextes]]'
sandboxDeletedComment = (u'Bot: Spielwiese wurde gelöscht, ich erstelle neue '
        u'Versionen und aktualisiere die Vorlage.')

merlBotPage = u'Wikipedia:Spielwiese/Vorlage' #fix for dewiki:User:MerlBot
timeformat = '%d. %B %Y, %H:%M:%S: '

class IrcHandler: 
  """IrcListener calls IrcHander.new_event for every new rc log entry.
  Do all the real work here.
  
  """
  def __init__(self):
    self.site = pywikibot.Site()
    self.site.login()
    self.sandboxPage = pywikibot.Page(self.site, sandboxTitle)

    #reset sandbox to save the default text
    self.reset_sandbox()
    self.sandboxDefaultText = self.sandboxPage.get(force=True)

    self.merlbot_fix() #fix for dewiki:User:MerlBot

    self.t_changed = time.time() #time of the last sandbox change
    self.t_reset = time.time()   #last time sandbox was default text

  def new_event(self, message): #new rc log entry
     """new rc log entry from IRC.
     Watch for changes on sandbox and related pages, 
     if found start functions dealing with the change as new thread.
     Check the reset timers"""
     try:
          message = message.encode('utf-8', 'ignore').strip()
          page = message.split('\x0314[[\x0307', 1)[1] 
          page = page.split('\x0314]]\x034', 1)[0] 

          if 'Spezial:Log' in page:
              if 'Spezial:Log/delete' in page and \
                      '\x0314]]\x034 delete\x0310' in message:
                  user = message.split('\x035*\x03 \x0303', 1)[1]
                  user = user.split('\x03 \x035*\x03', 1)[0]

                  page = message.split('\x0310deleted "[[\x0302', 1)[1]
                  page = page.split('\x0310]]"', 1)[0]

                  if page.decode('utf-8', 'ignore').strip() == sandboxTitle.strip():
                      Thread(target=self.sandbox_deleted).start()

          else:
                  #editcomment = message.rsplit('\x0310', 1)[1]
                  #editcomment = editcomment.rsplit('\x03', 1)[0]
                  #flags = message.split('\x0314]]\x034 ', 1)[1]
                  #flags = flags.split('\x0310', 1)[0]
                  
                  user = message.split('\x035*\x03 \x0303', 1)[1]
                  user = user.split('\x03 \x035*\x03', 1)[0]
                  
		  # add .decode('utf-8', 'replace')?
                  ##includes fix for dewiki:User:MerlBot
                  if page.decode('utf-8', 'ignore').strip() == sandboxTitle.strip() and \
                          user.decode('utf-8', 'ignore').strip() != \
                          pywikibot.Site().username().strip() and \
                          user.decode('utf-8', 'ignore').strip() != u'Benutzer:MerlBot':
                      #Sandbox changed, check what changed
                      Thread(target=self.sandbox_changed).start()

                  elif page.decode('utf-8', 'ignore').strip() == textTitle.strip():
                      #Text changed, update sandbox & revid
                      Thread(target=self.text_changed).start()

		  # Sandbox or related pages were not changed.
		  # Now check if it is time to reset non-default sandbox
                  elif self.sandbox_is_changed and \
                          (time.time() - self.t_changed > 900):
                      Thread(target=self.reset_sandbox).start()
                      self.sandbox_is_changed = False

                  elif self.sandbox_is_changed and \
		          (time.time() - self.t_reset > 3600):
                      Thread(target=self.reset_sandbox).start()
                      self.sandbox_is_changed = False
     except IndexError:
         pywikibot.output(u"\n\03{lightred}" + time.strftime(timeformat) +\
                 u"Split ERROR!\03{default}")
         pywikibot.output(message.strip())
         pywikibot.output(u"\n")
     except UnicodeDecodeError:
         pywikibot.output(u"\n\03{lightred}" + time.strftime(timeformat) +\
                 u"Currupted data, UnicodeDecodeError\03{default}")
         pywikibot.output(message.strip())
         pywikibot.output(u"\n")

  def sandbox_changed(self):
    """Something on the sandbox changed, check what."""
    
    time.sleep(0.5) #sometimes were are faster then mediawiki
    text = self.sandboxPage.get(force=True, get_redirect=True)
    if text == self.sandboxDefaultText:
        self.sandbox_is_changed = False
        self.sandbox_is_default = True
        pywikibot.output(u"\n\03{lightyellow}" + time.strftime(timeformat) +\
                u"Sandbox is on default text\03{default}")
    elif not text.startswith(sandboxTemplate):
        pywikibot.output(u"\n\03{lightyellow}" + time.strftime(timeformat) +\
                u"Sandbox template is not at the beginning!\03{default}")
        self.add_template()
    else:
        pywikibot.output(u"\n\03{lightyellow}" + time.strftime(timeformat) +\
               u" Sandbox was changed\03{default}")
        #pywikibot.showDiff(self.sandboxDefaultText, text)
        self.sandbox_is_changed = True
        self.t_changed = time.time()
        if self.sandbox_is_default:
    	    self.t_reset = time.time()
    	    self.sandbox_is_default = False

  def add_template(self):
    """The template is not at the beginning of the sandbox, insert it"""

    pywikibot.output(u'\03{lightyellow}Adding template ...\03{default}')
    try:
        _ = self.sandboxPage.get(force=True, get_redirect=True)
        text = self.sandboxPage.text.replace(sandboxTemplate, u'')
        self.sandboxPage.text = sandboxTemplate + u'\n' + text

        comment = sandboxTemplateInsertComment
        self.sandboxPage.save(comment=comment, botflag=False, minor=True)
        self.sandbox_is_changed = True
        self.t_changed = time.time()
        if self.sandbox_is_default:
        	self.t_reset = time.time()
        	self.sandbox_is_default = False
    except pywikibot.EditConflict:
        pywikibot.output(u'\03{lightyellow}Editconflict while'
                u'adding template!\03{default}')
        pass

  def reset_sandbox(self, comment=sandboxResetComment, botflag=True):
    """reset sandbox to default text, clear reset timers"""

    pywikibot.output(u'\03{lightyellow}' + time.strftime(timeformat) +\
		    u'Reseting Sandbox ...\03{default}')
    try:
        _ = self.sandboxPage.get(force=True, get_redirect=True)
        self.sandboxPage.text = sandboxDefault
        self.sandboxPage.save(comment=comment, botflag=False, minor=False)
        self.sandbox_is_changed = False
        self.sandbox_is_default = True
        pywikibot.output(u'\03{lightyellow}Done!\03{default}')
    except pywikibot.EditConflict:
        pywikibot.output(u'\03{lightyellow}Editconflict while'
                u'reseting!\03{default}')
        self.reset_sandbox(comment, botflag=False)
    except pywikibot.NoPage:
        pywikibot.output(u'\n\03{lightpurple}Sandbox does not seem do exist, '
                u'pywikibot.Nopage error.\03{default}')
	#rc watcher should take care of this, this can happen on startup
        time.sleep(20)
        self.sandbox_deleted() 

  def sandbox_deleted(self):
    """When the sandbox is deleted, we need to create a version with
    only sandbox template and one with sandbox template + text.
    Then we update the revids used by the template
    
    """
    pywikibot.output(u'\n\03{lightpurple}' + time.strftime(timeformat) +\
            u'Sandbox was deleted, creating new one\03{default}')

    #template only
    try:
        _ = self.sandboxPage.get(force=True, get_redirect=True)
        self.sandboxPage.text = sandboxTemplate
        self.sandboxPage.save(comment=sandboxDeletedComment, botflag=False, minor=False)
    except pywikibot.EditConflict: # lets do it again
        pywikibot.output(u'\03{lightpurple}EditConflict!\03{default}')
        _ = self.sandboxPage.get(force=True, get_redirect=True)
        self.sandboxPage.text = sandboxTemplate
        self.sandboxPage.save(comment=sandboxDeletedComment, botflag=False, minor=False)
    revidempty = self.sandboxPage.latestRevision()

    #reset sandbox to default
    pywikibot.output(u'\03{lightpurple}now reseting sandbox\03{default}')
    try:
        _ = self.sandboxPage.get(force=True)
        self.sandboxPage.text = sandboxDefault
        self.sandboxPage.save(comment=sandboxDeletedComment, botflag=False, minor=False)
        self.sandbox_is_changed = False
    except pywikibot.EditConflict: # lets do it again
        pywikibot.output(u'\03{lightpurple}EditConflict!\03{default}')
        _ = self.sandboxPage.get(force=True)
        self.sandboxPage.text = sandboxDefault
        self.sandboxPage.save(comment=sandboxDeletedComment, botflag=False, minor=False)
        self.sandbox_is_changed = False
    revidtext = self.sandboxPage.latestRevision()

    pywikibot.output(u'\03{lightpurple}Updating revids\03{default}')
    #update empty revid
    revIdEmptyPage = pywikibot.Page(self.site, revIdEmptyTitle)
    revIdEmptyPage.text = revIdDoku+unicode(revidempty)+revIdEmptyAddon
    revIdEmptyPage.save(comment=revIdComment, botflag=True)

    #update text revid
    revIdTextPage = pywikibot.Page(self.site, revIdTextTitle)
    revIdTextPage.text = revIdDoku+unicode(revidtext)+revIdTextAddon
    revIdTextPage.save(comment=revIdComment, botflag=True)
    
    self.sandbox_is_changed = False
    self.sandbox_is_default = True

    pywikibot.output(u'\03{lightpurple}Done! Back to normal\03{default}')

  def text_changed(self):
    """The text changed, reset sandbox to version with new text
    and update the revid used by the sandbox template"""

    pywikibot.output(u'\n\03{lightpurple}' + time.strftime(timeformat) +\
            u'Text changed, resting Sandbox, updating revision id\03{default}')
    time.sleep(1) #sometimes were are faster then mediawiki
    #reseting sandbox
    self.reset_sandbox(comment=sandboxTextComment, botflag=False)
    self.t_reset = time.time()

    #update text revid
    self.sandboxDefaultText = self.sandboxPage.get(force=True)
    revid = self.sandboxPage.latestRevision()
    revIdTextPage = pywikibot.Page(self.site, revIdTextTitle)
    revIdTextPage.text = revIdDoku+unicode(revid)+revIdTextAddon
    revIdTextPage.save(comment=revIdComment, botflag=True)
    pywikibot.output(u'\n\03{lightpurple}Text revid updated\03{default}')

    pywikibot.output(u'\n\03{lightpurple}Running MerlBot-fix...\03{default}')
    self.merlbot_fix()

  def merlbot_fix(self):
    """fix which allows dewiki:User:MerlBot to continue to reset the sandbox
    """
    page = pywikibot.Page(self.site, merlBotPage)
    page.text = sandboxDefault
    page.save(comment=sandboxTextComment, botflag=True, minor=False)

class IrcListener(irc.bot.SingleServerIRCBot):
  """Takes care of the IRC backend,
  calls IrcHander.new_event() for new rc log entries
  
  """
  def __init__(self):
    irc.bot.SingleServerIRCBot.__init__(self, [("irc.wikimedia.org", 6667)],
            pywikibot.Site().username(), u"aBotBy"+contactUser)
    irc.client.ServerConnection.buffer_class.errors = 'replace'
    self.channel = u"#"+pywikibot.Site().language()+u"."+pywikibot.Site().family.name
    self.handler = IrcHandler()

    self.start()
    
  def on_nicknameinuse(self, c, e):
    c.nick(c.get_nickname() + "_wtf")

  def on_welcome(self, c, e):
    pywikibot.output("\03{lightred}Connected to IRC!\03{default}\n")
    c.join(self.channel)

  def on_privmsg(self, c, e):
    pywikibot.output(u"\n\03{lightred}IRC: recieved privmsg from "
            +e.source.nick+u": "+e.arguments[0]+u"\03{default}")
    c.notice(e.source.nick, u"This is a brainless bot, please contact "
            +contactUser+u" on " + pywikibot.Site().language()+u"."
            +pywikibot.Site().family.name + u".org or irc.freenode.net")

  def on_pubmsg(self, c, e):
    if e.source.nick == "rc-pmtpa":
            m = e.arguments[0]
            #pywikibot.output(repr(m)) #debug
            self.handler.new_event(m)
    return

if __name__ == "__main__":
  try:
    pywikibot.output(u"\03{lightred}Connecting to IRC ...\03{default}")
    IrcListener().start()
  except KeyboardInterrupt:
    pywikibot.output("u\n\n\03{lightred}Shutting down ...\03{default}")
    pywikibot.stopme()
