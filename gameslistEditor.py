#! python

import os
import re
import shutil
import urllib
import urllib2
import codecs
import difflib
import argparse

from collections import OrderedDict
from operator import itemgetter

from xml.dom.minidom import parse, parseString

import urwid

from pprint import pprint
from functools import partial

ROMS_DIR = '//retropie/roms'

MONTHS = ['jan', 'feb', 'mar', 'apr',
          'may', 'jun', 'jul', 'aug',
          'sep', 'oct', 'nov', 'dec']

# - Generic ----------------------------------------------------

def backupFile(path):

    sp = os.path.abspath(path)
    fp, fn = os.path.split(sp)
    backupdir = os.path.join(fp, '.backup')
    if not os.path.exists(backupdir):
        os.mkdir(backupdir)

    matcher = fn + '.backup.\d+'
    backups = [f for f in os.listdir(backupdir) if re.match(matcher, f)]
    versons = []
    for b in backups:
        try:
            versons.append(int(b.split('.').pop()))
        except:
            pass

    maxVersion = max(versons) if versons else 0
    version = maxVersion + 1

    tp = os.path.join(backupdir, fn + '.backup.' + str(version))
    shutil.copyfile(sp, tp)

# - Utils ------------------------------------------------------

def readableDateToEsString(dateStr):

    dateStr = re.findall(r'[\w]+', dateStr)

    if not len(dateStr) == 3:

        print 'bad input'
        return '00010101T000000'

    mm, dd, yyyy = dateStr

    if not all([i.isdigit() for i in [dd, yyyy]]):

        print 'bad input', dd, yyyy
        return '00010101T000000'

    if not mm.isdigit():
        mm = mm[:3].lower()
        if mm in MONTHS:
            mm = str(MONTHS.index(mm) + 1).zfill(2)
        else:
            print 'bad input', mm
            return '00010101T000000'

    dd = dd.zfill(2)

    return yyyy+mm+dd + 'T000000'

def esStringToReadableDate(dateStr):

    if not dateStr:
        return ''

    dateStr = dateStr.split('T').pop(0)
    yyyy = dateStr[:4]
    mm = dateStr[4:6]
    dd = dateStr[6:8]
    return '/'.join([ mm, dd, yyyy ])

def getGamelist(system):

    return os.path.join(ROMS_DIR, system, 'gamelist.xml')

def getSystems():

    dirs = os.listdir(ROMS_DIR)
    for d in dirs:
        glpath = getGamelist(d)
        if os.path.exists(glpath):
            yield d

# - Scraper ----------------------------------------------------

