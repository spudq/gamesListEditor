#! python

# - Imports -------------------------------------------------------------------
import os
import shutil
import urwid

from pprint import pprint

from xml.dom.minidom import parse, parseString, Document

# - User Settings -------------------------------------------------------------

ROMS_TARGET_DIR = '//retropie/roms/mame-libretro'
ROMS_SOURCE_DIR = '/cygdrive/d/Games/Emulation/romSets/mame/MAME2003_Reference_Set_MAME0.78_ROMs_CHDs_Samples/roms'
DAT_FILE = r'\\retropie\roms\mame-libretro\MAME 078.dat'

# - Stuffs --------------------------------------------------------------------

def pathSplit(path):

    fp, fn = os.path.split(path)
    bn, ext = os.path.splitext(fn)
    return fp, bn, ext

def gameTitlesFromDat():

    print 'Parsing:', DAT_FILE

    # get game names from .dat file
    datData = dict()
    for gameTag in parse(DAT_FILE).getElementsByTagName('game'):
        if gameTag.hasAttribute('name'):
            name = gameTag.getAttribute('name')
            subTag = gameTag.getElementsByTagName('description')
            if not subTag:
                continue
            datData.setdefault(name, {})
            datData[name]['gameName'] = subTag[0].firstChild.data

    return datData

class CopyGamesGui(object):

    def __init__(self):

        self.gameData = gameTitlesFromDat() 

        sourceRoms = self.getGames(ROMS_SOURCE_DIR)
        targetRoms = self.getGames(ROMS_TARGET_DIR)

        self.romList = [(i, i in targetRoms) for i in sourceRoms]

        self.createCheckboxes(self.romList)

        self.chooserWidget = self.menuWidget('Source Roms', self.romList)

        self.body = urwid.WidgetPlaceholder(self.chooserWidget)

        self.filterWidget = urwid.Edit(u'', u'', multiline=False)
        urwid.connect_signal(self.filterWidget, 'change', self.filterButtonAction)

        editWidget = urwid.Filler(self.filterWidget)

        pwidget = urwid.Pile([
                    (1, editWidget),
                    self.body,
                    (2, self.buttonsWidget()),
                    ])

        # footer
        self.footer = urwid.Text('')
        self.footer = urwid.AttrMap(self.footer, 'footerText')
        self.frameWidget = urwid.Frame(
                pwidget, header=None, footer=self.footer)
        self.frameWidget = self.main_shadow(self.frameWidget)

        self.mainwidget = urwid.WidgetPlaceholder(self.frameWidget)

        # do it
        self.loop = urwid.MainLoop(
                self.mainwidget,
                self.palette(),
                unhandled_input=self.keypress
                )
        self.loop.run()

    def filterButtonAction(self, button, *args):

        roms = list()
        for rom in self.romList:
            text = self.filterWidget.get_edit_text()
            if text.lower() in self.getLabel(rom[0]).lower():
                roms.append(rom)
        self.chooserWidget = self.menuWidget('Source Roms', roms)
        self.body.original_widget = self.chooserWidget

    def buttonsWidget(self):

        body = [urwid.Button('Do It', self.doIt)]
        gridFlow = urwid.GridFlow(body, 10, 2, 0, 'left')
        lw = urwid.SimpleFocusListWalker([gridFlow])
        box = urwid.ListBox(lw)
        widget = urwid.Padding(box, left=2, right=2)
        widget = urwid.AttrMap(widget, 'bodyColor')
        return widget

    def doIt(self, *args):

        targets = os.listdir(ROMS_TARGET_DIR)

        self.loop.screen.stop()
        for title, checkbox in self.checkboxes.items():
            filename = checkbox.filename
            checked = checkbox.state
            source = os.path.join(ROMS_SOURCE_DIR, filename)
            target = os.path.join(ROMS_TARGET_DIR, filename)

            if checked:
                if not filename in targets:
                    print 'cp', filename, ROMS_TARGET_DIR
                    shutil.copyfile(source, target)
            else:
                if filename in targets:
                    print 'rm', target
                    os.remove(target)

        raise urwid.ExitMainLoop()

    # - callbacks -------------------------------------------------------------

    def keypress(self, key):

        if key in ('f10', 'q', 'Q'):
            self.quit()
        else:
            self.updateFooterText(str(key))

    # - Widgets ---------------------------------------------------------------

    def getLabel(self, gameFile):
        path, fn, fext = pathSplit(gameFile)
        fileName = self.gameData.get(fn, {}).get('gameName', fn)
        return fileName + ', ' + fn

    def getGames(self, path):

        return [f for f in os.listdir(path) if f.endswith('.zip')]

    def main_shadow(self, widget):

        bg = urwid.AttrWrap(urwid.SolidFill(u"\u2592"), 'deepBackground')
        shadow = urwid.AttrWrap(urwid.SolidFill(u" "), 'dropShadow')

        bg = urwid.Overlay(
            shadow, bg,
            ('fixed left', 3), ('fixed right', 1),
            ('fixed top', 2), ('fixed bottom', 1))
        widget = urwid.Overlay(
            widget, bg,
            ('fixed left', 2), ('fixed right', 3),
            ('fixed top', 1), ('fixed bottom', 2))

        return widget

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
            self.paletteItm('bodyColor', bg='dark blue'),
            # for footer text
            self.paletteItm('footerText', fg='dark blue', bg='light gray'),
            # for drop shadow
            self.paletteItm('dropShadow', bg='black'),
            # for farmost background
            self.paletteItm('deepBackground', fg='black', bg='light gray'),
            ]

        return palette

    def quit(self, button=None):

        raise urwid.ExitMainLoop()

    # - Widget helpers --------------------------------------------------------

    def updateFooterText(self, text):

        text = urwid.Text(' ' + text)
        text = urwid.AttrMap(text, 'footerText')
        self.footer.original_widget = text

    def createCheckboxes(self, choices):

        self.checkboxes = dict()
        for choice, state in choices:
            label = self.getLabel(choice)
            checkbox = urwid.CheckBox(label, state=state)
            checkbox.filename = choice
            self.checkboxes.setdefault(choice, checkbox)

    def lineBoxWrap(self, widget, title, padding=2, attrMap='bodyColor'):

        widget = urwid.Padding(widget, left=padding, right=padding)
        widget = urwid.LineBox(widget, title)
        widget = urwid.AttrMap(widget, 'bodyColor')
        return widget

    # - Widgets ---------------------------------------------------------------

    def menuWidget(self, title, choices=[], callback=None):

        # body = self.menuButtonList(choices, callback)

        body = []
        for choice, state in choices:
            checkbox = self.checkboxes[choice]
            body.append(checkbox)

        lw = urwid.SimpleFocusListWalker(body)
        box = urwid.ListBox(lw)
        # widget = self.lineBoxWrap(box, title)
        widget = urwid.Padding(box, left=2, right=2)
        widget = urwid.LineBox(widget, title)
        widget = urwid.AttrMap(widget, 'bodyColor')

        return widget

if __name__ == '__main__':

    CopyGamesGui()

#
