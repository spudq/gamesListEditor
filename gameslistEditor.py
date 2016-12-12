#! python

import os
import re
import shutil
from xml.dom.minidom import parse, parseString

import urwid

from pprint import pprint

ROMS_DIR = '//retropie/roms'

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

    dateStr = re.sub('\D' , '', dateStr)

    if not len(dateStr) == 8 or not dateStr.isdigit():
        print 'bad input'
        return '00010101T000000'

    return dateStr + 'T000000'

def esStringToReadableDate(dateStr):

    if not len(dateStr) == 15:
        return dateStr

    yyyy = dateStr[:4]
    mm = dateStr[4:6]
    dd = dateStr[6:8]

    return '/'.join([ yyyy, mm, dd ])

def getGamelist(system):

    return os.path.join(ROMS_DIR, system, 'gamelist.xml')

def getSystems():

    dirs = os.listdir(ROMS_DIR)
    for d in dirs:
        glpath = getGamelist(d)
        if os.path.exists(glpath):
            yield d

# - XML Manager ------------------------------------------------

class ManageGameXML(object):

    def __init__(self, system):

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

        d = parentNode.getElementsByTagName(name)

        if not value:
            for item in d:
                parentNode.removeChild(item)
            return

        if d:
            # print dir(d[0])
            d[0].firstChild.data = str(value)
        else:
            textNode = self.dom.createTextNode(str(value))
            e = self.dom.createElement(name)
            e.appendChild(textNode)
            parentNode.appendChild(e)

    def getData(self, parentNode, name):

        d = parentNode.getElementsByTagName(name)
        return d[0].firstChild.data if d and d[0].firstChild else None

    def getGames(self):

        for node in self.dom.getElementsByTagName('game'):
            yield self.getData(node, 'name')

    def getDataForGame(self, gameName):

        node = self.__getNodeForGame__(gameName)
        data = dict()

        for tag in self.gameDatas:
            data[tag] = self.getData(node, tag) or ''

        return data

    def setDataForGame(self, game, properties={}):

        node = self.__getNodeForGame__(game)
        for key, value in properties.items():
            self.setData(node, key, value)

    def toxml(self):

        newXML = self.dom.toxml()
        reparsed = parseString(newXML)
        return '\n'.join([line for line in reparsed.toprettyxml(indent='    '*2).split('\n') if line.strip()])

    def writeXML(self):

        backupFile( self.xmlpath )
        f = open(self.xmlpath, 'w')
        f.write(self.toxml())
        f.close()

# - URWID Below ------------------------------------------------

class GameslistGUI(object):

    def __init__(self):

        # get systems that have gameslists
        self.systems = list(getSystems())
        # xml parse objects
        self.xmlManagers = dict()

        # widget instances
        self.mainWidgetInstance = self.mainEditWidget()
        self.systemMenu = self.menuWidget('Roms/Systems', self.systems, self.systemsWidgetCallback)
        self.gamesMenu = self.menuWidget('Games')

        # layout
        cwidget = urwid.Columns([self.systemMenu, self.gamesMenu])
        pwidget = urwid.Pile([('weight', 0.5, cwidget), self.mainWidgetInstance])

        # footer
        self.footer = urwid.Text('')
        self.footer = urwid.AttrMap(self.footer, 'infotext')
        self.frameWidget = urwid.Frame(pwidget, header=None, footer=self.footer)

        # do it
        self.loop = urwid.MainLoop(self.frameWidget, self.getPalette(), unhandled_input=self.keypress)

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

    def getPalette(self):

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

        '''

        # color palette
        palette = [

                # for button selections
                self.paletteItm('reversed', 'standout', mode='bold'),

                # for body text
                self.paletteItm('textItem', 'yellow', 'dark blue', mode='bold'),

                # background color
                self.paletteItm('background', bg='dark blue'),

                # for footer text
                self.paletteItm('infotext', fg='light blue', bg='light gray'),

                # color for text being actively edited
                self.paletteItm('edittext', fg='white', bg='black'),

                ]

        return palette

    def exit_program(self, button):

        raise urwid.ExitMainLoop()

    # - utils ------------------------------------------------------------------

    def keypress(self, key):

        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()

    def getOrMakeManager(self, system):

        xmlManager = self.xmlManagers.get(system)

        if xmlManager:
            return xmlManager
        else:
            manager = ManageGameXML(system)
            self.xmlManagers[system] = manager
            return manager

    # - Widget helpers ---------------------------------------------------------

    def updateFooterText(self, text):

        text = urwid.Text(' ' + text)
        text = urwid.AttrMap(text, 'infotext')
        self.footer.original_widget = text

    def menuButtonList(self, choices, callback=None):

        # editWidget = urwid.Edit('', '', multiline=False)

        body = []
        for choice in choices:
            button = urwid.Button(choice)
            if callback:
                urwid.connect_signal(button, 'click', callback, choice)
            button = urwid.AttrMap(button, None, focus_map='reversed')
            body.append( button )
        return body

    def field(self, var, label=None, defaultText='', multiline=False):

        label = label or var
        label = label + ': '
        labelWidget = urwid.Text(('background', label))

        editWidget = urwid.Edit('', defaultText, multiline=multiline)
        map = urwid.AttrMap(editWidget, 'textItem', 'edittext')

        setattr(self, var, editWidget)

        buttonText = 'x'
        clearButton = urwid.Button(buttonText)
        clearButton = urwid.AttrMap(clearButton, None, 'reversed')
        clearButton = urwid.Padding(clearButton, width=len(buttonText)+4)

        return urwid.Columns([
            ('pack', labelWidget),
            map
            ])

    # - Widgets ----------------------------------------------------------------

    def menuWidget(self, title, choices=[], callback=None, padding=2):

        body = self.menuButtonList(choices, callback)
        lw = urwid.SimpleFocusListWalker(body)
        box = urwid.ListBox(lw)
        widget = urwid.Padding(box, left=padding, right=padding)
        widget = urwid.LineBox(widget, title)
        widget = urwid.AttrMap(widget, 'background')

        return widget

    def emptyBoxWidget(self):

        widget = urwid.SolidFill()
        widget = urwid.LineBox(widget, 'Content Goes in here')
        widget = urwid.AttrMap(widget, 'background')
        return widget

    def mainEditWidget(self):

        blank = urwid.Divider()

        buttonText = 'Apply Changes'
        button = urwid.Button(buttonText)
        applyButton = urwid.AttrMap(button, None, 'reversed')
        applyButton = urwid.Padding(applyButton, width=len(buttonText)+4)
        urwid.connect_signal(button, 'click', self.saveGameXmlCallback)

        body = [
            blank, applyButton,
            blank, self.field('path'),
            blank, self.field('name'),
            blank, self.field('image'),
            #blank, self.field('thumbnail'),
            blank, self.field('rating'),
            blank, self.field('releasedate', 'releasedate(YYYY/MM/DD)'),
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
        widget = urwid.AttrMap(widget, 'background')

        return widget

    # - callbacks --------------------------------------------------------------

    def saveGameXmlCallback(self, button):

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
        xmlpath = xmlManager.xmlpath
        xmlManager.writeXML()
        self.updateFooterText('wrote: ' + xmlpath)

    def systemsWidgetCallback(self, button, choice):

        self.currentSystem = choice
        self.currentGame = None

        response = urwid.Text('You chose {} \n'.format(choice))
        button = urwid.Button('Ok')

        reversedbutton = urwid.AttrMap(button, None, focus_map='reversed')
        pile = urwid.Pile([response, reversedbutton])
        filler = urwid.Filler(pile)

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

if __name__ == '__main__':
    glg = GameslistGUI().start()


