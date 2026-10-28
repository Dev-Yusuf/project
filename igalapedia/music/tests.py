import io
import wave
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from .forms import SubmissionForm
from .models import Artist, Genre, MusicSubmission, Playlist, PlaylistItem, Release, SavedTrack, Track
from .validators import validate_music_audio


def test_audio(name='test.wav', seconds=2):
    out = io.BytesIO()
    with wave.open(out, 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b'\0\0' * 8000 * seconds)
    return SimpleUploadedFile(name, out.getvalue(), content_type='audio/wav')


class MusicTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='artist', password='test-password')
        self.other = get_user_model().objects.create_user(username='other')
        self.staff = get_user_model().objects.create_superuser(username='editor', password='test-password')
        self.artist = Artist.objects.create(name='Test artist', is_published=True)
        self.genre = Genre.objects.create(name='Folk')
        self.track = Track.objects.create(title='A song', artist=self.artist, audio=test_audio(),
            rights_confirmed=True, rights_contact='Permission reference', is_published=True, genre=self.genre)

    def test_valid_audio_metadata_and_mismatched_audio_rejected(self):
        self.assertEqual(self.track.duration, 2)
        with self.assertRaises(ValidationError):
            validate_music_audio(test_audio('fake.mp3'))
        with self.assertRaises(ValidationError):
            validate_music_audio(SimpleUploadedFile('fake.mp3', b'ID3not-a-real-file'))

    def test_public_discovery_details_and_search_render(self):
        album = Release.objects.create(title='An album', artist=self.artist, is_published=True)
        for route, args in [('home', []), ('search', []), ('artists', []), ('releases', []),
                            ('artist', [self.artist.slug]), ('track', [self.track.slug]), ('release', [album.slug])]:
            with self.subTest(route=route):
                response = self.client.get(reverse('music:' + route, args=args))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'music-audio')
        response = self.client.get(reverse('music:search'), {'q': 'Test artist', 'genre': self.genre.pk})
        self.assertContains(response, 'A song')
        self.assertEqual(self.client.get(reverse('music:search'), {'q': 'missing'}).context['tracks'], [])

    def test_fragment_does_not_replace_persistent_player(self):
        response = self.client.get(reverse('music:search'), {'fragment': '1'})
        self.assertContains(response, 'music-view')
        self.assertNotContains(response, 'id="music-audio"')
        self.assertContains(response, 'music-page-tracks')

    def test_guest_playback_returns_temporary_url_without_private_metadata(self):
        response = self.client.get(reverse('music:playback', args=[self.track.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('stream', response.json())
        self.assertNotIn('rights_contact', response.json())
        self.assertNotIn('audio', response.json())
        self.assertIn('no-store', response['Cache-Control'])

    def test_unpublished_or_unapproved_content_never_streams(self):
        url = reverse('music:playback', args=[self.track.pk])
        for field in ['is_published', 'rights_confirmed']:
            Track.objects.filter(pk=self.track.pk).update(**{field: False})
            self.assertEqual(self.client.get(url).status_code, 404)
            Track.objects.filter(pk=self.track.pk).update(**{field: True})
        self.artist.is_published = False
        self.artist.save()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_hidden_release_blocks_track_in_every_public_path(self):
        album = Release.objects.create(title='Hidden album', artist=self.artist)
        Track.objects.filter(pk=self.track.pk).update(release=album)
        self.assertEqual(self.client.get(reverse('music:playback', args=[self.track.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse('music:home')), 'A song')

    def test_publishing_requires_rights_and_a_published_artist(self):
        self.track.rights_confirmed = False
        with self.assertRaises(ValidationError):
            self.track.save()
        self.track.rights_confirmed = True
        self.artist.is_published = False
        self.artist.save()
        with self.assertRaises(ValidationError):
            self.track.save()

    def test_guest_cannot_submit_or_access_private_library(self):
        for route in ['submit', 'submissions', 'library']:
            self.assertEqual(self.client.get(reverse('music:' + route)).status_code, 302)

    def test_submission_is_private_and_ignores_forged_publication_fields(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('music:submit'), {'artist_name': 'New artist', 'title': 'Unreviewed',
            'audio': test_audio(), 'rights_confirmed': 'on', 'rights_contact': 'Owner contact',
            'status': 'approved', 'user': self.other.pk})
        self.assertEqual(response.status_code, 302)
        submission = MusicSubmission.objects.get()
        self.assertEqual(submission.status, 'pending')
        self.assertEqual(submission.user, self.user)
        self.assertEqual(submission.duration, 2)
        self.assertNotContains(self.client.get(reverse('music:home')), 'Unreviewed')
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse('music:submissions')), 'Unreviewed')
        self.assertEqual(self.client.get(reverse('music:submission_preview', args=[submission.pk])).status_code, 404)

    def test_rights_confirmation_is_required_on_submission(self):
        form = SubmissionForm({'artist_name':'New artist','title':'A title','rights_contact':'Owner'}, {'audio':test_audio()})
        self.assertFalse(form.is_valid())
        self.assertIn('rights_confirmed', form.errors)

    def test_staff_approval_is_idempotent_and_preserves_audio(self):
        submission = MusicSubmission.objects.create(user=self.user, artist_name='Test artist', title='Reviewed',
            audio=test_audio(), rights_confirmed=True, rights_contact='Owner')
        song = submission.approve(self.staff, self.artist)
        self.assertTrue(song.is_published)
        self.assertEqual(song.audio.name, submission.audio.name)
        self.assertEqual(song.duration, 2)
        with self.assertRaises(ValidationError):
            submission.approve(self.staff, self.artist)
        self.assertEqual(Track.objects.filter(title='Reviewed').count(), 1)

    def test_artist_cannot_approve_own_submission(self):
        submission = MusicSubmission.objects.create(user=self.user, title='Pending', artist_name='Artist',
            audio=test_audio(), rights_confirmed=True, rights_contact='Owner')
        with self.assertRaises(ValidationError):
            submission.approve(self.user, self.artist)

    def test_like_is_authenticated_post_only_and_idempotent(self):
        url = reverse('music:save_track', args=[self.track.pk])
        self.assertEqual(self.client.post(url, {'saved':'1'}).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 405)
        for _ in range(2):
            self.assertEqual(self.client.post(url, {'saved':'1'}).status_code, 200)
        self.assertEqual(SavedTrack.objects.count(), 1)
        self.client.post(url, {'saved':'0'})
        self.assertEqual(SavedTrack.objects.count(), 0)

    def test_playlist_owner_access_ordering_and_duplicate_add(self):
        item = Playlist.objects.create(user=self.user, title='My playlist')
        url = reverse('music:playlist_action', args=[item.pk])
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse('music:playlist', args=[item.pk])).status_code, 404)
        self.assertEqual(self.client.post(url, {'action':'add','track':self.track.pk}).status_code, 404)
        self.client.force_login(self.user)
        for _ in range(2): self.client.post(url, {'action':'add','track':self.track.pk})
        second = Track.objects.create(title='Second', artist=self.artist, audio=test_audio(),
            rights_confirmed=True, rights_contact='Owner', is_published=True)
        self.client.post(url, {'action':'add','track':second.pk})
        self.client.post(url, {'action':'up','track':second.pk})
        self.assertEqual(list(item.items.values_list('track_id', flat=True)), [second.pk, self.track.pk])
        self.assertEqual(item.items.count(), 2)
        self.assertEqual(self.client.get(reverse('music:playlist', args=[item.pk])).status_code, 200)
        self.client.post(url, {'action':'remove','track':self.track.pk})
        self.assertEqual(item.items.count(), 1)

    def test_unpublished_tracks_are_removed_from_library_and_playlists(self):
        SavedTrack.objects.create(user=self.user, track=self.track)
        item = Playlist.objects.create(user=self.user, title='Mine')
        PlaylistItem.objects.create(playlist=item, track=self.track)
        Track.objects.filter(pk=self.track.pk).update(is_published=False)
        self.client.force_login(self.user)
        for url in [reverse('music:library'), reverse('music:playlist', args=[item.pk])]:
            self.assertNotContains(self.client.get(url), 'A song')

    def test_upload_limit_blocks_more_pending_submissions(self):
        for number in range(10):
            MusicSubmission.objects.create(user=self.user, title=str(number), artist_name='Artist',
                audio='not-public.wav', duration=1, rights_contact='Owner', rights_confirmed=True)
        self.client.force_login(self.user)
        response = self.client.post(reverse('music:submit'), {'title':'Over limit','artist_name':'Artist',
            'audio':test_audio(), 'rights_contact':'Owner', 'rights_confirmed':'on'})
        self.assertContains(response, 'submission limit')
        self.assertEqual(MusicSubmission.objects.count(), 10)

    def test_csrf_is_enforced_on_state_changes(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse('music:save_track', args=[self.track.pk]), {'saved':'1'}).status_code, 403)

    def test_private_storage_does_not_fall_back_to_public_bucket(self):
        from .storage import PrivateMusicStorage
        with self.settings(MUSIC_STORAGE_BUCKET=''):
            with self.assertRaises(Exception):
                PrivateMusicStorage().configured()
        with self.settings(MUSIC_STORAGE_BUCKET='music-private'):
            storage = PrivateMusicStorage()
            self.assertTrue(storage.querystring_auth)
            self.assertIsNone(storage.default_acl)

    def test_empty_catalogue_uses_real_empty_states(self):
        Track.objects.all().delete()
        Artist.objects.all().delete()
        response = self.client.get(reverse('music:home'))
        self.assertContains(response, 'No tracks yet.')
        self.assertContains(response, 'No artists published yet.')

    def test_admin_can_review_approve_and_reject(self):
        self.client.force_login(self.staff)
        item = MusicSubmission.objects.create(user=self.user, title='Staff reviewed', artist_name='Artist',
            audio=test_audio(), rights_confirmed=True, rights_contact='Permission reference')
        url = reverse('admin:music_review', args=[item.pk])
        self.assertContains(self.client.get(url), 'Review music submission')
        self.assertEqual(self.client.post(url, {'decision':'approve','artist':self.artist.pk,'review_notes':'Verified'}).status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.status, 'approved')
        self.assertEqual(item.review_notes, 'Verified')
        another = MusicSubmission.objects.create(user=self.user, title='Rejected', artist_name='Artist',
            audio=test_audio(), rights_confirmed=True, rights_contact='Owner')
        url = reverse('admin:music_review', args=[another.pk])
        self.assertContains(self.client.post(url, {'decision':'reject'}), 'Give the artist a reason')
        self.assertEqual(self.client.post(url, {'decision':'reject','review_notes':'Please correct the artist credit.'}).status_code, 302)
        another.refresh_from_db()
        self.assertEqual(another.status, 'rejected')

    def test_owner_and_staff_can_preview_but_guests_cannot(self):
        item = MusicSubmission.objects.create(user=self.user, title='Preview', artist_name='Artist',
            audio=test_audio(), rights_confirmed=True, rights_contact='Owner')
        url = reverse('music:submission_preview', args=[item.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        for user in [self.user, self.staff]:
            self.client.force_login(user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/media/', response['Location'])

    def test_audio_size_and_duration_limits(self):
        from .validators import audio_metadata
        upload = test_audio()
        with self.settings(MUSIC_MAX_UPLOAD_BYTES=16):
            with self.assertRaises(ValidationError):
                audio_metadata(upload)
        with self.assertRaises(ValidationError):
            audio_metadata(test_audio(seconds=0))

    def test_missing_music_storage_is_a_form_error(self):
        from .storage import PrivateMusicStorage
        with self.settings(MUSIC_STORAGE_BUCKET=''):
            with patch.object(Track._meta.get_field('audio'), 'storage', PrivateMusicStorage()):
                song = Track(title='Not configured', artist=self.artist, audio=test_audio(), rights_contact='Owner')
                with self.assertRaisesMessage(ValidationError, 'uploads are not available'):
                    song.clean()

    def test_huge_genre_filter_does_not_crash(self):
        self.assertEqual(self.client.get(reverse('music:search'), {'genre':'9' * 5000}).status_code, 200)

    def test_search_includes_matching_artist_and_release_cards(self):
        album = Release.objects.create(title='Test release', artist=self.artist, is_published=True)
        response = self.client.get(reverse('music:search'), {'q':'Test'})
        self.assertEqual(list(response.context['artists']), [self.artist])
        self.assertEqual(list(response.context['releases']), [album])

    def test_submission_artwork_uses_private_storage_and_survives_approval(self):
        from PIL import Image
        out = io.BytesIO()
        Image.new('RGB', (2,2), color='green').save(out, format='PNG')
        item = MusicSubmission.objects.create(user=self.user, title='Private cover', artist_name='Artist',
            audio=test_audio(), artwork=SimpleUploadedFile('cover.png',out.getvalue(),content_type='image/png'),
            rights_confirmed=True, rights_contact='Owner')
        approved = item.approve(self.staff,self.artist)
        self.assertTrue(approved.audio.storage.exists(approved.audio.name))
        self.assertTrue(approved.artwork.storage.exists(approved.artwork.name))
        self.assertTrue(item.artwork.name.startswith('artwork/'))
