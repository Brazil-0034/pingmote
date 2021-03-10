'''
pingmote: a cross-platform Python global emote picker to quickly insert custom images/gifs

Author: David Chen
'''
import PySimpleGUI as sg
import json
import pyperclip
import keyboard
import os
from pathlib import Path
from time import sleep
from math import ceil
from pynput.mouse import Controller as MouseController


# CONFIGS

SHORTCUT = 'ctrl+q'
KILL_SHORTCUT = 'alt+shift+k'
# main path is the pingmote directory (containing pingmote.py)
MAIN_PATH = Path(__file__).parent
IMAGE_PATH = MAIN_PATH / 'assets' / 'resized'
NUM_COLS = 12  # max number of images per row in picker
SHOW_FREQUENTS = True  # show the frequents section at the topaaaa
NUM_FREQUENT = 12  # max number of images to show in the frequent section
SHOW_LABELS = True  # show section labels (frequents, static, gifs)
SEPARATE_GIFS = True  # separate static emojis and gifs into different sections

AUTO_PASTE = True  # if True, automatically pastes the image after selection
# if True and AUTO_PASTE is True, hits enter after pasting (useful in Discord)
AUTO_ENTER = True
# if True and AUTO_PASTE is True, will paste without affecting clipboard
# NOTE: this pastes with pynput and can be unreliable; SLEEP_TIME might need to be set
# or else the beginning of the URL might get cut off
PRESERVE_CLIPBOARD = False

# ADDITIONAL CONFIGS

# top left corner of emote picker, (0, 0) is screen top left
WINDOW_LOCATION = None  # if set to None, will open the GUI near the mouse cursor
# if pasting or enter isn't working, add a short delay (in seconds)
SLEEP_TIME = 0
GUI_BG_COLOR = '#36393F'  # copied from discord colors


