import feedparser
import json
import xml.etree.ElementTree as ET
import os
import html
import email.utils, time

# Helper - pretty print xml with proper formatting
def prettify(elem):
    xml_bytes = ET.tostring(elem, encoding="utf-8", xml_declaration=True, method='xml')
    xml_str = xml_bytes.decode("utf-8")
    xml_str = xml_str.replace('><', '>\n<')
    return xml_str.strip()

# Custom unescape to handle special XML/HTML character & numeric entities
def clean_text_for_xml(text):
    if not isinstance(text, str):
        return text
    # Unescape HTML entities (e.g. &amp; -> &)
    cleaned = html.unescape(text)
    # Remove illegal XML chars: https://stackoverflow.com/a/25920330
    def strip_illegal(xml_str):
        # Allow: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
        def valid_xml_char_ordinal(c):
            code = ord(c)
            return (
                code == 0x9 or code == 0xA or code == 0xD or
                (0x20 <= code <= 0xD7FF) or
                (0xE000 <= code <= 0xFFFD) or
                (0x10000 <= code <= 0x10FFFF)
            )
        return ''.join(c for c in xml_str if valid_xml_char_ordinal(c))
    cleaned = strip_illegal(cleaned)
    return cleaned.strip()

# Feed configurations: mapping name to info
feeds = {
    "vontobel": {
        "rss_url": "https://cdn.reputation.onclusive.com/Rss.aspx?crypt=914A6D7552F78E98E738E18676772F46B295FF7226540263A18247662BA78B9A",
        "xml_name": "vontobel_rss_feed.xml",
        "seen_ids_name": "seen_ids_vontobel.json",
        "site_title": "Vontobel RSS Feed",
    },
    "comgest": {
        "rss_url": "https://cdn.reputation.onclusive.com/Rss.aspx?crypt=C2C7A48D17D8CA1D072615A0205169284FBD18E8D839F9F11E3287FB352BD489",
        "xml_name": "comgest_rss_feed.xml",
        "seen_ids_name": "seen_ids_comgest.json",
        "site_title": "Comgest RSS Feed",
    },
    "bankhaus_bauer": {
        "rss_url": "https://cdn.reputation.onclusive.com/Rss.aspx?crypt=4A505AFEA8726BE9909F93BFD8DCC92BFEBC18065DDBCB68367935420C9DD8A2",
        "xml_name": "bankhaus_bauer_rss_feed.xml",
        "seen_ids_name": "seen_ids_bankhaus_bauer.json",
        "site_title": "Bankhaus Bauer RSS Feed",
    },
    "goodwin": {
        "rss_url": "https://cdn.reputation.onclusive.com/Rss.aspx?crypt=3936910317E6CF0430D32C55E9AC5BC1E6CC1E71D0FC79E90CD6D98022F52D92",
        "xml_name": "goodwin_rss_feed.xml",
        "seen_ids_name": "seen_ids_goodwin.json",
        "site_title": "Goodwin RSS Feed",
    },  
    "alken_fund": {
        "rss_url": "https://cdn.reputation.onclusive.com/Rss.aspx?crypt=32B7B668ABE50B0856D09DC7D72CA1555336A1ABBAEA699823DDB96A595B5443",
        "xml_name": "alken_fund_rss_feed.xml",
        "seen_ids_name": "seen_ids_alken_fund.json",
        "site_title": "Alken Fund RSS Feed",
    },
    "multitude_se": {
        "rss_url": "https://cdn.reputation.onclusive.com/Rss.aspx?crypt=14D1989EB96679B0EEA61D40DB85F47BCE4368742A77DC9AFC82E7BCCDB895C9",
        "xml_name": "multitude_se_rss_feed.xml",
        "seen_ids_name": "seen_ids_multitude_se.json",
        "site_title": "Multitude SE RSS Feed",
    },
    "robus_capital": {
        "rss_url": "https://cdn.reputation.onclusive.com/Rss.aspx?crypt=59DB29A4D56CE6A0D3B6946155AAEA5A4BBD0972C3AB64811A58EE282BE4DB42",
        "xml_name": "robus_capital_rss_feed.xml",
        "seen_ids_name": "seen_ids_robus_capital.json",
        "site_title": "Robus Capital RSS Feed",
    },
}