class Scraper(object):

    def __init__(self, system, searchQuery, timeout=None):

        # userAgent can be anything but python apperently
        # so I told gamesdb that this is my browser
        self.userAgent = 'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0'
        self.system = system
        self.searchQuery = searchQuery
        self.timeout = timeout
        self.systemName = self.__getSystemName__(system)

    def __getSystemName__(self, system):
        systems = {
            '3do' : '3DO',
            'amiga' : 'Amiga',
            'amstradcpc' : 'Amstrad CPC',
            'arcade' : 'Arcade',
            'atari2600' : 'Atari 2600',
            'atari5200' : 'Atari 5200',
            'atari7800' : 'Atari 7800',
            'atarilynx' : 'Atari Lynx',
            'atarijaguar' : 'Atari Jaguar',
            'atarijaguarcd' : 'Atari Jaguar CD',
            'atarixe' : 'Atari XE',
            'colecovision' : 'Colecovision',
            'c64' : 'Commodore 64',
            'intellivision' : 'Intellivision',
            'macintosh' : 'Mac OS',
            'xbox' : 'Microsoft Xbox',
            'xbox360' : 'Microsoft Xbox 360',
            'neogeo' : 'NeoGeo',
            'ngp' : 'Neo Geo Pocket',
            'ngpc' : 'Neo Geo Pocket Color',
            'n3ds' : 'Nintendo 3DS',
            'n64' : 'Nintendo 64',
            'nds' : 'Nintendo DS',
            'nes' : 'Nintendo Entertainment System (NES)',
            'mame-mame4all': 'Arcade',
            'gb' : 'Nintendo Game Boy',
            'gba' : 'Nintendo Game Boy Advance',
            'gbc' : 'Nintendo Game Boy Color',
            'gc' : 'Nintendo GameCube',
            'wii' : 'Nintendo Wii',
            'wiiu' : 'Nintendo Wii U',
            'pc' : 'PC',
            'sega32x' : 'Sega 32X',
            'segacd' : 'Sega CD',
            'dreamcast' : 'Sega Dreamcast',
            'gamegear' : 'Sega Game Gear',
            'genesis' : 'Sega Genesis',
            'mastersystem' : 'Sega Master System',
            'megadrive' : 'Sega Mega Drive',
            'saturn' : 'Sega Saturn',
            'psx' : 'Sony Playstation',
            'ps2' : 'Sony Playstation 2',
            'ps3' : 'Sony Playstation 3',
            'ps4' : 'Sony Playstation 4',
            'psvita' : 'Sony Playstation Vita',
            'psp' : 'Sony PSP',
            'snes' : 'Super Nintendo (SNES)',
            'pcengine' : 'TurboGrafx 16',
            'wonderswan' : 'WonderSwan',
            'wonderswancolor' : 'WonderSwan Color',
            'zxspectrum' : 'Sinclair ZX Spectrum',
        }
        return systems.get(system)

    def __makeRequest__(self, url, request={}):

        querry = urllib.urlencode(request)
        headers = {'User-Agent' : self.userAgent}
        request = urllib2.Request(url, querry, headers=headers)
        fileObject =  urllib2.urlopen(request, timeout=self.timeout)
        return fileObject

    def __xmlValue__(self, parent, tag):

        elements = parent.getElementsByTagName(tag)
        if len(elements) > 1:
            raise RuntimeError('more than one tag for ' + tag)
        if elements:
            node = elements[0].firstChild
            return node.data if node else None

    def get_bigrams(self, string):
        '''
        Takes a string and returns a list of bigrams
        '''
        s = string.lower()
        return [s[i:i+2] for i in xrange(len(s) - 1)]

    def string_similarity(self, str1, str2):
        '''
        Perform bigram comparison between two strings
        and return a percentage match in decimal form
        '''
        pairs1 = self.get_bigrams(str1)
        pairs2 = self.get_bigrams(str2)
        union  = len(pairs1) + len(pairs2)
        hit_count = 0
        for x in pairs1:
            for y in pairs2:
                if x == y:
                    hit_count += 1
                    break
        return (2.0 * hit_count) / union

    def simplifySearchSting(self, search):

        match = re.match('(.*)\(.*\).*', search)
        search = match.group(1) if match else search

        return search

    def gameSearch(self, sort=True):

        systemName = self.systemName
        searchQuery = self.searchQuery
        searchQuery = self.simplifySearchSting(searchQuery)

        results = dict()

        url = 'http://thegamesdb.net/api/GetGamesList.php'
        querry = {
            'name': searchQuery,
            #'exactname' : searchQuery,
            'platform' : systemName,
            }
        fileObject = self.__makeRequest__(url, querry)

        # get xml results
        dom = parse(fileObject)
        for node in dom.getElementsByTagName('Game'):
            gameTitle = self.__xmlValue__(node, 'GameTitle')
            gameId = self.__xmlValue__(node, 'id')
            releasedate = self.__xmlValue__(node, 'ReleaseDate')
            results[gameTitle] = {u'gameId':gameId,
                                  u'releasedate':releasedate}

        if not sort:
            return results

        # get sorting order lookup
        skeys = list()
        for key, data in results.items():
            ss = self.string_similarity(self.searchQuery, key)
            # str(ss).ljust(15, '0'), key
            skeys.append([ss, key])

        sortedResults = list()
        for i, title in reversed(sorted(skeys, key=itemgetter(0))):
            sortedResults.append((title, results.get(title)))

        return OrderedDict(sortedResults)

    def dataSearch(self, gameID):

        url = 'http://thegamesdb.net/api/GetGame.php'
        querry = {
            'id': gameID,
            'platform' : self.systemName,
            }
        fileObject = self.__makeRequest__(url, querry)
        print fileObject.read()

