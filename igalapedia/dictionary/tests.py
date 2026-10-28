from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models.query import QuerySet
from django.test import RequestFactory, TestCase
from django.urls import reverse, resolve

from .admin import PendingWordAdmin
from .models import (
    ContributionStats, Example, Meaning, PartOfSpeech,
    PendingExample, PendingMeaning, PendingWord, Words,
)


class WordApprovalTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='contributor')
        self.reviewer = get_user_model().objects.create_user(username='reviewer', is_staff=True)
        self.submission = PendingWord.objects.create(word='Testword', submitted_by=self.user)
        part = PartOfSpeech.objects.create(name='Noun')
        meaning = PendingMeaning.objects.create(
            pending_word=self.submission, meaning='A meaning', part_of_speech=part,
        )
        PendingExample.objects.create(
            pending_meaning=meaning, igala_example='Example', english_meaning='Translation',
        )
        self.stats = ContributionStats.objects.create(user=self.user)
        self.stats.update_stats()

    def assert_rolled_back(self):
        self.submission.refresh_from_db()
        self.stats.refresh_from_db()
        self.assertEqual(self.submission.status, 'PENDING')
        self.assertIsNone(self.submission.approved_word_id)
        self.assertIsNone(self.submission.reviewed_at)
        self.assertEqual(self.stats.approved_words_count, 0)
        self.assertEqual(self.stats.pending_words_count, 1)
        self.assertFalse(Words.objects.exists())
        self.assertFalse(Meaning.objects.exists())
        self.assertFalse(Example.objects.exists())

    def test_approval_publishes_complete_submission_and_stats(self):
        word = self.submission.approve(self.reviewer)
        meaning = word.meanings.get()
        self.assertEqual(meaning.meaning, 'A meaning')
        self.assertEqual(meaning.examples.get().english_meaning, 'Translation')
        self.submission.refresh_from_db()
        self.stats.refresh_from_db()
        self.assertEqual(self.submission.status, 'APPROVED')
        self.assertEqual(self.submission.approved_word, word)
        self.assertEqual(self.submission.reviewed_by, self.reviewer)
        self.assertEqual(self.stats.approved_words_count, 1)
        self.assertEqual(self.stats.pending_words_count, 0)

    def test_failures_roll_back_every_part_of_approval(self):
        for target in ('Meaning.objects.create', 'Example.objects.create',
                       'PendingWord.save', 'ContributionStats.update_stats'):
            with self.subTest(target=target):
                with patch('dictionary.models.' + target, side_effect=RuntimeError('Failure')):
                    with self.assertRaises(RuntimeError):
                        self.submission.approve(self.reviewer)
                self.assert_rolled_back()

    def test_integrity_failure_in_children_is_not_treated_as_duplicate(self):
        with patch('dictionary.models.Example.objects.create', side_effect=IntegrityError('Failure')):
            with self.assertRaises(IntegrityError):
                self.submission.approve(self.reviewer)
        self.assert_rolled_back()

    def test_stale_pending_instance_cannot_approve_twice(self):
        stale = PendingWord.objects.get(pk=self.submission.pk)
        self.submission.approve(self.reviewer)
        self.assertIsNone(stale.approve(self.reviewer))
        self.assertEqual(Words.objects.count(), 1)
        self.assertEqual(Meaning.objects.count(), 1)
        self.assertEqual(Example.objects.count(), 1)

    def test_real_duplicate_is_rejected_and_stats_updated(self):
        Words.objects.create(word=self.submission.word)
        self.assertIsNone(self.submission.approve(self.reviewer))
        self.submission.refresh_from_db()
        self.stats.refresh_from_db()
        self.assertEqual(self.submission.status, 'REJECTED')
        self.assertIn('Duplicate', self.submission.review_notes)
        self.assertEqual(self.stats.rejected_words_count, 1)
        self.assertFalse(Meaning.objects.exists())

    def test_slug_collision_does_not_reject_a_distinct_word(self):
        Words.objects.create(word='Testword!')
        word = self.submission.approve(self.reviewer)
        self.assertEqual(word.slug, 'testword-2')
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, 'APPROVED')
        self.assertEqual(word.meanings.get().examples.count(), 1)

    def test_admin_defers_approval_email_until_commit(self):
        model_admin = PendingWordAdmin(PendingWord, admin.site)
        request = RequestFactory().post('/admin/dictionary/pendingword/')
        request.user = self.reviewer
        with patch.object(model_admin, 'message_user'), patch(
            'dictionary.emails.send_word_approved_email'
        ) as send_email:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                model_admin.approve_submissions(
                    request, PendingWord.objects.filter(pk=self.submission.pk),
                )
                send_email.assert_not_called()
                self.assertEqual(Meaning.objects.count(), 1)
                self.assertEqual(Example.objects.count(), 1)
            self.assertEqual(len(callbacks), 1)
            send_email.assert_called_once()


