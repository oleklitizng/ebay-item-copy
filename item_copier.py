import os
import json
import time  # Added missing import for time.time() used in create_new_item_draft
from ebaysdk.trading import Connection as Trading
from ebaysdk.exception import ConnectionError
from dotenv import load_dotenv
import html
from collections import defaultdict

def get_item_details(item_id):
    """Ruft die eBay-Item-Details ab und speichert sie in einer Datei."""
    try:
        api = Trading(config_file=None, **EBAY_API_CONFIG)
        
        call = {
            'ItemID': item_id,
            'DetailLevel': 'ReturnAll',
            'IncludeItemSpecifics': True,
            'IncludeItemCompatibilityList': True
        }
        
        response = api.execute('GetItem', call)

        if response.reply.Ack == 'Success':
            item_data = response.dict()  # Umwandlung in ein Dictionary
            save_item_details(item_id, item_data)
            return response.reply.Item
        else:
            print(f"Fehler beim Abrufen des Artikels {item_id}: {response.reply.Errors}")
            return None

    except ConnectionError as e:
        print(f"Fehler bei der API-Verbindung: {e}")
        return None

def save_item_details(item_id, item_data):
    """Speichert die Artikelinformationen als JSON-Datei."""
    file_name = f"item_{item_id}.json"
    
    try:
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(item_data, f, indent=4, ensure_ascii=False)
        print(f"Artikelinformationen gespeichert: {file_name}")
    except Exception as e:
        print(f"Fehler beim Speichern der Datei: {e}")

def extract_item_specific(item, keys):
    """Extrahiert einen spezifischen Wert aus den Item-Specifics."""
    if not item or not hasattr(item, 'ItemSpecifics'):
        print(f"Keine Item-Specifics für {keys} gefunden!")
        return None
    
    specifics = item.ItemSpecifics.NameValueList
    for spec in specifics:
        if spec.Name.lower() in keys:
            return spec.Value  # Normalerweise ist Value eine Liste
    
    print(f"{keys} nicht gefunden!")
    return None

import html

def extract_compatibility_list(item):
    """Extrahiert die Fahrzeugkompatibilitätsliste aus ItemCompatibilityList."""
    if not item or not hasattr(item, 'ItemCompatibilityList'):
        print("Keine Fahrzeugkompatibilitätsliste gefunden!")
        return None

    compatibility_list = []
    for compatibility in item.ItemCompatibilityList.Compatibility:
        vehicle_data = {}
        for spec in compatibility.NameValueList:
            if spec:  # Vermeidung von Null-Werten
                vehicle_data[spec.Name] = spec.Value

        # Hier wird das Period-Attribut überprüft und korrigiert, wenn nötig
        if hasattr(compatibility, 'Period'):
            period_value = getattr(compatibility, 'Period')
            # Überprüfen, ob das Period-Attribut den '='-Operator fehlt und hinzufügen
            if period_value and '=' not in period_value:
                corrected_period = period_value.replace('Period"', 'Period="')
                setattr(compatibility, 'Period', corrected_period)

        # Verwende .get() für CompatibilityNotes, um Fehler zu vermeiden
        compatibility_notes = compatibility.get("CompatibilityNotes")
        if compatibility_notes:
            # HTML-Entities dekodieren
            vehicle_data["Notes"] = html.unescape(compatibility_notes)
        
        compatibility_list.append(vehicle_data)
    
    return compatibility_list


def extract_title(item):
    """Extrahiert den Titel des Artikels."""
    if not item or not hasattr(item, 'Title'):
        print(f"Kein Title gefunden!")
        return None
    
    return item.Title

def extract_picture_url(item):
    """Extrahiert die erste Bild-URL des Artikels."""
    if not item or not hasattr(item, 'PictureDetails'):
        print(f"Keine Bilder gefunden!")
        return None
    
    picture_details = item.PictureDetails
    if hasattr(picture_details, 'PictureURL'):
        if isinstance(picture_details.PictureURL, list):
            return picture_details.PictureURL[0]
        else:
            return picture_details.PictureURL
    
    return None

