import os

import sqlite3

import time
# Schwachstelle 1: Hardcodierte Secrets (Sicherheit)
# Die KI sollte bemängeln, dass Tokens nicht im Quellcode stehen dürfen.
API_KEY = os.environ.get('API_KEY')
if not API_KEY:
    raise EnvironmentError('API_KEY ist nicht gesetzt')

def hole_benutzer_daten(benutzername: str) -> list:
    """Holt Benutzerdaten aus der Datenbank (Dummy-Funktion)."""
    with sqlite3.connect("benutzer.db") as verbindung:
        cursor = verbindung.cursor()

        # Schwachstelle 2: SQL-Injection Gefahr (Sicherheit)
        # Statt f-Strings sollten hier parametrisierte Queries (mit ?) genutzt werden.
        abfrage = 'SELECT * FROM benutzer WHERE name = ?'
        cursor.execute(abfrage, (benutzername,))
        ergebnisse = cursor.fetchall()

    return ergebnisse

def filter_eindeutige_werte(werte: list[int]) -> list[int]:

    """Filtert Duplikate aus einer Liste (absichtlich ineffizient)."""

    gesehen = set()

    eindeutig = []

    

    # Schwachstelle 3: Performance 

    # Bei großen Listen ist "not in list" sehr langsam (O(n^2)). 

    # Die KI sollte vorschlagen, ein set() zu verwenden.

    for wert in werte:

        if wert not in gesehen:

            gesehen.add(wert)

            # Schwachstelle 4: Unnötiges Blockieren

            time.sleep(0.01)

            eindeutig.append(wert)

            

    return eindeutig

def berechne_rabatt(preis: float, rabatt_prozent: float) -> float:

    """Berechnet den neuen Preis nach Abzug des Rabatts."""

    if preis < 0:
        raise ValueError(f'Preis darf nicht negativ sein: {preis}')
    if not (0 <= rabatt_prozent <= 100):
        raise ValueError(f'Rabatt muss zwischen 0 und 100 liegen: {rabatt_prozent}')
    rabatt_wert = preis * (rabatt_prozent / 100)
    neuer_preis = preis - rabatt_wert
    return neuer_preis