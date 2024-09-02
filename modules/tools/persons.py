"""
Processes authority file, extract and enrich data about persons.

Reads data/auxiliary/authorityLists.xml.
Saves to data/auxiliary/persons.xml.
"""
import datetime

import requests
from wikidata.client import Client
from lxml import etree
from wikidata.datavalue import DatavalueError

ns = {"tei": "http://www.tei-c.org/ns/1.0", "marc": "http://www.loc.gov/MARC21/slim",
      "dnb": "http://www.loc.gov/zing/srw/"}

persons_out_root = etree.parse('templates/persons.xml')
input_root = etree.parse('../../data/auxiliary/authorityLists.xml')

wd_client = Client()

gender_mapping = {
    '1': {
        'value': 'M',
        'text': 'male',
    },
    '2': {
        'value': 'F',
        'text': 'female'
    }
}

persons_data = {}
with open('input/persons.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.split('|')
        document_id = parts[0].strip()
        wikidata = parts[1].strip() if len(parts) >= 2 else None
        dnb = parts[2].strip() if len(parts) >= 3 else None

        persons_data[document_id] = {
            'wikidata': wikidata,
            'wikidata_id': wikidata.split('/')[-1] if wikidata else None,
            'dnb': dnb,
            'dnb_id': dnb.split('/')[-1] if dnb else None,
        }

# PERSONS
out_persons = persons_out_root.xpath(".//tei:listPerson", namespaces=ns)[0]
persons = input_root.xpath(".//tei:person", namespaces=ns)
for person in persons:
    person_name = person.xpath("tei:persName", namespaces=ns)[0]
    person_id = person.attrib["{http://www.w3.org/XML/1998/namespace}id"]
    print(f'Processing {person_name.text} ({person_id})')

    # add type to existing persName
    person_name.attrib['type'] = 'main'

    # biographical note
    person_note = person.xpath("tei:note", namespaces=ns)[0]
    person_note.attrib['type'] = 'bio'

    person_details = {
        'gender': None,
        'birth': None,
        'death': None,
        'name_variants': set(),
        'occupations': [],
    }

    # getting data first from Wikidata, then adding from DNB
    if persons_data[person_id]['wikidata_id']:
        wikidata_person = wd_client.get(persons_data[person_id]['wikidata_id'], load=True)

        # gender
        if wd_client.get('P21') in wikidata_person:
            if wikidata_person[wd_client.get('P21')].label['en'] == 'male':
                person_details['gender'] = '1'
            elif wikidata_person[wd_client.get('P21')].label['en'] == 'female':
                person_details['gender'] = '2'

        # date of birth
        try:
            if wd_client.get('P569') in wikidata_person:
                date_val = wikidata_person[wd_client.get('P569')]
                if isinstance(date_val, datetime.date):
                    person_details['birth'] = date_val.strftime("%Y-%m-%d")
                elif isinstance(date_val, int):
                    person_details['birth'] = str(date_val)
                elif isinstance(date_val, tuple):
                    person_details['death'] = '-'.join([str(v) for v in date_val])
                else:
                    raise ValueError('Unknown date format')
        except DatavalueError as e:
            date_val = e.datavalue['value']['time'].lstrip('+').split('T')[0].split('-')
            person_details['birth'] = '-'.join([v for v in date_val if v != '00'])

        # date of death
        try:
            if wd_client.get('P570') in wikidata_person:
                date_val = wikidata_person[wd_client.get('P570')]

                if isinstance(date_val, datetime.date):
                    person_details['death'] = date_val.strftime("%Y-%m-%d")
                elif isinstance(date_val, int):
                    person_details['death'] = str(date_val)
                elif isinstance(date_val, tuple):
                    person_details['death'] = '-'.join([str(v) for v in date_val])
                else:
                    raise ValueError('Unknown date format')
        except DatavalueError as e:
            date_val = e.datavalue['value']['time'].lstrip('+').split('T')[0].split('-')
            person_details['death'] = '-'.join([v for v in date_val if v != '00'])

        # name variants
        for lang, aliases in wikidata_person.attributes['aliases'].items():
            for alias in aliases:
                person_details['name_variants'].add(alias['value'])

        for lang, label in wikidata_person.attributes['labels'].items():
            person_details['name_variants'].add(label['value'])

        # occupations
        if wd_client.get('P106') in wikidata_person:
            for occupation in wikidata_person.getlist(wd_client.get('P106')):
                person_details['occupations'].append({
                    'value': occupation.label['en'],
                    'ref': f"https://www.wikidata.org/wiki/{occupation.data['title']}",
                })

    if persons_data[person_id]['dnb']:
        response = requests.get(f'https://services.dnb.de/sru/authorities', params={
            'version': '1.1',
            'operation': 'searchRetrieve',
            'recordSchema': 'MARC21-xml',
            'query': f"nid={persons_data[person_id]['dnb_id']}"
        })

        dnb_record = etree.fromstring(response.content).xpath("//dnb:recordData", namespaces=ns)[0]

        # gender
        if not person_details['gender']:
            dnb_gender = dnb_record.xpath("//marc:datafield[@tag='375']/marc:subfield[@code='a']", namespaces=ns)
            if dnb_gender:
                person_details['gender'] = dnb_gender[0].text

        # birth date and place (where available)
        # death date and place (where available)
        # taking only dates like: 1900-2000, -2000, 2000-, there are others like: "ur 2000" but they're not considered
        dnb_dates = dnb_record.xpath("//marc:datafield[@tag='100']/marc:subfield[@code='d']", namespaces=ns)
        if dnb_dates and '-' in dnb_dates[0].text:
            dates = dnb_dates[0].text
            dates_parts = dates.split('-')
            birthdate = ''
            death = ''

            if len(dates_parts) == 2:
                birthdate = dates_parts[0]
                death = dates_parts[1]
            elif dates.startswith('-'):
                death = dates_parts[0]
            elif dates.endswith('-'):
                birthdate = dates_parts[0]

            birthdate = birthdate if 'x' not in birthdate.lower() else ''
            death = death if 'x' not in death.lower() else ''

            if not person_details['birth'] and birthdate:
                person_details['birth'] = birthdate

            if not person_details['death'] and death:
                person_details['death'] = death

        # name variants
        dnb_sort_name = dnb_record.xpath("//marc:datafield[@tag='100']/marc:subfield", namespaces=ns)
        if dnb_sort_name:
            sort_name_parts = []
            for subfield in dnb_sort_name:
                if subfield.attrib['code'] in ['a', 'b', 'c']:
                    sort_name_parts.append(subfield.text)

            person_details['name_variants'].add(' '.join(sort_name_parts))

        dnb_name_variants = dnb_record.xpath("//marc:datafield[@tag='400']", namespaces=ns)
        if dnb_name_variants:
            for dnb_name_variant in dnb_name_variants:
                name_variant_parts = []
                for subfield in dnb_name_variant:
                    if subfield.attrib['code'] in ['a', 'b', 'c']:
                        name_variant_parts.append(subfield.text)

                person_details['name_variants'].add(' '.join(name_variant_parts))

        # occupation with references to gnd profession ontology (cf example below)
        # trying to take english name of the occupation if not available taking first 750 field
        dnb_occupations = dnb_record.xpath("//marc:datafield[@tag='550']/marc:subfield[@code='0']", namespaces=ns)
        if dnb_occupations:
            for dnb_occupation in dnb_occupations:
                if 'http' in dnb_occupation.text:
                    dnb_occupation_url = dnb_occupation.text
                    occupation_id = dnb_occupation_url.split('/')[-1]

                    response = requests.get(f'https://services.dnb.de/sru/authorities', params={
                        'version': '1.1',
                        'operation': 'searchRetrieve',
                        'recordSchema': 'MARC21-xml',
                        'query': occupation_id
                    })

                    dnb_occupation_record = etree.fromstring(response.content)
                    dnb_occupation_names = dnb_occupation_record.xpath("//marc:datafield[@tag='750']", namespaces=ns)

                    found_occupation_names = {}
                    for index, dnb_occupation_name in enumerate(dnb_occupation_names):
                        occupation_index = index
                        occupation_name = None
                        for subfield in dnb_occupation_name:
                            if subfield.attrib['code'] == 'a':
                                occupation_name = subfield.text
                            elif subfield.attrib['code'] == '9':
                                occupation_index = subfield.text

                        if occupation_name:
                            found_occupation_names[occupation_index] = occupation_name

                    if found_occupation_names:
                        person_details['occupations'].append({
                            'value': found_occupation_names['L:eng'] if 'L:eng' in found_occupation_names else next(
                                iter(found_occupation_names.values())),
                            'ref': dnb_occupation_url,
                        })

    # build elements
    if person_details['gender']:
        gender = etree.Element("gender")
        gender.text = gender_mapping[person_details['gender']]['text']
        gender.attrib['value'] = gender_mapping[person_details['gender']]['value']
        person.append(gender)

    if person_details['birth']:
        birth_el = etree.Element("birth")
        date_el = etree.Element("date")
        date_el.attrib['when'] = person_details['birth']
        birth_el.append(date_el)
        person.append(birth_el)

    if person_details['death']:
        death_el = etree.Element("death")
        date_el = etree.Element("date")
        date_el.attrib['when'] = person_details['death']
        death_el.append(date_el)
        person.append(death_el)

    if person_details['name_variants']:
        person_details['name_variants'].discard(person_name.text)
        for name_variant in person_details['name_variants']:
            name_variant_el = etree.Element("persName")
            name_variant_el.text = name_variant
            name_variant_el.attrib['type'] = 'variant'
            person.append(name_variant_el)

    if persons_data[person_id]['wikidata']:
        link = etree.Element("ptr")
        link.attrib['type'] = 'wikidata'
        link.attrib['target'] = persons_data[person_id]['wikidata']
        person.append(link)

    if persons_data[person_id]['dnb']:
        link = etree.Element("ptr")
        link.attrib['type'] = 'gnd'
        link.attrib['target'] = persons_data[person_id]['dnb']
        person.append(link)

    if person_details['occupations']:
        for occupation in person_details['occupations']:
            occupation_el = etree.Element("occupation")
            occupation_el.text = occupation['value']
            occupation_el.attrib['ref'] = occupation['ref']
            person.append(occupation_el)

    out_persons.append(person)

persons_out_root.write('../../data/auxiliary/persons.xml', pretty_print=True, encoding='utf-8')