class PingMote():

    def __init__(self):
        # Load frequencies from json for frequents section
        self.frequencies = self.load_frequencies()
        self.frequents = self.get_frequents(self.frequencies)

        # Load links and file paths
        self.filename_to_link = self.load_links()

        # Setup
        self.hidden = True
        self.setup_hardware()
        keyboard.hook(self.custom_hotkey)
        self.setup_gui()
        self.create_window_gui()

    def setup_gui(self):
        sg.theme('LightBrown1')  # Use this as base theme
        # Set location for where the window opens, (0, 0) is top left
        sg.SetOptions(button_color=(GUI_BG_COLOR, GUI_BG_COLOR), background_color=GUI_BG_COLOR,
                      text_element_background_color=GUI_BG_COLOR, text_color='white', border_width=0)
        self.layout_gui()

    def layout_gui(self):
        """ Layout GUI with PySimpleGui """
        print('loading layout...')
        self.layout = []
        if SHOW_FREQUENTS:
            if SHOW_LABELS:
                self.layout.append([sg.Text('Frequently Used'),
                                    sg.Button('Hide', button_color=('black', 'orange'))])
            self.layout.append([sg.HorizontalSeparator()])
            self.layout += self.layout_frequents_section()
        self.layout += self.layout_main_section()
        self.window = sg.Window('Emote Picker', self.layout, location=self.find_window_location(
        ), keep_on_top=True, no_titlebar=True, grab_anywhere=True, finalize=True)
        self.window.hide()
        print('ready - window created and hidden')

    def layout_frequents_section(self):
        """ Return a list of frequent emotes """
        return self.list_to_table([
            sg.Button('', key=img_name, image_filename=IMAGE_PATH /
                      img_name, image_subsample=2)
            for img_name in self.frequents
        ])

    def layout_main_section(self):
        """ Return a list of main section emotes.
        If SEPARATE_GIFS is True, split into static and emoji sections
        """
        main_section = []
        statics, gifs = [], []
        for img in sorted(IMAGE_PATH.iterdir()):
            if SHOW_FREQUENTS and img.name in self.frequents:  # don't show same image in both sections
                continue
            button = sg.Button(
                '', key=img.name, image_filename=img, image_subsample=2)
            if SEPARATE_GIFS:
                if img.suffix == '.png':
                    statics.append(button)
                else:  # gif
                    gifs.append(button)
            else:
                main_section.append(button)
        if SEPARATE_GIFS:
            combined = []
            if SHOW_LABELS:
                combined.append([sg.Text('Images')])
                combined.append([sg.HorizontalSeparator()])
            combined += self.list_to_table(statics)
            if SHOW_LABELS:
                combined.append([sg.Text('GIFs')])
            combined.append([sg.HorizontalSeparator()])
            combined += self.list_to_table(gifs)
            return combined

        return self.list_to_table(main_section)

    def create_window_gui(self):
        """ Create the window from layout """
        # Event loop
        while True:
            event, _ = self.window.read(timeout=100, timeout_key='timeout')
            if event == sg.WINDOW_CLOSED:
                break
            elif event == 'timeout':
                continue
            elif event == 'Hide':
                self.window.hide()
                self.hidden = True
            else:
                self.on_select(event)

        self.window.close()

    def on_select(self, event):
        """ Paste selected image non-destructively (if auto paste is True) """
        self.window.hide()

        if AUTO_PASTE:
            if PRESERVE_CLIPBOARD:  # write text with pynput
                self.paste_selection(event)
            else:  # copy to clipboard then paste
                self.copy_to_clipboard(event)
                self.paste_link()
            if AUTO_ENTER:
                self.keyboard_enter()
        else:
            self.copy_to_clipboard(event)

        self.update_frequencies(event)  # update count for chosen image

    def copy_to_clipboard(self, filename):
        """ Given an an image, copy the image link to clipboard """
        pyperclip.copy(self.filename_to_link[filename])

    def paste_selection(self, filename):
        keyboard.write(self.filename_to_link[filename])

    def paste_link(self):
        """ Press ctrl + v to paste """
        sleep(SLEEP_TIME)  # wait a bit if needed
        keyboard.send('ctrl+v')

    def keyboard_enter(self):
        """ Hit enter on keyboard to send pasted link """
        sleep(SLEEP_TIME)
        keyboard.send('enter')

    def update_frequencies(self, filename):
        """ Increment chosen image's counter in frequencies.json """
        if filename not in self.frequencies:
            self.frequencies[filename] = 0
        self.frequencies[filename] += 1
        self.write_frequencies(self.frequencies)
        self.frequents = self.get_frequents(
            self.frequencies)  # update frequents list

    def find_window_location(self):
        """ Open the window near where the mouse currently is """
        if WINDOW_LOCATION:  # use user provided location
            return WINDOW_LOCATION
        mouse_x, mouse_y = self.mouse.position
        # open window with the mouse cursor somewhere in the middle, near top left (since top left is most frequent)
        return (mouse_x - 400, mouse_y - 300)

    def load_links(self):
        """ Load image links from links.txt """
        with open(MAIN_PATH / 'assets' / 'links.txt') as f:
            links = f.read().splitlines()
            return {link.rsplit('/', 1)[-1]: link for link in links}

    def load_frequencies(self):
        """ Load the frequencies dictionary from frequencies.json """
        with open(MAIN_PATH / 'assets' / 'frequencies.json', 'r') as f:
            return json.load(f)

    def write_frequencies(self, frequencies):
        """ Write new frequencies to frequencies.json """
        with open(MAIN_PATH / 'assets' / 'frequencies.json', 'w') as f:
            json.dump(frequencies, f, indent=4)

    def get_frequents(self, frequencies):
        """ Get the images used most frequently """
        # sort in descending order by frequency
        desc_frequencies = sorted(
            frequencies.items(), key=lambda x: x[-1], reverse=True)
        return [img for img, _ in desc_frequencies[:NUM_FREQUENT]]

    def list_to_table(self, a, num_cols=NUM_COLS):
        """ Given a list a, convert it to rows and columns
            ex) a = [1, 2, 3, 4, 5], num_cols = 2
            returns: [[1, 2], [3, 4], [5]]
            """
        return [a[i * num_cols:i * num_cols + num_cols] for i in range(ceil(len(a) / num_cols))]

    def setup_hardware(self):
        """ Create mouse controller, setup hotkeys """
        self.mouse = MouseController()
        # keyboard.add_hotkey(SHORTCUT, self.on_activate)
        # keyboard.add_hotkey(KILL_SHORTCUT, self.kill_all)
        self.hotkeys = {
            SHORTCUT: self.on_activate,
            KILL_SHORTCUT: self.kill_all,
        }

    def custom_hotkey(self, event):
        for hotkey, func in self.hotkeys.items():
            pressed = all(
                keyboard.is_pressed(split_val) != False
                for split_val in hotkey.split('+')
            )

            if pressed:
                func()

    def on_activate(self):
        """ When hotkey is activated, toggle the GUI """
        if self.hidden:
            self.window.un_hide()
            self.hidden = False
        else:
            self.window.hide()
            self.hidden = True

    def kill_all(self):
        """ Kill the script in case it's frozen or buggy """
        print('exit program')
        self.window.close()
        os._exit(1)  # exit the entire program


if __name__ == '__main__':
    pingmote = PingMote()
