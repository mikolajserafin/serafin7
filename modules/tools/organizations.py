"""
Processes authority file, extract and enrich data about organizations.

Reads data/auxiliary/authorityLists.xml.
Saves to data/auxiliary/organizations.xml.
"""
from lxml import etree

ns = {"tei": "http://www.tei-c.org/ns/1.0"}

organizations_out_root = etree.parse('templates/organizations.xml')
input_root = etree.parse('../../data/auxiliary/authorityLists.xml')

# PLACES
out_organizations = organizations_out_root.xpath(".//tei:listOrg", namespaces=ns)[0]
organizations = input_root.xpath(".//tei:org", namespaces=ns)
for organization in organizations:
    print(f'Processing {organization.xpath("tei:orgName", namespaces=ns)[0].text}')
    out_organizations.append(organization)

organizations_out_root.write('../../data/auxiliary/organizations.xml', pretty_print=True, encoding='utf-8')
