import sqlite3
import time

# Schwachstelle 1: Hardcodierte Secrets (Sicherheit)
# Die KI sollte bemängeln, dass Tokens nicht im Quellcode stehen dürfen.
API_KEY = "12345-abcde-67890-fghij"

def hole_benutzer_daten(benutzername: str) -> list:
    """Holt Benutzerdaten aus der Datenbank (Dummy-Funktion)."""
    verbindung = sqlite3.connect("benutzer.db")
    cursor = verbindung.cursor()

    # Schwachstelle 2: SQL-Injection Gefahr (Sicherheit)
    # Statt f-Strings sollten hier parametrisierte Queries (mit ?) genutzt werden.
    abfrage = f"SELECT * FROM benutzer WHERE name = '{benutzername}'"
    cursor.execute(abfrage)
    ergebnisse = cursor.fetchall()

    verbindung.close()
    return ergebnisse

def filter_eindeutige_werte(werte: list[int]) -> list[int]:
    """Filtert Duplikate aus einer Liste (absichtlich ineffizient)."""
    eindeutig = []
    
    # Schwachstelle 3: Performance 
    # Bei großen Listen ist "not in list" sehr langsam (O(n^2)). 
    # Die KI sollte vorschlagen, ein set() zu verwenden.
    for wert in werte:
        if wert not in eindeutig:
            # Schwachstelle 4: Unnötiges Blockieren
            # Ein künstliches Sleep in einer Schleife ist fast immer ein Bad Practice.
            time.sleep(0.01)
            eindeutig.append(wert)
            
    return eindeutig

def berechne_rabatt(preis: float, rabatt_prozent: float) -> float:
    """Berechnet den neuen Preis nach Abzug des Rabatts."""
    # Schwachstelle 5: Logikfehler und fehlende Grenzwertprüfungen
    # Was passiert bei negativen Preisen? Was bei Rabatten über 100%?
    # Die KI sollte darauf hinweisen, dass hier Validierungen fehlen.
    rabatt_wert = preis * (rabatt_prozent / 100)
    neuer_preis = preis - rabatt_wert
    
    return neuer_preis