class WordSlugTests(TestCase):
    def test_accents_and_punctuation_get_distinct_urls(self):
        words = [Words.objects.create(word=text) for text in ('Oko', 'Óko', 'Oko!')]
        self.assertEqual([word.slug for word in words], ['oko', 'oko-2', 'oko-3'])
        for word in words:
            match = resolve(reverse('single-word', kwargs={'slug': word.slug}))
            self.assertEqual(Words.objects.get(slug=match.kwargs['slug']), word)

    def test_words_without_ascii_slug_characters_have_nonempty_urls(self):
        first = Words.objects.create(word='!!!')
        second = Words.objects.create(word='???')
        self.assertEqual(first.slug, 'word')
        self.assertEqual(second.slug, 'word-2')

    def test_collision_suffix_fits_maximum_length(self):
        first = Words.objects.create(word='a' * 100)
        second = Words.objects.create(word='a' * 99 + '!')
        third = Words.objects.create(word='a' * 99 + '?')
        fourth = Words.objects.create(word='a' * 99 + '.')
        self.assertEqual(len(first.slug), 100)
        self.assertEqual(third.slug, 'a' * 98 + '-2')
        self.assertEqual(fourth.slug, 'a' * 98 + '-3')
        self.assertEqual(len({w.slug for w in (first, second, third, fourth)}), 4)

    def test_existing_urls_remain_stable_when_word_changes(self):
        word = Words.objects.create(word='Original', slug='established-url')
        word.word = 'Changed'
        word.save()
        word.refresh_from_db()
        self.assertEqual(word.slug, 'established-url')

    def test_duplicate_words_still_raise_integrity_error(self):
        Words.objects.create(word='Duplicate')
        with self.assertRaises(IntegrityError):
            Words.objects.create(word='Duplicate')
        self.assertEqual(Words.objects.count(), 1)

    def test_retries_if_candidate_is_taken_after_availability_check(self):
        Words.objects.create(word='Oko')
        original_exists = QuerySet.exists
        missed_check = False

        def miss_first_check(queryset):
            nonlocal missed_check
            if queryset.model is Words and not missed_check:
                missed_check = True
                return False
            return original_exists(queryset)

        # Simulate the stale availability result from a competing transaction;
        # the real database constraint then rejects the first INSERT.
        with patch.object(QuerySet, 'exists', miss_first_check):
            word = Words.objects.create(word='Óko')
        self.assertEqual(word.slug, 'oko-2')
        self.assertEqual(Words.objects.count(), 2)


class RelatedTermEscapingTests(TestCase):
    def test_linked_and_unlinked_terms_escape_user_html(self):
        from django.template import Context, Template
        from .templatetags.dictionary_extras import create_word_link, related_terms_html
        malicious = '<img src=x onerror=attack()>'
        Words.objects.create(word=malicious)
        linked = str(create_word_link(malicious))
        self.assertIn('&lt;img', linked)
        self.assertNotIn('<img', linked)
        result = str(related_terms_html(malicious + ', <script>attack()</script>'))
        self.assertNotIn('<script>', result)
        self.assertNotIn('<img', result)
        rendered = Template('{% load dictionary_extras %}{{ term|create_word_link }}').render(
            Context({'term': '<script>missing()</script>'}))
        self.assertNotIn('<script>', rendered)


class LeaderboardQueryTests(TestCase):
    def test_leaderboard_uses_current_submissions_in_one_query(self):
        from .views import leaderboard
        for i in range(5):
            user = get_user_model().objects.create_user(username=f'leader{i}')
            PendingWord.objects.create(word=f'Entry{i}', submitted_by=user, status='APPROVED')
        request = RequestFactory().get('/dictionary/leaderboard/')
        with patch('dictionary.views.render') as render:
            with self.assertNumQueries(1):
                leaderboard(request)
        contributors = render.call_args.args[2]['contributors']
        self.assertEqual(len(contributors), 5)
        self.assertTrue(all(row['word_count'] == 1 for row in contributors))


