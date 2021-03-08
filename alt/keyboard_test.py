import keyboard
import chime


def customHotkey(event):
    for hotkey, func in hotkeys.items():
        pressed = all(
            keyboard.is_pressed(split__value) != False
            for split__value in hotkey.split('+')
        )

        if pressed:
            # do some actions
            print(pressed, func)
            func()
            chime.success()


def print_stuff():
    print('print stuff')


hotkeys = {
    "alt+w": print_stuff
}


keyboard.hook(customHotkey)
keyboard.wait('esc')