def get_xml_dir():
    xml_dir = os.path.join(os.getcwd(), 'feeds')
    os.makedirs(xml_dir, exist_ok=True)
    return xml_dir

def get_seen_ids_dir():
    seen_ids_dir = os.path.join(os.getcwd(), 'seen_ids')
    os.makedirs(seen_ids_dir, exist_ok=True)
    return seen_ids_dir

def get_xml_path(filename):
    return os.path.join(get_xml_dir(), filename)

def get_seen_ids_path(filename):
    return os.path.join(get_seen_ids_dir(), filename)

# Extract only basic, important fields for output xml
def extract_simple_fields(entry):
    def norm(s):
        return s.strip() if isinstance(s, str) else s

    # idClip is the true unique id
    id_clip = (
        entry.get("kmplusitem_idclip")
        or entry.get("kmplusItem_idClip")
        or entry.get("idclip")
        or entry.get("idClip")
    )
    # Sometimes it is deeply nested under 'tags'
    if not id_clip:
        # Try tags if present
        if "tags" in entry:
            for tag in entry["tags"]:
                term = tag.get("term", "")
                if "idclip" in term.lower():
                    # try to parse e.g. "kmplusItem:idClip=DE2139867_1000024-5184397633"
                    if "=" in term:
                        _, v = term.split("=", 1)
                        id_clip = v.strip()
                        break
    id_clip = norm(id_clip) if id_clip else None

    # title
    title = entry.get("title")
    if not title and "title_detail" in entry:
        title = entry.get("title_detail", {}).get("value")
    title = norm(title) if title else None

    # link
    link = entry.get("link")
    if not link and isinstance(entry.get('links'), list) and entry['links']:
        link = entry['links'][0].get('href')
    link = norm(link) if link else None

    # author (use <kmplusItem:source>)
    author = entry.get('kmplusitem_source') or entry.get('kmplusItem_source')
    author = norm(author) if author else None

    # description / summary
    description = entry.get("description") or entry.get("summary")
    description = norm(description) if description else None

    # pubDate
    pubdate = entry.get('pubDate') or entry.get('published') or entry.get('pubdate')
    if not pubdate:
        # Sometimes present in entry.keys() with a diff case
        for k in entry.keys():
            if k.lower() == 'pubdate':
                pubdate = entry[k]
    pubdate = norm(pubdate) if pubdate else None

    # Clean title and description of HTML and XML entities and non-printables
    cleaned_title = clean_text_for_xml(title) if title else ""
    cleaned_desc = clean_text_for_xml(description) if description else ""

    return {
        "idClip": id_clip or "",
        "title": cleaned_title,
        "link": link or "",
        "author": author or "",
        "description": cleaned_desc,
        "pubDate": pubdate or "",
    }