# - XML Manager ------------------------------------------------

class ManageGameListXML(object):

    def __init__(self, system):

        self.changes = False
        self.xmlpath = getGamelist(system)
        self.dom = parse(self.xmlpath)
        self.gameProperties = []
        self.gameDatas = [
                'path', 'name', 'desc', 'image',
                'rating', 'releasedate',
                'developer', 'publisher', 'genre',
                'players', 'playcount', 'lastplayed',
                ]

    def __getNodeForGame__(self, game):

        for node in self.dom.getElementsByTagName('game'):
            if self.getData(node, 'name') == game:
                return node

    def setData(self, parentNode, name, value):

        if isinstance(value, str):
            value = unicode(value, errors='ignore')

        d = parentNode.getElementsByTagName(name)

        if not value:
            for item in d:
                parentNode.removeChild(item)
            return

        # value = value.encode('utf-8')

        if d:
            if d[0].childNodes:
                d[0].firstChild.data = value
            else:
                textNode = self.dom.createTextNode(value)
                d[0].appendChild(textNode)
        else:
            textNode = self.dom.createTextNode(value)
            e = self.dom.createElement(name)
            e.appendChild(textNode)
            parentNode.appendChild(e)

        self.changes = True

    def getData(self, parentNode, name):

        d = parentNode.getElementsByTagName(name)
        data = d[0].firstChild.data if d and d[0].firstChild else None
        data = data.encode('utf-8') if data else None
        return data

    def getGames(self):

        for node in self.dom.getElementsByTagName('game'):
            yield self.getData(node, 'name')

    def getDataForGame(self, gameName):

        node = self.__getNodeForGame__(gameName)
        data = dict()

        for tag in self.gameDatas:
            data[tag] = self.getData(node, tag) or u''

        return data

    def setDataForGame(self, game, properties={}):

        node = self.__getNodeForGame__(game)
        for key, value in properties.items():
            self.setData(node, key, value)
        self.changes = True

    def toxml(self):

        newXML = self.dom.toxml()
        reparsed = parseString(newXML)
        return '\n'.join([line for line in reparsed.toprettyxml(indent='    '*2).split('\n') if line.strip()])

    def writeXML(self):

        backupFile( self.xmlpath )

        xmlOutPath = '/cygdrive/d/Games/Emulation/RetroPie/gamesListEditor/test.xml'
        xmlOutPath = self.xmlpath

        with open(xmlOutPath, 'w') as f:
            f = codecs.lookup('utf-8')[3](f)
            self.dom.writexml(f, encoding='utf-8')

'''
m = ManageGameListXML('nes')
i = m.getGames()
game = i.next()
game = i.next()
game = i.next()
game = i.next()
game = i.next()
game = i.next()
game = i.next()
game = i.next()
game = i.next()
game = i.next()

s = Scraper('nes', game)
d = s.gameSearch().items()[0][1]
gameId = d.get('gameId')
s.dataSearch(gameId)
'''

'''
m = ManageGameListXML('mame-mame4all')
game = 'Choplifter'
data = m.getDataForGame(game)
pprint (data)
m.setDataForGame(game, data)
data = m.getDataForGame(game)
pprint (data)
'''

# - URWID Below ------------------------------------------------