class WordLabLookupTests(TestCase):
    def setUp(self):
        self.url = reverse('dictionary_search_api')
        noun = PartOfSpeech.objects.create(name='Noun')
        verb = PartOfSpeech.objects.create(name='Verb')
        self.word = Words.objects.create(word='Oko')
        Meaning.objects.create(word=self.word, meaning='First recorded meaning', part_of_speech=noun)
        Meaning.objects.create(word=self.word, meaning='Second recorded meaning', part_of_speech=verb)
        Words.objects.create(word='Okoro')

    def test_public_exact_lookup_returns_all_meanings_without_prefix_matches(self):
        with self.assertNumQueries(2):
            response = self.client.get(self.url, {'q': '  OKO  ', 'exact': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['words'], [{
            'word': 'Oko', 'slug': self.word.slug,
            'url': reverse('single-word', kwargs={'slug': self.word.slug}),
            'meanings': [
                {'meaning': 'First recorded meaning', 'part_of_speech': 'Noun'},
                {'meaning': 'Second recorded meaning', 'part_of_speech': 'Verb'},
            ],
        }])

    def test_prefix_search_keeps_its_existing_contract(self):
        response = self.client.get(self.url, {'q': 'Ok'})
        self.assertEqual(response.json()['words'], [
            {'word': 'Oko', 'slug': self.word.slug}, {'word': 'Okoro', 'slug': 'okoro'},
        ])

    def test_unknown_blank_and_oversized_queries_return_empty_results(self):
        for query in ('missing', '', 'x' * 101):
            with self.subTest(query=query):
                self.assertEqual(self.client.get(self.url, {'q': query, 'exact': '1'}).json(), {'words': []})

    def test_word_without_meanings_and_unicode_word(self):
        Words.objects.create(word='ọkọ')
        result = self.client.get(self.url, {'q': 'ọkọ', 'exact': '1'}).json()['words'][0]
        self.assertEqual(result['word'], 'ọkọ')
        self.assertEqual(result['meanings'], [])

    def test_pending_submission_does_not_appear_in_public_lookup(self):
        user = get_user_model().objects.create_user(username='pending-contributor')
        PendingWord.objects.create(word='Privateword', submitted_by=user)
        self.assertEqual(self.client.get(self.url, {'q': 'Privateword', 'exact': '1'}).json(), {'words': []})


class DictionaryBrowseTests(TestCase):
    def setUp(self):
        self.url = reverse('words')
        noun = PartOfSpeech.objects.create(name='Noun')
        for number in range(43):
            word = Words.objects.create(word=f'Aword{number:02d}')
            Meaning.objects.create(word=word, meaning=f'Meaning {number}', part_of_speech=noun)
        Words.objects.create(word='Oko')
        Words.objects.create(word='ọkọ')

    def test_browse_has_meaning_previews_and_bounded_numbered_pages(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['words']), 20)
        self.assertContains(response, 'Meaning 0')
        self.assertContains(response, 'Showing 1–20 of 45')
        self.assertContains(response, 'aria-label="Page 3"')
        self.assertNotContains(response, 'aria-label="Previous page"')

    def test_search_is_preserved_in_pagination_links(self):
        response = self.client.get(self.url, {'word': '  Aword  ', 'letter': 'a', 'page': 2})
        self.assertEqual(response.context['query'], 'Aword')
        self.assertEqual(response.context['current_page_holder'].number, 2)
        self.assertContains(response, 'word=Aword&amp;page=3')
        self.assertNotContains(response, 'letter=')
        self.assertContains(response, 'Showing 21–40 of 43')
        self.assertNotContains(response, '<h3>Oko</h3>')

    def test_unicode_search_without_alphabet_navigation(self):
        response = self.client.get(self.url, {'word': 'ọ'})
        self.assertEqual([word.word for word in response.context['words']], ['ọkọ'])
        self.assertNotContains(response, 'Browse by initial')
        self.assertNotContains(response, 'lexicon-alphabet')
        self.assertNotContains(response, 'aria-label="Dictionary pagination"')

    def test_fragment_renders_results_without_layout_or_scripts(self):
        response = self.client.get(self.url, {'word': 'Oko', 'fragment': '1'})
        self.assertContains(response, 'lexicon-result-content')
        self.assertContains(response, '<h3>Oko</h3>')
        self.assertNotContains(response, '<html')
        self.assertNotContains(response, '<script')

    def test_empty_results_and_unsafe_query_remain_escaped(self):
        response = self.client.get(self.url, {'word': '<script>alert(1)</script>'})
        self.assertContains(response, 'No matching words.')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertNotContains(response, 'aria-label="Dictionary pagination"')

    def test_invalid_page_falls_back_and_old_initial_filter_is_ignored(self):
        response = self.client.get(self.url, {'page': 'invalid', 'letter': 'bad'})
        self.assertEqual(response.context['current_page_holder'].number, 1)
        self.assertEqual(response.context['current_page_holder'].paginator.count, 45)
