"""Testdatei mit absichtlichen Fehlern für den Linter-Test."""

import sys
import os
import json  # unused import

# E501: Zeile zu lang
sehr_langer_variablenname = "Das ist ein sehr langer String der definitiv die empfohlene Zeilenlänge von 88 Zeichen überschreitet"

# F841: lokale Variable wird nie verwendet
def berechne_summe(a, b):
    ergebnis = a + b
    unbenutzte_variable = 42  # wird nie verwendet
    return ergebnis


# E711: Vergleich mit None via == statt is
def pruefe_wert(x):
    if x == None:
        return False
    return True


# W291: trailing whitespace + E302: fehlende Leerzeile
class MeineKlasse:
    def __init__(self):
        self.wert = 0   
    def setze_wert(self, v):  # E301: fehlende Leerzeile vor Methode
        self.wert = v


# B006: mutable default argument
def fuege_hinzu(element, liste=[]):
    liste.append(element)
    return liste


# UP007: verwende X | Y statt Optional[X]
# E402: import nicht zu Beginn ausgeführt
from typing import Optional
def hole_name(name: Optional[str]) -> Optional[str]:
    return name


# C901: zu hohe Komplexität (viele verschachtelte if)
def komplexe_funktion(a, b, c, d):
    if a:
        if b:
            if c:
                if d:
                    return "tief verschachtelt"
                else:
                    return "d ist False"
            else:
                return "c ist False"
        else:
            return "b ist False"
    else:
        return "a ist False"