for feed_key, config in feeds.items():
    rss_url = config["rss_url"]
    xml_name = config["xml_name"]
    seen_ids_name = config["seen_ids_name"]
    site_title = config["site_title"]
    xml_path = get_xml_path(xml_name)
    seen_ids_path = get_seen_ids_path(seen_ids_name)

    # Load previously seen idClips (to keep items unique by idClip)
    if os.path.exists(seen_ids_path):
        with open(seen_ids_path, "r") as f:
            try:
                loaded_ids = json.load(f)
                if loaded_ids is None or loaded_ids == [None]:
                    seen_ids = set()
                else:
                    seen_ids = set(loaded_ids)
            except Exception:
                seen_ids = set()
    else:
        seen_ids = set()

    # Load existing items from XML (preserving order), mapping idClip → item data dict
    existing_items_dict = {}  # idClip -> Element
    existing_items_list = []  # List of dicts to preserve XML order (oldest-to-newest)

    if os.path.exists(xml_path):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            ch = root.find('channel')
            if ch is not None:
                for item_elem in ch.findall('item'):
                    # Extract idClip from guid
                    guid_elem = item_elem.find('guid')
                    if guid_elem is not None and guid_elem.text:
                        id_clip = guid_elem.text.strip()
                    else:
                        continue
                    # For fields: title, link, author, description, pubDate
                    entry = {
                        'idClip': id_clip,
                        'title': (item_elem.find('title').text or "") if item_elem.find('title') is not None else "",
                        'link': (item_elem.find('link').text or "") if item_elem.find('link') is not None else "",
                        'author': (item_elem.find('author').text or "") if item_elem.find('author') is not None else "",
                        'description': (item_elem.find('description').text or "") if item_elem.find('description') is not None else "",
                        'pubDate': (item_elem.find('pubDate').text or "") if item_elem.find('pubDate') is not None else "",
                    }
                    existing_items_list.append(entry)
                    existing_items_dict[id_clip] = entry
        except Exception:
            # If parsing fails, treat as empty
            existing_items_dict = {}
            existing_items_list = []

    feed = feedparser.parse(rss_url)
    new_items = []
    new_item_dicts = []
    # Use idClip as the true unique id for all logic
    for entry in feed.entries:
        data = extract_simple_fields(entry)
        item_id = data["idClip"]
        if not item_id:
            continue  # skip if no idClip
        if (item_id not in seen_ids) and (item_id not in existing_items_dict):
            new_items.append(data)
            new_item_dicts.append(data)

    # Compose the items to write: newest items on top
    # The order: [newest (from this run), ... oldest (from previous runs)]
    # New items: order as in feedparser parsing (most recent on top, as feed usually provides)
    # So: new_items (in order they were collected, which is newest first), then existing_items_list (oldest to newest)
    # But ensure we don't duplicate IDs
    all_items = []
    written_ids = set()  # To track already written ids

    # First, write new items (from *this* run only)
    for data in new_items:
        all_items.append(data)
        written_ids.add(data['idClip'])

    # Now, append older items (preserving original XML order), skipping any id written above
    for data in existing_items_list:
        if data['idClip'] not in written_ids:
            all_items.append(data)
            written_ids.add(data['idClip'])

    # If there are no new nor old, just create empty channel
    rss_elem = ET.Element('rss', {'version': '2.0'})
    channel = ET.SubElement(rss_elem, 'channel')
    ET.SubElement(channel, 'title').text = site_title
    ET.SubElement(channel, 'link').text = rss_url
    ET.SubElement(channel, 'description').text = site_title
    #ET.SubElement(channel, 'lastBuildDate').text = email.utils.formatdate(time.time())

    for data in all_items:
        item = ET.SubElement(channel, 'item')
        idclip_val = data['idClip']
        if idclip_val:
            guid = ET.SubElement(item, 'guid')
            guid.text = idclip_val
            guid.attrib['isPermaLink'] = "false"
        title_cleaned = clean_text_for_xml(data['title'] or "")
        desc_cleaned = clean_text_for_xml(data['description'] or "")

        ET.SubElement(item, 'title').text = title_cleaned
        ET.SubElement(item, 'link').text = data['link'] or ""
        if data['author']:
            ET.SubElement(item, 'author').text = data['author']
        if desc_cleaned:
            ET.SubElement(item, 'description').text = desc_cleaned
        if data['pubDate']:
            ET.SubElement(item, 'pubDate').text = data['pubDate']

    xmlstr = prettify(rss_elem)
    if not xmlstr.startswith('<?xml'):
        xmlstr = '<?xml version="1.0" encoding="utf-8"?>\n' + xmlstr

    with open(xml_path, "w", encoding="utf-8", newline='\n') as f:
        f.write(xmlstr)

    # Update seen_ids with all ids seen so far + any new ones we just wrote.
    updated_seen_ids = set(seen_ids)
    updated_seen_ids.update([data['idClip'] for data in new_items])
    with open(seen_ids_path, "w") as f:
        json.dump(sorted(updated_seen_ids), f, indent=2, ensure_ascii=False)