class GameslistGUI(object):

    def __init__(self):

        self.currentSystem = None
        self.currentGame = None
        self.systems = list(getSystems())
        self.xmlManagers = dict()

        self.panelOpen = False

        # widget instances
        self.mainWidgetInstance = self.mainEditWidget()
        self.systemMenu = self.menuWidget('Game Systems', self.systems, self.systemsWidgetCallback)
        self.gamesMenu = self.menuWidget('Games')

        button = urwid.Button('test')
        button = urwid.Filler(button, height = 20)
        button = urwid.AttrMap(button, 'primaryBackground')
        button = urwid.Frame(button)

        # layout
        cwidget = urwid.Columns([self.systemMenu, self.gamesMenu])
        pwidget = urwid.Pile([
                    ('weight', 0.5, cwidget),
                    self.mainWidgetInstance,
                    (2,self.buttonsWidget()),
                    ])

        # footer
        self.footer = urwid.Text('')
        self.footer = urwid.AttrMap(self.footer, 'footerText')
        self.frameWidget = urwid.Frame(pwidget, header=None, footer=self.footer)
        self.frameWidget = self.main_shadow(self.frameWidget)

        self.body = urwid.WidgetPlaceholder(self.frameWidget)

        # do it
        self.loop = urwid.MainLoop(self.body, self.palette(), unhandled_input=self.keypress)

    def main_shadow(self, w):

        bg = urwid.AttrWrap(urwid.SolidFill(u"\u2592"), 'deepBackground')
        shadow = urwid.AttrWrap(urwid.SolidFill(u" "), 'dropShadow')

        bg = urwid.Overlay( shadow, bg,
            ('fixed left', 3), ('fixed right', 1),
            ('fixed top', 2), ('fixed bottom', 1))
        w = urwid.Overlay( w, bg,
            ('fixed left', 2), ('fixed right', 3),
            ('fixed top', 1), ('fixed bottom', 2))

        return w

    def start(self):

        self.loop.run()

    def paletteItm(self, name, fg='default', bg='default', mode=None,
                   mono=None, fghq=None, bghq=None):

        '''
        fg - foreground options:
            'white' 'black' 'brown' 'yellow'
            'dark red' 'dark green' 'dark blue'
            'dark cyan' 'dark magenta' 'dark gray'
            'light red' 'light green' 'light blue'
            'light cyan' 'light magenta' 'light gray'

        mode - foregroundSetting options:
            'bold' 'underline' 'blink' 'standout'

        bg - background options:
            'dark red' 'dark green' 'dark blue'
            'dark cyan' 'dark magenta' 'light gray'
            'black' 'brown'

        mono options:
            'bold' 'underline' 'blink' 'standout'

        fghq & bghq - foreground_high background_high example values:
            '#009' (0% red, 0% green, 60% red, like HTML colors)
            '#fcc' (100% red, 80% green, 80% blue)
            'g40'  (40% gray, decimal),
            'g#cc' (80% gray, hex),
            '#000', 'g0', ' g#00'   (black),
            '#fff', 'g100', rg#ff' (white)
            'h8'   (color number 8),
            'h255' (color number 255)
        '''

        fg = ','.join((fg, mode)) if mode else fg
        setting = (name, fg, bg, mono, fghq, bghq)
        return setting

    def palette(self):

        # color palette
        palette = [

                # for button selections
                self.paletteItm('activeButton', 'standout', mode='bold'),

                # for body text
                self.paletteItm('bodyText', 'yellow', 'dark blue', mode='bold'),

                # color for text being actively edited
                self.paletteItm('edittext', fg='white', bg='black'),

                # background color
                self.paletteItm('primaryBackground', bg='dark blue'),

                # for footer text
                self.paletteItm('footerText', fg='dark blue', bg='light gray'),

                # for drop shadow
                self.paletteItm('dropShadow', bg='black'),

                # for farmost background
                self.paletteItm('deepBackground', fg='black', bg='light gray'),

                ]

        return palette

    def exit_program(self, button=None):

        raise urwid.ExitMainLoop()

    # - utils ------------------------------------------------------------------

    def getOrMakeManager(self, system):

        xmlManager = self.xmlManagers.get(system)

        if xmlManager:
            return xmlManager
        else:
            manager = ManageGameListXML(system)
            self.xmlManagers[system] = manager
            return manager

    def saveGameXml(self):

        if not self.currentSystem:
            self.updateFooterText('no system data to update')
            return

        xmlManager = self.getOrMakeManager(self.currentSystem)

        if not xmlManager.changes:
            self.updateFooterText('no changes to save')
            return

        xmlpath = xmlManager.xmlpath
        xmlManager.writeXML()
        self.updateFooterText('wrote: ' + xmlpath)

    def updateGameXml(self):

        if not self.currentSystem:
            self.updateFooterText('no system data to update')
            return
        if not self.currentGame:
            self.updateFooterText('no changes to save')
            return

        xmlManager = self.getOrMakeManager(self.currentSystem)


        releasedate = self.releasedate.get_edit_text()
        releasedate = readableDateToEsString(releasedate)

        data = dict(
            path        = self.path.get_edit_text(),
            name        = self.name.get_edit_text(),
            image       = self.image.get_edit_text(),
            # thumbnail   = self.thumbnail.get_edit_text(),
            rating      = self.rating.get_edit_text(),
            releasedate = releasedate,
            developer   = self.developer.get_edit_text(),
            publisher   = self.publisher.get_edit_text(),
            genre       = self.genre.get_edit_text(),
            players     = self.players.get_edit_text(),
            playcount   = self.playcount.get_edit_text(),
            lastplayed  = self.lastplayed.get_edit_text(),
            desc        = self.desc.get_edit_text(),
            )
        xmlManager.setDataForGame(self.currentGame, data)

    # - Widget helpers ---------------------------------------------------------

    def updateFooterText(self, text):

        text = urwid.Text(' ' + text)
        text = urwid.AttrMap(text, 'footerText')
        self.footer.original_widget = text

    def menuButtonList(self, choices, callback=None):

        body = []
        for choice in choices:
            button = urwid.Button(choice)
            if callback:
                urwid.connect_signal(button, 'click', callback, choice)
            button = urwid.AttrMap(button, None, focus_map='activeButton')
            body.append( button )
        return body

    def field(self, var, label=None, defaultText='', multiline=False, callback=None):

        label = label or var
        label = label + ': '
        labelWidget = urwid.Text(('primaryBackground', label))
        editWidget = urwid.Edit('', defaultText, multiline=multiline)
        map = urwid.AttrMap(editWidget, 'bodyText', 'edittext')
        setattr(self, var, editWidget)

        return urwid.Columns([('pack', labelWidget), map])

    def minimalButton(self, *args, **kwargs):

        button = urwid.Button(*args, **kwargs)
        buttonText = button.get_label()
        return urwid.Padding(button, width=len(buttonText)+4)

    # - Widgets ----------------------------------------------------------------

    def menuWidget(self, title, choices=[], callback=None, padding=2):

        body = self.menuButtonList(choices, callback)
        lw = urwid.SimpleFocusListWalker(body)
        box = urwid.ListBox(lw)
        widget = urwid.Padding(box, left=padding, right=padding)
        widget = urwid.LineBox(widget, title)
        widget = urwid.AttrMap(widget, 'primaryBackground')

        return widget

    def buttonsWidget(self):

        applyButton = self.minimalButton('Save Changes')
        urwid.connect_signal(applyButton.original_widget, 'click', self.saveGameXmlCallback)

        closeButtom = self.minimalButton('Quit')
        urwid.connect_signal(closeButtom.original_widget, 'click', self.exit_program)

        body = [
            applyButton,
            closeButtom,
            ]

        gridFlow = urwid.GridFlow(body, 20, 0, 0, 'left')
        lw = urwid.SimpleFocusListWalker([gridFlow])
        box = urwid.ListBox(lw)
        widget = urwid.Padding(box, left=2, right=2)
        widget = urwid.AttrMap(widget, 'primaryBackground')

        return widget

    def emptyBoxWidget(self, title='Content Goes Here', text=''):

        text = urwid.Text(text)
        fill = urwid.Filler(text)

        widget = urwid.SolidFill()
        widget = urwid.LineBox(fill, title)
        widget = urwid.AttrMap(widget, 'primaryBackground')
        return widget

    def mainEditWidget(self):

        blank = urwid.Divider()

        body = [
            blank, self.field('path'),
            blank, self.field('name'),
            blank, self.field('image'),
            #blank, self.field('thumbnail'),
            blank, self.field('rating'),
            blank, self.field('releasedate', 'releasedate(MM/DD/YYYY)'),
            blank, self.field('developer'),
            blank, self.field('publisher'),
            blank, self.field('genre'),
            blank, self.field('players'),
            blank, self.field('playcount'),
            blank, self.field('lastplayed'),
            blank, self.field('desc', multiline=True),
            ]

        lw = urwid.SimpleFocusListWalker(body)
        box = urwid.ListBox(lw)
        widget = urwid.Padding(box, left=2, right=2)
        widget = urwid.LineBox(widget, 'Game Information')
        widget = urwid.AttrMap(widget, 'primaryBackground')

        return widget

    # - popups -----------------------------------------------------------------

    def openPopupWindow(self, widget=None, size=50):

        widget = widget or self.emptyBoxWidget()
        overlay = urwid.Overlay(
                    top_w=widget,
                    bottom_w=self.frameWidget,
                    align='center',
                    width=('relative', size),
                    valign='middle',
                    height=('relative', size),
                    min_width=None,
                    min_height=None,
                    left=-1,
                    right=0,
                    top=0,
                    bottom=0
                    )
        self.body.original_widget = overlay
        self.panelOpen = widget

    def closePopupWindow(self, *args):

        self.body.original_widget = self.frameWidget
        self.panelOpen = None

    def togglePopupWindow(self, widget=None, size=50):

        if not self.panelOpen:
            widget = self.openPopupWindow(widget=widget, size=size)
        else:
            self.closePopupWindow()

    def scraperChoices(self):

        if self.currentSystem and self.currentGame:
            title = self.currentGame
            title = title.split('(')[0] if '(' in title else title
            scr = Scraper(self.currentSystem, title)
            results = scr.gameSearch()


            menu = self.menuWidget(
                    title,
                    choices=results,
                    callback=self.scraperChoicesCallback)
            self.gameSearchResults = results
            return menu
        else:
            title = 'Nothing Selected'
            return self.emptyBoxWidget(title, '')

    # - callbacks --------------------------------------------------------------

    def keypress(self, key):

        if key in ('t', 'T'):
            popup = self.emptyBoxWidget()
            self.togglePopupWindow(popup)

        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()

        if key in ('s', 'S'):
            popup = self.scraperChoices()
            self.togglePopupWindow(popup)

    def scraperChoicesCallback(self, button, choice, data=None):

        bodyText = self.gameSearchResults

        data = bodyText.get(choice)
        date = data.get('releasedate', u'')

        oldDate = self.releasedate.get_edit_text()
        string = str(oldDate) + ' --> ' + str(date)

        self.closePopupWindow()

        response = urwid.Text(string)
        button = urwid.Button('Ok', self.scraperOkButtonAction, date)
        button2 = urwid.Button('Cancel', self.closePopupWindow)
        reversedbutton = urwid.AttrMap(button, None, focus_map='activeButton')
        reversedbutton2 = urwid.AttrMap(button2, None, focus_map='activeButton')
        pile = urwid.Pile([response, reversedbutton, reversedbutton2])
        filler = urwid.Filler(pile)
        widget = urwid.LineBox(filler, '')
        widget = urwid.AttrMap(widget, 'primaryBackground')

        # widget = self.emptyBoxWidget('', str(date))
        self.togglePopupWindow(widget)

    def scraperOkButtonAction(self, button, date):
        self.releasedate.set_edit_text(date)
        self.closePopupWindow()

    def saveGameXmlCallback(self, button):

        self.updateGameXml()
        self.saveGameXml()

    def systemsWidgetCallback(self, button, choice):

        self.updateGameXml()

        self.currentSystem = choice
        self.currentGame = None

        '''
        response = urwid.Text('You chose {} \n'.format(choice))
        button = urwid.Button('Ok')
        reversedbutton = urwid.AttrMap(button, None, focus_map='activeButton')
        pile = urwid.Pile([response, reversedbutton])
        filler = urwid.Filler(pile)
        '''

        games = self.getOrMakeManager(choice).getGames()
        self.gamesMenu.original_widget = self.menuWidget('Games', games, self.gamesWidgetCallback)
        self.updateFooterText(getGamelist(choice))

        self.path.set_edit_text('')
        self.name.set_edit_text('')
        self.image.set_edit_text('')
        # self.thumbnail.set_edit_text('')
        self.rating.set_edit_text('')
        self.releasedate.set_edit_text('')
        self.developer.set_edit_text('')
        self.publisher.set_edit_text('')
        self.genre.set_edit_text('')
        self.players.set_edit_text('')
        self.playcount.set_edit_text('')
        self.lastplayed.set_edit_text('')
        self.desc.set_edit_text('')

    def gamesWidgetCallback(self, button, choice):

        self.updateGameXml()

        self.currentGame = choice
        self.updateFooterText(self.currentSystem + ', ' + choice)

        xmlManager = self.getOrMakeManager(self.currentSystem)
        data = xmlManager.getDataForGame(choice)

        path        = data.get('path', '')
        name        = data.get('name', '')
        image       = data.get('image', '')
        # thumbnail   = data.get('thumbnail', '')
        rating      = data.get('rating', '')
        releasedate = data.get('releasedate', '')
        developer   = data.get('developer', '')
        publisher   = data.get('publisher', '')
        genre       = data.get('genre', '')
        players     = data.get('players', '')
        playcount   = data.get('playcount', '')
        lastplayed  = data.get('lastplayed', '')
        desc        = data.get('desc', '')

        releasedate = esStringToReadableDate(releasedate)

        self.path.set_edit_text(path)
        self.name.set_edit_text(name)
        self.image.set_edit_text(image)
        # self.thumbnail.set_edit_text(thumbnail)
        self.rating.set_edit_text(rating)
        self.releasedate.set_edit_text(releasedate)
        self.developer.set_edit_text(developer)
        self.publisher.set_edit_text(publisher)
        self.genre.set_edit_text(genre)
        self.players.set_edit_text(players)
        self.playcount.set_edit_text(playcount)
        self.lastplayed.set_edit_text(lastplayed)
        self.desc.set_edit_text(desc)