def create_item_specifics_html(item):
    """Erstellt HTML-Tabelle für die Item-Specifics."""
    if not item or not hasattr(item, 'ItemSpecifics'):
        return "<p>Keine Produktdetails verfügbar</p>"
    
    html_output = "<table>"
    html_output += "<tr><th>Eigenschaft</th><th>Wert</th></tr>"
    
    for spec in item.ItemSpecifics.NameValueList:
        name = html.escape(spec.Name)
        
        # Werte können Listen oder Strings sein
        if isinstance(spec.Value, list):
            value = ", ".join([html.escape(str(v)) for v in spec.Value])
        else:
            value = html.escape(str(spec.Value))
        
        html_output += f"<tr><td>{name}</td><td>{value}</td></tr>"
    
    html_output += "</table>"
    return html_output

def create_compatibility_html(compatibility_list):
    """Erstellt eine kompakte HTML-Tabelle für die Fahrzeugkompatibilitätsliste."""
    if not compatibility_list:
        return "<p>Keine Kompatibilitätsdaten verfügbar</p>"
    
    # Gruppierung nach Marke, Modell und Plattform
    grouped_vehicles = defaultdict(list)
    
    for vehicle in compatibility_list:
        # Schlüssel für die Gruppierung: Marke + Modell + Plattform (wenn vorhanden)
        brand = vehicle.get('Make', 'Unbekannt')
        model = vehicle.get('Model', 'Unbekannt')
        platform = vehicle.get('Platform', '')
        
        # Zusammengesetzter Schlüssel für die Gruppierung
        group_key = f"{brand}|{model}|{platform}"
        
        # Kopie des Fahrzeugs ohne Notes und Type erstellen
        vehicle_copy = {k: v for k, v in vehicle.items() if k not in ['Notes', 'Type']}
        
        # Zur entsprechenden Gruppe hinzufügen
        grouped_vehicles[group_key].append(vehicle_copy)
    
    # HTML-Tabelle erstellen
    html_output = "<table>"
    
    # Sammeln aller möglichen Schlüssel außer Make, Model, Platform, Notes und Type
    all_keys = set()
    for vehicles in grouped_vehicles.values():
        for vehicle in vehicles:
            all_keys.update(k for k in vehicle.keys() if k not in ['Make', 'Model', 'Platform', 'Notes', 'Type'])
    
    # Sortieren der Schlüssel für eine konsistente Anzeige (Make, Model, Platform zuerst)
    header_keys = ['Make', 'Model', 'Platform'] + sorted(all_keys)
    
    # Tabellenkopf erstellen
    html_output += "<tr>"
    for key in header_keys:
        html_output += f"<th>{html.escape(key)}</th>"
    html_output += "</tr>"
    
    # Für jede Gruppe eine zusammengefasste Zeile erstellen
    for group_key, vehicles in sorted(grouped_vehicles.items()):
        if not vehicles:
            continue
            
        # Die erste Zeile für Make, Model, Platform verwenden
        brand, model, platform = group_key.split('|')
        
        html_output += "<tr>"
        html_output += f"<td>{html.escape(brand)}</td>"
        html_output += f"<td>{html.escape(model)}</td>"
        html_output += f"<td>{html.escape(platform)}</td>"
        
        # Restliche Felder zusammenfassen (Jahre, Motoren, etc.)
        for key in sorted(all_keys):
            # Alle unterschiedlichen Werte für dieses Attribut sammeln
            values = set()
            for vehicle in vehicles:
                if key in vehicle and vehicle[key]:
                    if isinstance(vehicle[key], list):
                        values.update(vehicle[key])
                    else:
                        values.add(vehicle[key])
            
            # Werte zusammenfassen und anzeigen
            if values:
                joined_values = ", ".join(sorted(html.escape(str(v)) for v in values))
                html_output += f"<td>{joined_values}</td>"
            else:
                html_output += "<td>-</td>"
        
        html_output += "</tr>"
    
    html_output += "</table>"
    return html_output

