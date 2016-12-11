#! python



import os
from xml.dom.minidom import parse, parseString

import urwid

from pprint import pprint

ROMS_DIR = '//retropie/roms'


def readableDateToEsString(dateStr):
    pass

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

class ManageGameXML(object):

    def __init__(self, system):

        self.xmlpath = getGamelist(system)
        self.dom = parse(self.xmlpath)
        self.gameProperties = []

    def getData(self, parentNode, name):

        d = parentNode.getElementsByTagName(name)
        return d[0].firstChild.data if d and d[0].firstChild else None
        #return d[0].firstChild.data if d else None

    def getGames(self):

        for node in self.dom.getElementsByTagName('game'):
            yield self.getData(node, 'name') or self.getData(node, 'path')

    def getDataForGame(self, gameName):

        for node in self.dom.getElementsByTagName('game'):
            if gameName in [self.getData(node, 'name'),
                            self.getData(node, 'path')]:

                data = dict()
                data['path']        = self.getData(node, 'path') or 'MISSING FROM XML'
                data['name']        = self.getData(node, 'name') or 'MISSING FROM XML'
                data['desc']        = self.getData(node, 'desc') or 'MISSING FROM XML'
                data['image']       = self.getData(node, 'image') or 'MISSING FROM XML'
                data['rating']      = self.getData(node, 'rating') or 'MISSING FROM XML'
                data['releasedate'] = self.getData(node, 'releasedate') or 'MISSING FROM XML'
                data['developer']   = self.getData(node, 'developer') or 'MISSING FROM XML'
                data['publisher']   = self.getData(node, 'publisher') or 'MISSING FROM XML'
                data['genre']       = self.getData(node, 'genre') or 'MISSING FROM XML'

                return data

    def setDataForGame(self, prop, value):
        pass

# - URWID Below ------------------------------------------------

class GameslistGUI(object):

    def __init__(self):

        # get systems that have gameslists
        self.systems = list(getSystems())

        # parse the xml files
        # for now parse them all up front
        # i can't decide if i want
        # to do it all at once or defered
        # right now it's really slow
        self.xmlManagers = dict()
        for system in self.systems:
            domWrap = ManageGameXML(system)
            self.xmlManagers[system] = domWrap

        # widget instances
        self.mainWidgetInstance = self.mainEditWidget()
        self.systemMenu = self.menuWidget(
                'Roms/Systems',
                self.systems,
                self.systemsWidgetCallback
                )
        self.gamesMenu = self.menuWidget('Games')

        # layout
        cwidget = urwid.Columns([self.systemMenu, self.gamesMenu])
        pwidget = urwid.Pile([('weight', 0.5, cwidget), self.mainWidgetInstance])

        self.footer = urwid.Text('')
        self.footer = urwid.AttrMap(self.footer, 'infotext')
        # self.progress = urwid.ProgressBar('reversed', 'background', current=0, total=len(self.systems))

        self.frameWidget = urwid.Frame(pwidget, header=None, footer=self.footer)

        # do it
        self.loop = urwid.MainLoop(
                self.frameWidget,
                self.getPalette(),
                unhandled_input=self.keypress
                )
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

    # - Widget helpers ---------------------------------------------------------

    def updateFooterText(self, text):

        text = urwid.Text(' ' + text)
        text = urwid.AttrMap(text, 'infotext')
        self.footer.original_widget = text

    def menuButtonList(self, choices, callback=None):

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
        applyButton = urwid.Button(buttonText)
        applyButton = urwid.AttrMap(applyButton, None, 'reversed')
        applyButton = urwid.Padding(applyButton, width=len(buttonText)+4)


        body = [
            blank, self.field('path'),
            blank, self.field('name'),
            blank, self.field('image'),
            blank, self.field('rating'),
            blank, self.field('releasedate'),
            blank, self.field('developer'),
            blank, self.field('publisher'),
            blank, self.field('genre'),
            blank, self.field('desc', multiline=True),
            blank, applyButton,
            ]

        lw = urwid.SimpleFocusListWalker(body)
        box = urwid.ListBox(lw)
        widget = urwid.Padding(box, left=2, right=2)
        widget = urwid.LineBox(widget, 'Game Information')
        widget = urwid.AttrMap(widget, 'background')

        return widget

    # - callbacks --------------------------------------------------------------

    def systemsWidgetCallback(self, button, choice):

        self.currentSystem = choice
        self.currentGame = None

        response = urwid.Text('You chose {} \n'.format(choice))
        button = urwid.Button('Ok')

        reversedbutton = urwid.AttrMap(button, None, focus_map='reversed')
        pile = urwid.Pile([response, reversedbutton])
        filler = urwid.Filler(pile)

        games = self.xmlManagers[choice].getGames()
        self.gamesMenu.original_widget = self.menuWidget('Games', games, self.gamesWidgetCallback)
        self.updateFooterText(getGamelist(choice))

        self.path.set_edit_text('')
        self.name.set_edit_text('')
        self.image.set_edit_text('')
        self.rating.set_edit_text('')
        self.releasedate.set_edit_text('')
        self.developer.set_edit_text('')
        self.publisher.set_edit_text('')
        self.genre.set_edit_text('')
        self.desc.set_edit_text('')

    def gamesWidgetCallback(self, button, choice):

        self.currentGame = choice
        self.updateFooterText(self.currentSystem + ', ' + choice)

        xmlManager = self.xmlManagers[self.currentSystem]
        data = xmlManager.getDataForGame(choice)

        path        = data.get('path', '')
        name        = data.get('name', '')
        image       = data.get('image', '')
        rating      = data.get('rating', '')
        releasedate = data.get('releasedate', '')
        developer   = data.get('developer', '')
        publisher   = data.get('publisher', '')
        genre       = data.get('genre', '')
        desc        = data.get('desc', '')

        releasedate = esStringToReadableDate(releasedate)

        self.path.set_edit_text(path)
        self.name.set_edit_text(name)
        self.image.set_edit_text(image)
        self.rating.set_edit_text(rating)
        self.releasedate.set_edit_text(releasedate)
        self.developer.set_edit_text(developer)
        self.publisher.set_edit_text(publisher)
        self.genre.set_edit_text(genre)
        self.desc.set_edit_text(desc)

glg = GameslistGUI()


