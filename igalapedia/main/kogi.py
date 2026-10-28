"""Curated place context; administrative regions are not language boundaries.

Geometry, facts, licences, and editorial notes are documented in docs/KOGI_MAP.md.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

from django.db.models import Q


PROFILES = {
    'ankpa': ('Ankpa', 'At the eastern edge of Kogi, Ankpa is one of the nine local government areas in Kogi East.'),
    'bassa': ('Oguma', 'Bassa is part of multilingual Kogi East. Its inclusion here describes an administrative district, not an exclusively Igala-speaking area.'),
    'dekina': ('Dekina', 'Dekina includes Anyigba, alongside communities such as Iyale and Abocho. Its administrative headquarters is in Dekina town.'),
    'ibaji': ('Onyedega', 'Ibaji reaches the southern end of Kogi State. Its administrative headquarters is Onyedega.'),
    'idah': ('Idah', 'On the River Niger, Idah is the traditional capital of the Igala people and the seat of the Attah Igala.'),
    'igalamela-odolu': ('Ajaka', 'With its headquarters in Ajaka, Igalamela-Odolu lies alongside Idah in the southern part of Kogi East.'),
    'ofu': ('Ugwolawo', 'Ofu is one of the nine local government areas of Kogi East, with its administrative headquarters in Ugwolawo.'),
    'olamaboro': ('Okpo', 'Olamaboro lies in the south-east of Kogi State. Its administrative headquarters is Okpo.'),
    'omala': ('Abejukolo', 'Omala is in the north-eastern part of Kogi East, with its administrative headquarters in Abejukolo.'),
}


@lru_cache(maxsize=1)
def boundaries():
    return json.loads((Path(__file__).parent / 'data' / 'kogi_boundaries.json').read_text(encoding='utf-8'))


def map_context(selected='idah'):
    from history.models import HistoryArticle

    data = boundaries()
    # One bounded query; these are explicit title mentions, not inferred provenance.
    query = Q()
    for name in PROFILES:
        query |= Q(title__icontains=name.replace('-', ' '))
    query |= Q(title__icontains='Igalamela')
    stories = list(HistoryArticle.objects.filter(query).only('title', 'slug').order_by('-published_at')[:100])
    profiles = []
    for lga in data['lgas']:
        if not lga['east']:
            continue
        headquarters, overview = PROFILES[lga['id']]
        pattern = re.compile(r'(?<!\w)' + re.escape(lga['name']).replace(r'\-', r'[- /]') + r'(?!\w)', re.I)
        mentions = [story for story in stories if pattern.search(story.title)][:2]
        profiles.append({**lga, 'headquarters': headquarters, 'overview': overview, 'stories': mentions})
    return {'kogi_map': data, 'kogi_profiles': profiles,
            'kogi_selected': selected if selected in PROFILES else 'idah'}