def generate_ebay_listing_html(item_id):
    """Hauptfunktion zum Erstellen einer HTML-Vorlage für den eBay-Artikel."""
    # Template-Datei laden
    try:
        with open("ebay_listing_template_general.html", "r", encoding="utf-8") as f:
            template = f.read()
    except Exception as e:
        print(f"Fehler beim Laden der Template-Datei: {e}")
        return None
    
    # Artikeldetails abrufen
    item_details = get_item_details(item_id)
    if not item_details:
        return None
    
    # Daten extrahieren
    title = extract_title(item_details) or "Produkttitel nicht verfügbar"
    picture_url = extract_picture_url(item_details) or ""
    item_specifics_html = create_item_specifics_html(item_details)
    compatibility_html = create_compatibility_html(extract_compatibility_list(item_details))
    
    # Template mit Daten füllen
    filled_template = template.replace("{{TITLE}}", html.escape(title))
    filled_template = filled_template.replace("{{PICTURE_URL}}", picture_url)
    filled_template = filled_template.replace("{{ITEMSPEZIFIKATIONEN}}", item_specifics_html)
    filled_template = filled_template.replace("{{KOMPATIBILITÄT}}", compatibility_html)
    
    # Ausgabedatei erstellen
    output_filename = f"ebay_listing_{item_id}.html"
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(filled_template)
        print(f"eBay-Listing-HTML erstellt: {output_filename}")
        return output_filename
    except Exception as e:
        print(f"Fehler beim Erstellen der HTML-Datei: {e}")
        return None

def get_shipping_profile(weight):
    """
    Bestimmt das Versandprofil basierend auf dem Gewicht.
    
    Args:
        weight: Gewicht des Artikels in kg
    
    Returns:
        Dictionary mit ShippingProfileID und ShippingProfileName
    """
    weight_float = float(weight)
    if weight_float <= 2:
        return {
            'ShippingProfileID': '250276345015',
            'ShippingProfileName': 'DeutschePost/DHL/DPD/bis2kg/MBHbis90cm'
        }
    elif 2 < weight_float <= 5:
        return {
            'ShippingProfileID': '252160656015',
            'ShippingProfileName': 'DHL/DPD/2-5kg/120x60x60'
        }
    else:
        return {
            'ShippingProfileID': '249607222015',
            'ShippingProfileName': 'DHL/DPD/5-10kg/120x6x60'
        }

import time
def escape_xml(text):
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&apos;')
    return text