# - Alternate Colors -------------------------------------------------------

class GreenTheme(GameslistGUI):
    def palette(self):

        # color palette
        palette = [

                # for button selections
                self.paletteItm('activeButton', 'light green', bg='black', mode='standout'),

                # for body text
                self.paletteItm('bodyText', 'dark green', 'black', mode='bold'),

                # color for text being actively edited
                self.paletteItm('edittext', fg='light green', bg='black', mode='bold'),

                # background color
                self.paletteItm('primaryBackground', fg='dark green', bg='black'),

                # for footer text
                self.paletteItm('footerText', 'dark green', bg='black', mode='standout'),

                # for drop shadow
                self.paletteItm('dropShadow', bg='black'),

                # for farmost background
                self.paletteItm('deepBackground', fg='dark green', bg='black'),

                ]

        return palette

class GrayTheme(GameslistGUI):
    def palette(self):
        # color palette
        palette = [

                # for button selections
                self.paletteItm('activeButton', 'dark cyan', bg='black', mode='standout'),

                # for body text
                self.paletteItm('bodyText', 'black', bg='light gray', mode='bold'),

                # color for text being actively edited
                self.paletteItm('edittext', fg='black', bg='light gray', mode='bold'),

                # background color
                self.paletteItm('primaryBackground', fg='black', bg='light gray'),

                # for footer text
                self.paletteItm('footerText', mode='standout'),

                # for drop shadow
                self.paletteItm('dropShadow', bg='black'),

                # for farmost background
                self.paletteItm('deepBackground', fg='black', bg='light blue'),

                ]

        return palette

def parseArgs():
    desc = 'Tool to edit gamelist.xml files'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-th',
                    help='green or gray')

    args = parser.parse_args()
    return args

if __name__ == '__main__':

    theme = parseArgs().th
    if theme == 'green':
        GreenTheme().start()
    elif theme == 'gray':
        GrayTheme().start()
    else:
        GameslistGUI().start()


