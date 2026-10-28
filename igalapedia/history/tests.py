from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from dictionary.models import ContributionStats
from .models import HistoryArticle, PendingHistory


class HistoryApprovalTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='historian')
        self.submission = PendingHistory.objects.create(title='History', content_english='Text', submitted_by=self.user)
        self.stats = ContributionStats.objects.create(user=self.user)

    def test_history_counts_recalculate_and_approval_is_idempotent(self):
        stale = PendingHistory.objects.get(pk=self.submission.pk)
        self.submission.approve(self.user)
        self.assertIsNone(stale.approve(self.user))
        self.stats.approved_histories_count = 99
        self.stats.save()
        self.stats.update_stats()
        self.assertEqual(self.stats.approved_histories_count, 1)
        self.assertEqual(HistoryArticle.objects.count(), 1)

    def test_stats_failure_rolls_back_article_and_review(self):
        with patch('dictionary.models.ContributionStats.update_stats', side_effect=RuntimeError('Failure')):
            with self.assertRaises(RuntimeError):
                self.submission.approve(self.user)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, 'PENDING')
        self.assertIsNone(self.submission.approved_article_id)
        self.assertFalse(HistoryArticle.objects.exists())