def create_new_item_draft(source_item_id, start_price=None, quantity=None, SKU=None):
    """
    Erstellt einen neuen Artikelentwurf basierend auf einem existierenden eBay-Artikel.
    
    Args:
        source_item_id: Die ID des Quellartikels
        start_price: Optional - neuer Preis, wenn nicht angegeben wird der Originalpreis verwendet
        quantity: Optional - neue Menge, wenn nicht angegeben wird die Originalmenge verwendet
        SKU: Optional - neue SKU, wenn nicht angegeben wird eine generierte SKU verwendet
    """
    # Artikeldetails abrufen
    print(f"Rufe Details für Artikel {source_item_id} ab...")
    source_item = get_item_details(source_item_id)
    if not source_item:
        print(f"Konnte keine Details für Artikel {source_item_id} abrufen.")
        return None
    
    print(f"Details für Artikel {source_item_id} erfolgreich abgerufen.")

    # HTML-Template für die Beschreibung generieren
    print("Generiere HTML-Beschreibung für Artikel...")
    output_file = generate_ebay_listing_html(source_item_id)
    if not output_file:
        print("Fehler beim Erstellen der HTML-Beschreibung.")
        return None
    
    print(f"HTML-Beschreibung erfolgreich erstellt. Lade Datei {output_file}...")
    
    # HTML-Beschreibung laden
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            description = f.read()
        description = f"<![CDATA[{description}]]>"
        print("HTML-Beschreibung erfolgreich geladen.")
    except Exception as e:
        print(f"Fehler beim Laden der HTML-Beschreibung: {e}")
        return None
    
    # API-Verbindung herstellen
    print("Stelle API-Verbindung zu eBay her...")
    api = Trading(config_file=None, **EBAY_API_CONFIG)
    
    # Werte aus dem Quellartikel extrahieren
    print("Extrahiere Details aus dem Quellartikel...")
    title = source_item.Title
    category_id = source_item.PrimaryCategory.CategoryID
    condition_id = source_item.ConditionID if hasattr(source_item, 'ConditionID') else "1000"  # Default: Neu
    original_price = float(source_item.StartPrice.value)
    original_quantity = int(source_item.Quantity) if hasattr(source_item, 'Quantity') else 1
    
    # Parameter überschreiben wenn angegeben
    final_price = start_price if start_price is not None else original_price
    final_quantity = quantity if quantity is not None else original_quantity
    final_sku = SKU if SKU is not None else f"COPY-{source_item_id}-{int(time.time())}"
    
    
    # ItemSpecifics extrahieren
    item_specifics = []

    if hasattr(source_item, 'ItemSpecifics') and hasattr(source_item.ItemSpecifics, 'NameValueList'):
        for spec in source_item.ItemSpecifics.NameValueList:
            # Escape für den Name-Wert
            name = escape_xml(spec.Name)

            # Verarbeitung des Values, wenn es eine Liste ist oder ein einzelner Wert
            if isinstance(spec.Value, list):
                # Escape für jedes Element in der Liste
                value = [escape_xml(v) for v in spec.Value]
            else:
                # Escape für den Einzelwert
                value = escape_xml(spec.Value)

            # Hinzufügen der verarbeiteten Werte zur item_specifics-Liste
            item_specifics.append({'Name': name, 'Value': value})

    #item_compatibility_list = extract_compatibility_list(source_item) 
    #print(item_compatibility_list)
    # Benutzer nach Gewicht fragen
    weight = input("Bitte geben Sie das Gewicht des Artikels in kg ein: ")
    
    # Versandprofil basierend auf Gewicht
    shipping_profile = get_shipping_profile(weight)
    
    # Verwende die angegebene Bild-URL anstatt der Original-URLs
    picture_url = 'https://rs-syke.de/wp-content/uploads/2024/06/rs-syke.de_.webp'

    # Neuen Artikel erstellen
    new_item = {
        'Item': {
            'Title': title,
            'Description': description,
            'PrimaryCategory': {'CategoryID': category_id},
            'StartPrice': final_price,
            'Quantity': final_quantity,
            'ListingType': 'FixedPriceItem',
            'ListingDuration': 'GTC',
            'Location': 'Hannoversche Str.57, 28857 Syke',
            'Country': 'DE',
            'Currency': 'EUR',
            'DispatchTimeMax': '3',
            'ConditionID': condition_id,
            'PictureDetails': {
                'PictureURL': [picture_url]
            },
            'ItemSpecifics': {'NameValueList': item_specifics},
            #'ItemCompatibilityList': {
                #'Compatibility': item_compatibility_list
            #},
            'SKU': final_sku,
            'VATDetails': {'VATPercent': '19'},
            'SellerProfiles': {
                'SellerShippingProfile': shipping_profile
            }
        }
    }


    # Als Entwurf speichern
    try:
        print("Versuche, Artikel als Entwurf zu speichern...")
        response = api.execute('AddItem', new_item)

        draft_item_id = response.reply.ItemID
        print(f"Entwurf erfolgreich erstellt mit ID: {draft_item_id}, Preis: {final_price}€")

        return draft_item_id
    except ConnectionError as e:
        print(f"Fehler beim Erstellen des Artikelentwurfs: {e}")
        return None
    except Exception as e:
        print(f"Unbekannter Fehler beim Erstellen des Artikelentwurfs: {e}")
        return None

    
