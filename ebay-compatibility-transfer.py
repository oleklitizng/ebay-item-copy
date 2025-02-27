import requests
import re
import html

# eBay API Configuration
EBAY_API_URL = "https://api.ebay.com/ws/api.dll"
EBAY_AUTH_TOKEN = "v^1.1#i^1#p^3#f^0#r^1#I^3#t^Ul4xMF8zOjUzODRCOUY2NkFFQkQ0QzZDNDNCNzk2NDkzMERBQjFEXzFfMSNFXjI2MA=="

def get_compatibility_list(source_item_id):
    """Fetch compatibility list from source item"""
    
    xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
<GetItemRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
        <eBayAuthToken>{EBAY_AUTH_TOKEN}</eBayAuthToken>
    </RequesterCredentials>
    <ErrorLanguage>en_US</ErrorLanguage>
    <WarningLevel>High</WarningLevel>
    <ItemID>{source_item_id}</ItemID>
    <DetailLevel>ReturnAll</DetailLevel>
    <IncludeItemSpecifics>true</IncludeItemSpecifics>
    <IncludeItemCompatibilityList>true</IncludeItemCompatibilityList>
</GetItemRequest>"""

    headers = {
        "X-EBAY-API-CALL-NAME": "GetItem",
        "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
        "X-EBAY-API-SITEID": "77",  # Deutschland
        "X-EBAY-API-IAF-TOKEN": EBAY_AUTH_TOKEN,
        "Content-Type": "text/xml"
    }

    try:
        response = requests.post(EBAY_API_URL, headers=headers, data=xml_request)
        response_content = response.text
        
        # Extract ItemCompatibilityList section
        start_tag = '<ItemCompatibilityList>'
        end_tag = '</ItemCompatibilityList>'
        
        start_pos = response_content.find(start_tag)
        end_pos = response_content.find(end_tag) + len(end_tag)
        
        if start_pos == -1 or end_pos == -1:
            raise Exception("Keine Compatibility List in der Quelle gefunden!")
            
        compatibility_list = response_content[start_pos:end_pos]
        
        # Fix special characters in the compatibility list
        compatibility_list = html.unescape(compatibility_list)
        
        return compatibility_list
        
    except Exception as e:
        print(f"Fehler beim Abrufen der Compatibility List: {str(e)}")
        return None

def transfer_compatibility_list(target_item_id, compatibility_list):
    """Transfer compatibility list to target item"""
    
    xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
<ReviseItemRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
        <eBayAuthToken>{EBAY_AUTH_TOKEN}</eBayAuthToken>
    </RequesterCredentials>
    <Item>
        <ItemID>{target_item_id}</ItemID>
        {compatibility_list}
    </Item>
</ReviseItemRequest>"""

    headers = {
        "X-EBAY-API-CALL-NAME": "ReviseItem",
        "X-EBAY-API-SITEID": "77",
        "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
        "X-EBAY-API-REQUEST-ENCODING": "XML",
        "X-EBAY-API-RESPONSE-ENCODING": "XML",
        "Content-Type": "text/xml;charset=utf-8"
    }

    try:
        # Encode with utf-8 to properly handle special characters
        xml_request_encoded = xml_request.encode('latin')
        
        response = requests.post(EBAY_API_URL, headers=headers, data=xml_request_encoded)
        print("\nAPI Response Status:", response.status_code)
        
        if response.status_code == 200:
            print("Compatibility List wurde erfolgreich übertragen!")
        else:
            print("Fehler beim Übertragen der Compatibility List.")
            print("API Response:", response.text)
            
    except Exception as e:
        print(f"Fehler beim Übertragen der Compatibility List: {str(e)}")

def main():
    print("=== eBay Compatibility List Transfer ===")
    
    # Get source and target item IDs
    source_item_id = input("Bitte geben Sie die Quell-Item-ID ein: ")
    target_item_id = input("Bitte geben Sie die Ziel-Item-ID ein: ")
    
    print("\nHole Compatibility List von Item", source_item_id, "...")
    compatibility_list = get_compatibility_list(source_item_id)
    
    if compatibility_list:
        print("Compatibility List erfolgreich geholt!")
        print("\nÜbertrage Compatibility List zu Item", target_item_id, "...")
        transfer_compatibility_list(target_item_id, compatibility_list)
    else:
        print("Übertragung abgebrochen aufgrund von Fehlern.")

if __name__ == "__main__":
    main()