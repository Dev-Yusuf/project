import re
from html.parser import HTMLParser

from django.test import TestCase
from django.urls import reverse

from history.models import HistoryArticle
from .kogi import PROFILES, boundaries, map_context


class MapMarkup(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.areas, self.panels, self.pressed = [], [], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'data-lga' in attrs:
            self.areas.append(attrs)
            if attrs.get('aria-pressed') == 'true':
                self.pressed.append(attrs['data-lga'])
        if tag == 'article' and attrs.get('class') == 'roots-place':
            self.panels.append(attrs)


class KogiMapTests(TestCase):
    def test_boundary_inventory_and_svg_geometry(self):
        data = boundaries()
        self.assertEqual(len(data['lgas']), 21)
        self.assertEqual(len({lga['id'] for lga in data['lgas']}), 21)
        self.assertEqual({lga['id'] for lga in data['lgas'] if lga['east']}, set(PROFILES))
        for lga in data['lgas']:
            self.assertRegex(lga['path'], r'^M[\d.,LZM]+Z$')
            points = re.findall(r'(\d+(?:\.\d+)?),(\d+(?:\.\d+)?)', lga['path'])
            self.assertTrue(points)
            self.assertTrue(all(0 <= float(x) <= 680 and 0 <= float(y) <= 620 for x, y in points))
        self.assertEqual(data['license'], 'CC BY 4.0')

    def test_default_has_nine_keyboard_controls_and_one_visible_panel(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)
        markup = MapMarkup(response.content.decode())
        self.assertEqual(len(markup.areas), 9)
        self.assertEqual(markup.pressed, ['idah'])
        self.assertEqual([p['id'] for p in markup.panels if 'hidden' not in p], ['place-idah'])
        for area in markup.areas:
            self.assertEqual(area['role'], 'button')
            self.assertEqual(area['tabindex'], '0')  # usable even without JavaScript
            self.assertIn('?lga=', area['href'])
        self.assertContains(response, 'Administrative boundaries, not language borders.')
        self.assertContains(response, 'GRID3 / geoBoundaries')

    def test_all_areas_can_be_opened_without_javascript(self):
        for key, (headquarters, _) in PROFILES.items():
            with self.subTest(key=key):
                response = self.client.get(reverse('about'), {'lga': key})
                markup = MapMarkup(response.content.decode())
                self.assertEqual(markup.pressed, [key])
                self.assertEqual([p['id'] for p in markup.panels if 'hidden' not in p], ['place-' + key])
                self.assertContains(response, headquarters)

    def test_invalid_or_hostile_area_falls_back_without_echoing_input(self):
        for invalid in ['', 'lokoja', 'missing', '<script>alert(1)</script>', 'x' * 4000]:
            response = self.client.get(reverse('about'), {'lga': invalid})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['kogi_selected'], 'idah')
            self.assertNotContains(response, '<script>alert(1)</script>')

    def test_stories_are_real_title_mentions_not_invented_place_associations(self):
        real = HistoryArticle.objects.create(title='Oral histories from Idah')
        HistoryArticle.objects.create(title='Ankpa traditions')
        HistoryArticle.objects.create(title='Idaho is a different place')
        HistoryArticle.objects.create(title='Igalamela/Odolu memories')
        with self.assertNumQueries(1):
            data = map_context()
        places = {p['id']: p for p in data['kogi_profiles']}
        self.assertEqual([s.pk for s in places['idah']['stories']], [real.pk])
        self.assertEqual(len(places['igalamela-odolu']['stories']), 1)
        self.assertEqual(places['bassa']['stories'], [])
        response = self.client.get(reverse('about'))
        self.assertContains(response, reverse('history_detail', args=[real.slug]))
        self.assertContains(response, 'Stories mentioning Idah')