def revise_item(item_id, source_item_id, start_price=None, quantity=None, SKU=None):
    """
    Überarbeitet einen bestehenden Artikel mit Daten aus einem Quellartikel.
    
    Args:
        item_id: Die ID des zu überarbeitenden Artikels
        source_item_id: Die ID des Quellartikels
        start_price: Optional - neuer Preis, wenn nicht angegeben wird der aktuelle Preis beibehalten
        quantity: Optional - neue Menge, wenn nicht angegeben wird die aktuelle Menge beibehalten
        SKU: Optional - neue SKU, wenn nicht angegeben wird die aktuelle SKU beibehalten
    """
    # Artikeldetails des Quellartikels abrufen
    source_item = get_item_details(source_item_id)
    if not source_item:
        print(f"Konnte keine Details für Quellartikel {source_item_id} abrufen.")
        return None
    
    # HTML-Template für die Beschreibung generieren
    output_file = generate_ebay_listing_html(source_item_id)
    if not output_file:
        print("Fehler beim Erstellen der HTML-Beschreibung.")
        return None
    
    # HTML-Beschreibung laden
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            description = f.read()
        description = f"<![CDATA[{description}]]>"
    except Exception as e:
        print(f"Fehler beim Laden der HTML-Beschreibung: {e}")
        return None
    
    # API-Verbindung herstellen
    api = Trading(config_file=None, **EBAY_API_CONFIG)
    
    # Daten des zu überarbeitenden Artikels abrufen
    try:
        get_item_response = api.execute('GetItem', {'ItemID': item_id})
        existing_item = get_item_response.reply.Item
    except ConnectionError as e:
        print(f"Fehler beim Abrufen des zu überarbeitenden Artikels: {e}")
        return None
    
    # Werte aus dem Quellartikel und dem bestehenden Artikel extrahieren
    title = source_item.Title
    category_id = source_item.PrimaryCategory.CategoryID
    condition_id = existing_item.ConditionID if hasattr(existing_item, 'ConditionID') else source_item.ConditionID
    
    # Parameter überschreiben wenn angegeben
    final_price = start_price if start_price is not None else float(existing_item.StartPrice.value)
    final_quantity = quantity if quantity is not None else int(existing_item.Quantity)
    final_sku = SKU if SKU is not None else existing_item.SKU if hasattr(existing_item, 'SKU') else None
    
    item_specifics = []
    # ItemSpecifics aus dem Quellartikel extrahieren
    if hasattr(source_item, 'ItemSpecifics') and hasattr(source_item.ItemSpecifics, 'NameValueList'):
        for spec in source_item.ItemSpecifics.NameValueList:
            # Escape für den Name-Wert
            name = escape_xml(spec.Name)

            # Verarbeitung des Values, wenn es eine Liste ist oder ein einzelner Wert
            if isinstance(spec.Value, list):
                # Escape für jedes Element in der Liste
                value = [escape_xml(v) for v in spec.Value]
            else:
                # Escape für den Einzelwert
                value = escape_xml(spec.Value)

            # Hinzufügen der verarbeiteten Werte zur item_specifics-Liste
            item_specifics.append({'Name': name, 'Value': value})

    # Benutzer nach Gewicht fragen
    weight = input("Bitte geben Sie das Gewicht des Artikels in kg ein: ")
    
    # Versandprofil basierend auf Gewicht
    shipping_profile = get_shipping_profile(weight)
    
    # Verwendung der festgelegten Bild-URL
    picture_url = 'https://rs-syke.de/wp-content/uploads/2024/06/rs-syke.de_.webp'
    
    # Artikelüberarbeitung vorbereiten
    revised_item = {
        'Item': {
            'ItemID': item_id,
            'Title': title,
            'Description': description,
            'PrimaryCategory': {'CategoryID': category_id},
            'StartPrice': final_price,
            'Quantity': final_quantity,
            'ItemSpecifics': {'NameValueList': item_specifics},
            'ConditionID': condition_id,
            'SellerProfiles': {
                'SellerShippingProfile': shipping_profile
            }
        }
    }
    
    # SKU hinzufügen, wenn vorhanden
    if final_sku:
        revised_item['Item']['SKU'] = final_sku
    
    # Artikel überarbeiten
    try:
        response = api.execute('ReviseItem', revised_item)
        print(f"Artikel erfolgreich überarbeitet. ItemID: {response.reply.ItemID}, Preis: {final_price}€")
        return response.reply.ItemID
    except ConnectionError as e:
        print(f"Fehler beim Überarbeiten des Artikels: {e}")
        return None
    
