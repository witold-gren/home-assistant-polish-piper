"""Pronunciation overrides: foreign words and names spelled the Polish way.

espeak-ng (Polish) reads English words letter by letter or with Polish rules
("Review" -> "rewiew"). Each entry is written as it should sound in Polish;
matching is case-insensitive and whole-word. Add words heard wrong in
`docker logs piper | grep normalize`.
"""

PRONUNCIATIONS: dict[str, str] = {
    # Work / calendar
    "standup": "stendap",
    "stand-up": "stendap",
    "review": "riwju",
    "meeting": "miting",
    "call": "kol",
    "sync": "sink",
    "PR": "pi ar",
    "1:1": "łan on łan",
    # Home / devices
    "Home Assistant": "Hołm Asystent",
    "HomePod": "Hołm Pod",
    "HomeKit": "Hołm Kit",
    "iPhone": "ajfon",
    "iPad": "ajpad",
    "MacBook": "Mekbuk",
    "Apple": "Epl",
    "Google": "Gugl",
    "YouTube": "Jutub",
    "Netflix": "Netfliks",
    "Spotify": "Spotifaj",
    "Wi-Fi": "łifi",
    "WiFi": "łifi",
    "Bluetooth": "blutut",
    "smart": "smart",
    "Volvo": "Wolwo",
    "Frigate": "Frigejt",
    "Reolink": "Riolink",
    "eufy": "jufi",
    "Netatmo": "Netatmo",
    "Philips Hue": "Filips Hju",
    "Hue": "Hju",
    "OK": "okej",
    "e-mail": "imejl",
    "email": "imejl",
}
