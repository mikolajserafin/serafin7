"""
Processes authority file, extract and enrich data about places.
Adjust geonames user before execution.

Reads data/auxiliary/authorityLists.xml.
Saves to data/auxiliary/places.xml.
"""
import requests
from lxml import etree

######################################
geonames_user = 'your_geonames_user'
######################################


ns = {"tei": "http://www.tei-c.org/ns/1.0"}

places_data = {}
with open('input/places.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.split('|')
        document_id = parts[0].strip()
        wikidata = parts[1].strip()
        geonames = parts[2].strip()

        places_data[document_id] = {
            'wikidata': wikidata,
            'geonames': '/'.join(geonames.split('/')[:-1]) if geonames else None,
            'geonames_id': geonames.split('/')[-2] if geonames else None,
        }

places_out_root = etree.parse('templates/places.xml')
input_root = etree.parse('../../data/auxiliary/authorityLists.xml')

# PLACES
out_places = places_out_root.xpath(".//tei:listPlace", namespaces=ns)[0]
places = input_root.xpath(".//tei:place", namespaces=ns)
for place in places:
    place_name = place.xpath("tei:placeName", namespaces=ns)[0]
    place_id = place.attrib["{http://www.w3.org/XML/1998/namespace}id"]

    print(f'Processing {place_name.text}')

    # add type to existing placeName
    place_name.attrib['type'] = 'main'

    # placeName type=sort
    place_name_with_sort = etree.Element("placeName")
    place_name_with_sort.attrib['type'] = 'sort'
    place_name_with_sort.text = place_name.text
    place.insert(1, place_name_with_sort)

    # add geonames
    if places_data[place_id]['geonames_id']:
        g = requests.get('http://api.geonames.org/getJSON', params={
            'geonameId': places_data[place_id]['geonames_id'],
            'username': geonames_user,
            'style': 'full',
        }).json()

        if g['countryName']:
            country = etree.Element("country")
            country.text = g['countryName']
            place.append(country)

        if g['adminName1']:
            region = etree.Element("region")
            region.text = g['adminName1']
            place.append(region)

        place_geo = place.xpath('tei:location/tei:geo', namespaces=ns)[0]
        if not place_geo.text and g['lat'] and g['lng']:
            place_geo.text = f"{g['lat']} {g['lng']}"

        ptr_geonames = etree.Element("ptr")
        ptr_geonames.attrib['type'] = f"geonames"
        ptr_geonames.attrib['target'] = places_data[place_id]['geonames']
        place.append(ptr_geonames)

    # add wikidata
    ptr_wikidata = etree.Element("ptr")
    ptr_wikidata.attrib['type'] = f"wikidata"
    ptr_wikidata.attrib['target'] = places_data[place_id]['wikidata']
    place.append(ptr_wikidata)

    out_places.append(place)

places_out_root.write('../../data/auxiliary/places.xml', pretty_print=True, encoding='utf-8')