# Lade API-Daten aus der .env-Datei
load_dotenv()

# eBay API Konfiguration
EBAY_API_CONFIG = {
    'api': 'trading',
    'siteid': '77',
    'appid': os.getenv('EBAY_APP_ID'),
    'certid': os.getenv('EBAY_CERT_ID'),
    'devid': os.getenv('EBAY_DEV_ID'),
    'token': os.getenv('EBAY_TOKEN'),
    'sandbox': False
}

# Hauptprogramm
if __name__ == "__main__":
    print("eBay Artikelkopierer")
    print("====================")
    print("1. HTML-Beschreibung generieren")
    print("2. Neuen Artikelentwurf erstellen")
    print("3. Bestehenden Artikel überarbeiten")
    
    option = input("\nBitte wählen Sie eine Option (1-3): ")
    
    if option == "1":
        item_id = input("Bitte geben Sie die eBay-Artikel-ID ein: ")
        output_file = generate_ebay_listing_html(item_id)
        
        if output_file:
            print(f"Die HTML-Datei wurde erfolgreich erstellt: {output_file}")
        else:
            print("Fehler beim Erstellen der HTML-Datei.")
            
    elif option == "2":
        source_item_id = input("Bitte geben Sie die Quell-Artikel-ID ein: ")
        price_input = input("Preis (leer lassen für den Originalpreis): ")
        quantity_input = input("Menge (leer lassen für die Originalmenge): ")
        sku_input = input("SKU (leer lassen für automatische Generierung): ")
        
        start_price = float(price_input) if price_input else None
        quantity = int(quantity_input) if quantity_input else None
        sku = sku_input if sku_input else None
        
        draft_id = create_new_item_draft(source_item_id, start_price, quantity, sku)
        
        if draft_id:
            print(f"Der Artikelentwurf wurde erfolgreich erstellt. ItemID: {draft_id}")
        else:
            print("Fehler beim Erstellen des Artikelentwurfs.")
            
    elif option == "3":
        item_id = input("Bitte geben Sie die zu überarbeitende Artikel-ID ein: ")
        source_item_id = input("Bitte geben Sie die Quell-Artikel-ID ein: ")
        price_input = input("Preis (leer lassen für den aktuellen Preis): ")
        quantity_input = input("Menge (leer lassen für die aktuelle Menge): ")
        sku_input = input("SKU (leer lassen für die aktuelle SKU): ")
        
        start_price = float(price_input) if price_input else None
        quantity = int(quantity_input) if quantity_input else None
        sku = sku_input if sku_input else None
        
        revised_id = revise_item(item_id, source_item_id, start_price, quantity, sku)
        
        if revised_id:
            print(f"Der Artikel wurde erfolgreich überarbeitet. ItemID: {revised_id}")
        else:
            print("Fehler beim Überarbeiten des Artikels.")
            
    else:
        print("Ungültige Option. Bitte wählen Sie eine Zahl zwischen 1 und 3.")