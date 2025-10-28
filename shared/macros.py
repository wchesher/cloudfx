# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: © 2024 William C. Chesher <wchesher@gmail.com>
#
# CloudFX Shared Macros - MASTER COPY
# =====================================
# This is the SINGLE SOURCE OF TRUTH for macro definitions.
# Both MacroPad and FunHouse use this same file.
#
# DEPLOYMENT:
# When deploying to a device, copy this file to the device root:
#   - For MacroPad: Copy to CIRCUITPY/macros.py
#   - For FunHouse: Copy to CIRCUITPY/macros.py
#
# Each macro maps a label (command name) to a sequence of HID keycodes.
#
# Format:
# {
#     "label": "command_name",  # Must match commands sent to AdafruitIO feed
#     "keycodes": [Keycode.X, Keycode.Y, ...]  # Key sequence to send
# }

from adafruit_hid.keycode import Keycode

class Macros:
    macros = [

        #SOUND OFF

        {
            "label": "off",
            "color": 0x000000,
            "keycodes": [Keycode.LEFT_SHIFT, Keycode.ESCAPE],
            "page": 0,
            "position": 0,
            "sound": None,
            "type": "control"
        },
        #**********************************************
        #EFFECTS
        {
            "label": "dj",
            "color": 0x17A398,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.F13],
            "page": 0,
            "position": 0,
            "sound": "dj.wav",
            "type": "sound"
        },
        {
            "label": "criket",
            "color": 0x17A398,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.F14],
            "page": 0,
            "position": 1,
            "sound": "criket.wav",
            "type": "sound"
        },
        {
            "label": "outro",
            "color": 0x17A398,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.F15],
            "page": 0,
            "position": 2,
            "sound": "outro.wav",
            "type": "sound"
        },
        {
            "label": "awww",
            "color": 0x17A398,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.F16],
            "page": 0,
            "position": 3,
            "sound": "awww.wav",
            "type": "sound"
        },
        {
            "label": "bass",
            "color": 0x17A398,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.F17],
            "page": 0,
            "position": 4,
            "sound": "bass.wav",
            "type": "sound"
        },
        {
            "label": "dundun",
            "color": 0x17A398,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.F18],
            "page": 0,
            "position": 5,
            "sound": "dundun.wav",
            "type": "sound"
        },
        {
            "label": "legoda",
            "color": 0x17A398,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.F19],
            "page": 0,
            "position": 6,
            "sound": "legoda.wav",
            "type": "sound"
        },
        {
            "label": "oooff",
            "color": 0x17A398,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.F20],
            "page": 0,
            "position": 7,
            "sound": "oooff.wav",
            "type": "sound"
        },
        {
            "label": "drama",
            "color": 0x17A398,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.F21],
            "page": 0,
            "position": 8,
            "sound": "drama.wav",
            "type": "sound"
        },
        {
            "label": "buzzer",
            "color": 0x17A398,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.F22],
            "page": 0,
            "position": 9,
            "sound": "buzzer.wav",
            "type": "sound"
        },
        {
            "label": "ding",
            "color": 0x17A398,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.F23],
            "page": 0,
            "position": 10,
            "sound": "ding.wav",
            "type": "sound"
        },
        {
            "label": "bruh",
            "color": 0x17A398,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.F24],
            "page": 0,
            "position": 11,
            "sound": "bruh.wav",
            "type": "sound"
        },

        #**********************************************
        #UPBEAT

        {
            "label": "rimshot",
            "color": 0x1D4E89,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.A],
            "page": 1,
            "position": 0,
            "sound": "rimshot.wav",
            "type": "sound"
        },
        {
            "label": "win",
            "color": 0x1D4E89,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.B],
            "page": 1,
            "position": 1,
            "sound": "win.wav",
            "type": "sound"
        },
        {
            "label": "tada",
            "color": 0x1D4E89,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.C],
            "page": 1,
            "position": 2,
            "sound": "tada.wav",
            "type": "sound"
        },
        {
            "label": "clap",
            "color": 0x1D4E89,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.D],
            "page": 1,
            "position": 3,
            "sound": "clap.wav",
            "type": "sound"
        },
        {
            "label": "gudjob",
            "color": 0x1D4E89,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.E],
            "page": 1,
            "position": 4,
            "sound": "gudjob.wav",
            "type": "sound"
        },
        {
            "label": "fanfare",
            "color": 0x1D4E89,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.F],
            "page": 1,
            "position": 5,
            "sound": "fanfare.wav",
            "type": "sound"
        },
        {
            "label": "cash",
            "color": 0x1D4E89,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.G],
            "page": 1,
            "position": 6,
            "sound": "cash.wav",
            "type": "sound"
        },
        {
            "label": "holy",
            "color": 0x1D4E89,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.H],
            "page": 1,
            "position": 7,
            "sound": "holy.wav",
            "type": "sound"
        },
        {
            "label": "goat",
            "color": 0x1D4E89,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.I],
            "page": 1,
            "position": 8,
            "sound": "goat.wav",
            "type": "sound"
        },
        {
            "label": "rewind",
            "color": 0x1D4E89,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.J],
            "page": 1,
            "position": 9,
            "sound": "rewind.wav",
            "type": "sound"
        },
        {
            "label": "android",
            "color": 0x1D4E89,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.K],
            "page": 1,
            "position": 10,
            "sound": "android.wav",
            "type": "sound"
        },
        {
            "label": "stop",
            "color": 0x1D4E89,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.L],
            "page": 1,
            "position": 11,
            "sound": "stop.wav",
            "type": "sound"
        },
        #**********************************************
        #DOWNBEAT
        {
            "label": "fail",
            "color": 0x731DD8,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.M],
            "page": 2,
            "position": 0,
            "sound": "fail.wav",
            "type": "sound"
        },
        {
            "label": "wahwah",
            "color": 0x731DD8,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.N],
            "page": 2,
            "position": 1,
            "sound": "wahwah.wav",
            "type": "sound"
        },
        {
            "label": "doh!",
            "color": 0x731DD8,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.O],
            "page": 2,
            "position": 2,
            "sound": "doh!.wav",
            "type": "sound"
        },
        {
            "label": "unacept",
            "color": 0x731DD8,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.P],
            "page": 2,
            "position": 3,
            "sound": "unacept.wav",
            "type": "sound"
        },
        {
            "label": "nope",
            "color": 0x731DD8,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.Q],
            "page": 2,
            "position": 4,
            "sound": "nope.wav",
            "type": "sound"
        },
        {
            "label": "violin",
            "color": 0x731DD8,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.R],
            "page": 2,
            "position": 5,
            "sound": "violin.wav",
            "type": "sound"
        },
        {
            "label": "pacman",
            "color": 0x731DD8,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.S],
            "page": 2,
            "position": 6,
            "sound": "pacman.wav",
            "type": "sound"
        },
        {
            "label": "haha",
            "color": 0x731DD8,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.T],
            "page": 2,
            "position": 7,
            "sound": "haha.wav",
            "type": "sound"
        },
        {
            "label": "helno1",
            "color": 0x731DD8,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.U],
            "page": 2,
            "position": 8,
            "sound": "helno1.wav",
            "type": "sound"
        },
        {
            "label": "mario",
            "color": 0x731DD8,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.V],
            "page": 2,
            "position": 9,
            "sound": "mario.wav",
            "type": "sound"
        },
        {
            "label": "notpass",
            "color": 0x731DD8,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.W],
            "page": 2,
            "position": 10,
            "sound": "notpass.wav",
            "type": "sound"
        },
        {
            "label": "helno2",
            "color": 0x731DD8,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.X],
            "page": 2,
            "position": 11,
            "sound": "helno2.wav",
            "type": "sound"
        },
        #**********************************************
        #RANDOM 1
        {
            "label": "jetsons",
            "color": 0xA30015,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F13],
            "page": 3,
            "position": 0,
            "sound": "jetsons.wav",
            "type": "sound"
        },
        {
            "label": "auugh",
            "color": 0xA30015,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F14],
            "page": 3,
            "position": 1,
            "sound": "auugh.wav",
            "type": "sound"
        },
        {
            "label": "ohmy",
            "color": 0xA30015,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F15],
            "page": 3,
            "position": 2,
            "sound": "ohmy.wav",
            "type": "sound"
        },
        {
            "label": "saywhat",
            "color": 0xA30015,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F16],
            "page": 3,
            "position": 3,
            "sound": "saywhat.wav",
            "type": "sound"
        },
        {
            "label": "psycho",
            "color": 0xA30015,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F17],
            "page": 3,
            "position": 4,
            "sound": "psycho.wav",
            "type": "sound"
        },
        {
            "label": "train",
            "color": 0xA30015,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F18],
            "page": 3,
            "position": 5,
            "sound": "train.wav",
            "type": "sound"
        },
        {
            "label": "tacobel",
            "color": 0xA30015,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F19],
            "page": 3,
            "position": 6,
            "sound": "tacobel.wav",
            "type": "sound"
        },
        {
            "label": "boop",
            "color": 0xA30015,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F20],
            "page": 3,
            "position": 7,
            "sound": "boop.wav",
            "type": "sound"
        },
        {
            "label": "olspice",
            "color": 0xA30015,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F21],
            "page": 3,
            "position": 8,
            "sound": "olspice.wav",
            "type": "sound"
        },
        {
            "label": "cat",
            "color": 0xA30015,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F22],
            "page": 3,
            "position": 9,
            "sound": "cat.wav",
            "type": "sound"
        },
        {
            "label": "forget",
            "color": 0xA30015,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F23],
            "page": 3,
            "position": 10,
            "sound": "forget.wav",
            "type": "sound"
        },
        {
            "label": "bird",
            "color": 0xA30015,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F24],
            "page": 3,
            "position": 11,
            "sound": "bird.wav",
            "type": "sound"
        },
        #**********************************************
        #RANDOM 2
        {
            "label": "donkey",
            "color": 0x80FF72,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.A],
            "page": 4,
            "position": 0,
            "sound": "donkey.wav",
            "type": "sound"
        },
        {
            "label": "swamp",
            "color": 0x80FF72,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.B],
            "page": 4,
            "position": 1,
            "sound": "swamp.wav",
            "type": "sound"
        },
        {
            "label": "incon",
            "color": 0x80FF72,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.C],
            "page": 4,
            "position": 2,
            "sound": "incon.wav",
            "type": "sound"
        },
        {
            "label": "wilhlm",
            "color": 0x80FF72,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.D],
            "page": 4,
            "position": 3,
            "sound": "wilhlm.wav",
            "type": "sound"
        },
        {
            "label": "wrest",
            "color": 0x80FF72,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.E],
            "page": 4,
            "position": 4,
            "sound": "wrest.wav",
            "type": "sound"
        },
        {
            "label": "slip",
            "color": 0x80FF72,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F],
            "page": 4,
            "position": 5,
            "sound": "slip.wav",
            "type": "sound"
        },
        {
            "label": "psycho",
            "color": 0x80FF72,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.G],
            "page": 4,
            "position": 6,
            "sound": "psycho.wav",
            "type": "sound"
        },
        {
            "label": "goat",
            "color": 0x80FF72,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.H],
            "page": 4,
            "position": 7,
            "sound": "goat.wav",
            "type": "sound"
        },
        {
            "label": "rewind",
            "color": 0x80FF72,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.I],
            "page": 4,
            "position": 8,
            "sound": "rewind.wav",
            "type": "sound"
        },
        {
            "label": "gta",
            "color": 0x80FF72,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.J],
            "page": 4,
            "position": 9,
            "sound": "gta.wav",
            "type": "sound"
        },
        {
            "label": "huh",
            "color": 0x80FF72,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.K],
            "page": 4,
            "position": 10,
            "sound": "huh.wav",
            "type": "sound"
        },
        {
            "label": "scrch",
            "color": 0x80FF72,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.L],
            "page": 4,
            "position": 11,
            "sound": "scrch.wav",
            "type": "sound"
        },
        #**********************************************
        #RICK 1
        {
            "label": "heymrt",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.M],
            "page": 5,
            "position": 0,
            "sound": "heymrt.wav",
            "type": "sound"
        },
        {
            "label": "likewht",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.N],
            "page": 5,
            "position": 1,
            "sound": "likewht.wav",
            "type": "sound"
        },
        {
            "label": "school",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.O],
            "page": 5,
            "position": 2,
            "sound": "school.wav",
            "type": "sound"
        },
        {
            "label": "alright",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.P],
            "page": 5,
            "position": 3,
            "sound": "alright.wav",
            "type": "sound"
        },
        {
            "label": "showme",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.Q],
            "page": 5,
            "position": 4,
            "sound": "shwme.wav",
            "type": "sound"
        },
        {
            "label": "totes",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.R],
            "page": 5,
            "position": 5,
            "sound": "totes.wav",
            "type": "sound"
        },
        {
            "label": "tryin",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.S],
            "page": 5,
            "position": 6,
            "sound": "tryin.wav",
            "type": "sound"
        },
        {
            "label": "wuba",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.T],
            "page": 5,
            "position": 7,
            "sound": "wuba.wav",
            "type": "sound"
        },
        {
            "label": "butter",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.U],
            "page": 5,
            "position": 8,
            "sound": "butter.wav",
            "type": "sound"
        },
        {
            "label": "myman",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.V],
            "page": 5,
            "position": 9,
            "sound": "myman.wav",
            "type": "sound"
        },
        {
            "label": "disqua",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.W],
            "page": 5,
            "position": 10,
            "sound": "disqua.wav",
            "type": "sound"
        },
        {
            "label": "whatsgo",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.X],
            "page": 5,
            "position": 11,
            "sound": "whatsgo.wav",
            "type": "sound"
        },
        #**********************************************
        #RICK 2
        {
            "label": "newsgo",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.A],
            "page": 6,
            "position": 0,
            "sound": "newsgo.wav",
            "type": "sound"
        },
        {
            "label": "nocan",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.B],
            "page": 6,
            "position": 1,
            "sound": "nocan.wav",
            "type": "sound"
        },
        {
            "label": "ok",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.C],
            "page": 6,
            "position": 2,
            "sound": "ok.wav",
            "type": "sound"
        },
        {
            "label": "thanku",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.D],
            "page": 6,
            "position": 3,
            "sound": "thanku.wav",
            "type": "sound"
        },
        {
            "label": "evilm",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.E],
            "page": 6,
            "position": 4,
            "sound": "evilm.wav",
            "type": "sound"
        },
        {
            "label": "totes",
            "color": 0x7A306C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.F],
            "page": 6,
            "position": 5,
            "sound": "totes.wav",
            "type": "sound"
        },
        {
            "label": "betrnt",
            "color": 0x000000,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.G],
            "page": 6,
            "position": 6,
            "sound": "betrnt.wav",
            "type": "sound"
        },
        {
            "label": "bndaid",
            "color": 0x000000,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.H],
            "page": 6,
            "position": 7,
            "sound": "bndaid.wav",
            "type": "sound"
        },
        #**********************************************
        #SONGS
        {
            "label": "circus",
            "color": 0xB7245C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.M],
            "page": 7,
            "position": 0,
            "sound": "circus.wav",
            "type": "sound"
        },
        {
            "label": "imarch",
            "color": 0xB7245C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.N],
            "page": 7,
            "position": 1,
            "sound": "imarch.wav",
            "type": "sound"
        },
        {
            "label": "sanford",
            "color": 0xB7245C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.O],
            "page": 7,
            "position": 2,
            "sound": "sanford.wav",
            "type": "sound"
        },
        {
            "label": "loony",
            "color": 0xB7245C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.P],
            "page": 7,
            "position": 3,
            "sound": "loony.wav",
            "type": "sound"
        },
        {
            "label": "dirty",
            "color": 0xB7245C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.Q],
            "page": 7,
            "position": 4,
            "sound": "dirty.wav",
            "type": "sound"
        },
        {
            "label": "never",
            "color": 0xB7245C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.R],
            "page": 7,
            "position": 5,
            "sound": "never.wav",
            "type": "sound"
        },
        {
            "label": "nancy",
            "color": 0xB7245C,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.S],
            "page": 7,
            "position": 6,
            "sound": "nancy.wav",
            "type": "sound"
        },
        {
            "label": "python",
            "color": 0x000000,
            "keycodes": [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.LEFT_SHIFT, Keycode.T],
            "page": 7,
            "position": 7,
            "sound": "python.wav",
            "type": "sound"
        },
        #**********************************************
        #SPONGEBOB
        {
            "label": "boowmp",
            "color": 0xFF9900,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F13],
            "page": 8,
            "position": 0,
            "sound": "boowmp.wav",
            "type": "sound"
        },
        {
            "label": "shucks",
            "color": 0xFF9900,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F14],
            "page": 8,
            "position": 1,
            "sound": "shucks.wav",
            "type": "sound"
        },
        {
            "label": "gary",
            "color": 0xFF9900,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F15],
            "page": 8,
            "position": 2,
            "sound": "gary.wav",
            "type": "sound"
        },
        {
            "label": "mml8tr",
            "color": 0xFF9900,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F16],
            "page": 8,
            "position": 3,
            "sound": "mml8tr.wav",
            "type": "sound"
        },
        {
            "label": "hrl8tr",
            "color": 0xFF9900,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F17],
            "page": 8,
            "position": 4,
            "sound": "hrl8tr.wav",
            "type": "sound"
        },
        {
            "label": "yrl8tr",
            "color": 0xFF9900,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F18],
            "page": 8,
            "position": 5,
            "sound": "yrl8tr.wav",
            "type": "sound"
        },
        {
            "label": "squid",
            "color": 0xFF9900,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F19],
            "page": 8,
            "position": 6,
            "sound": "squid.wav",
            "type": "sound"
        },
        {
            "label": "yippee",
            "color": 0xFF9900,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F20],
            "page": 8,
            "position": 7,
            "sound": "yippee.wav",
            "type": "sound"
        },
        {
            "label": "fog",
            "color": 0xFF9900,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F21],
            "page": 8,
            "position": 8,
            "sound": "fog.wav",
            "type": "sound"
        },
        {
            "label": "dolfn",
            "color": 0xFF9900,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F22],
            "page": 8,
            "position": 9,
            "sound": "dolfn.wav",
            "type": "sound"
        },
        {
            "label": "thanks",
            "color": 0xFF9900,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F23],
            "page": 8,
            "position": 10,
            "sound": "thanks.wav",
            "type": "sound"
        },
        {
            "label": "sadsng",
            "color": 0xFF9900,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F24],
            "page": 8,
            "position": 11,
            "sound": "sadsng.wav",
            "type": "sound"
        },
        #**********************************************
        #STARWARS 1
        {
            "label": "nooo",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.A],
            "page": 9,
            "position": 0,
            "sound": "nooo.wav",
            "type": "sound"
        },
        {
            "label": "faith",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.B],
            "page": 9,
            "position": 1,
            "sound": "faith.wav",
            "type": "sound"
        },
        {
            "label": "chewy",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.C],
            "page": 9,
            "position": 2,
            "sound": "chewy.wav",
            "type": "sound"
        },
        {
            "label": "strong",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.D],
            "page": 9,
            "position": 3,
            "sound": "strong.wav",
            "type": "sound"
        },
        {
            "label": "force",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.E],
            "page": 9,
            "position": 4,
            "sound": "force.wav",
            "type": "sound"
        },
        {
            "label": "order",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.F],
            "page": 9,
            "position": 5,
            "sound": "order.wav",
            "type": "sound"
        },
        {
            "label": "disturb",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.G],
            "page": 9,
            "position": 6,
            "sound": "disturb.wav",
            "type": "sound"
        },
        {
            "label": "yes",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.H],
            "page": 9,
            "position": 7,
            "sound": "yes.wav",
            "type": "sound"
        },
        #**********************************************
        #STARWARS 2
        {
            "label": "corect",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.M],
            "page": 10,
            "position": 0,
            "sound": "corect.wav",
            "type": "sound"
        },
        {
            "label": "whaat",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.N],
            "page": 10,
            "position": 1,
            "sound": "whaat.wav",
            "type": "sound"
        },
        {
            "label": "trap",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.O],
            "page": 10,
            "position": 2,
            "sound": "trap.wav",
            "type": "sound"
        },
        {
            "label": "gudwork",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.P],
            "page": 10,
            "position": 3,
            "sound": "gudwork.wav",
            "type": "sound"
        },
        {
            "label": "doit",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.Q],
            "page": 10,
            "position": 4,
            "sound": "doit.wav",
            "type": "sound"
        },
        {
            "label": "yoda",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.R],
            "page": 10,
            "position": 5,
            "sound": "yoda.wav",
            "type": "sound"
        },
        {
            "label": "apology",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.S],
            "page": 10,
            "position": 6,
            "sound": "apology.wav",
            "type": "sound"
        },
        {
            "label": "wish",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.T],
            "page": 10,
            "position": 7,
            "sound": "wish.wav",
            "type": "sound"
        },
        {
            "label": "cantina",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.U],
            "page": 10,
            "position": 8,
            "sound": "cantina.wav",
            "type": "sound"
        },
        {
            "label": "vader",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.Y],
            "page": 10,
            "position": 9,
            "sound": "vader.wav",
            "type": "sound"
        },
        {
            "label": "pntless",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.W],
            "page": 10,
            "position": 10,
            "sound": "pntless.wav",
            "type": "sound"
        },
        {
            "label": "destiny",
            "color": 0xFFFFFF,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_SHIFT, Keycode.X],
            "page": 10,
            "position": 11,
            "sound": "destiny.wav",
            "type": "sound"
        },
        #**********************************************
        #JEOPARDY
        {
            "label": "intro",
            "color": 0x000060,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.A],
            "page": 11,
            "position": 0,
            "sound": "intro.wav",
            "type": "sound"
        },
        {
            "label": "shuffle",
            "color": 0x000060,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.B],
            "page": 11,
            "position": 1,
            "sound": "shuffle.wav",
            "type": "sound"
        },
        {
            "label": "think",
            "color": 0x000060,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.C],
            "page": 11,
            "position": 2,
            "sound": "think.wav",
            "type": "sound"
        },
        {
            "label": "timeup",
            "color": 0x000060,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.D],
            "page": 11,
            "position": 3,
            "sound": "timeup.wav",
            "type": "sound"
        },
        {
            "label": "right",
            "color": 0x000060,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.E],
            "page": 11,
            "position": 4,
            "sound": "right.wav",
            "type": "sound"
        },
        {
            "label": "daily",
            "color": 0x000060,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.F],
            "page": 11,
            "position": 5,
            "sound": "daily.wav",
            "type": "sound"
        },
        {
            "label": "newlow",
            "color": 0x000060,
            "keycodes": [Keycode.LEFT_CONTROL, Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.G],
            "page": 11,
            "position": 6,
            "sound": "newlow.wav",
            "type": "sound"
        },
    ]
