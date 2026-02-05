"""
Email sending utilities for contribution status (approved/rejected).
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse


def send_word_approved_email(user, word, pending_word, request=None):
    """
    Send a congratulatory email when a user's word submission is approved.

    Args:
        user: The User who submitted the word.
        word: The approved Words instance.
        pending_word: The PendingWord submission that was approved.
        request: Optional HttpRequest for building absolute URLs.
    """
    if not user.email:
        return

    if request:
        word_url = request.build_absolute_uri(
            reverse('single-word', kwargs={'slug': word.slug})
        )
    else:
        base = getattr(settings, 'SITE_URL', 'https://igalapedia.org').rstrip('/')
        word_url = f"{base}/dictionary/single-word/{word.slug}/"

    context = {
        'username': user.get_full_name() or user.username,
        'word': word.word,
        'word_url': word_url,
    }

    subject = f'Your word "{word.word}" has been approved — Igalapedia'
    html_content = render_to_string('email/word_approved.html', context)
    text_content = (
        f"Hello {context['username']},\n\n"
        f"Great news! Your contribution has been approved and published to the Igalapedia dictionary.\n\n"
        f'Word: "{word.word}"\n\n'
        f"Thank you for helping preserve the Igala language. View it here: {word_url}\n\n"
        f"Keep contributing!\n\n"
        f"© Igalapedia."
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_content, 'text/html')
    msg.send(fail_silently=True)


def send_word_rejected_email(user, pending_word, request=None):
    """
    Send an email when a user's word submission is rejected.

    Args:
        user: The User who submitted the word.
        pending_word: The PendingWord submission that was rejected (with review_notes if any).
        request: Optional HttpRequest for building absolute URLs.
    """
    if not user.email:
        return

    if request:
        submit_url = request.build_absolute_uri(reverse('submit_word'))
    else:
        base = getattr(settings, 'SITE_URL', 'https://igalapedia.org').rstrip('/')
        submit_url = f"{base}/dictionary/submit/"

    context = {
        'username': user.get_full_name() or user.username,
        'word': pending_word.word,
        'review_notes': pending_word.review_notes or '',
        'submit_url': submit_url,
    }

    subject = f'Update on your submission "{pending_word.word}" — Igalapedia'
    html_content = render_to_string('email/word_rejected.html', context)
    text_content = (
        f"Hello {context['username']},\n\n"
        f"We've reviewed your submission and unfortunately it could not be approved at this time.\n\n"
        f'Word submitted: "{pending_word.word}"\n\n'
    )
    if pending_word.review_notes:
        text_content += f"Feedback from our team:\n{pending_word.review_notes}\n\n"
    text_content += f"You can submit a new or revised entry: {submit_url}\n\n© Igalapedia."

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_content, 'text/html')
    msg.send(fail_silently=True)


def send_example_approved_email(user, meaning, word, request=None):
    """
    Send a congratulatory email when a user's example contribution is approved.

    Args:
        user: The User who submitted the example.
        meaning: The Meaning the example was added to.
        word: The Words instance.
        request: Optional HttpRequest for building absolute URLs.
    """
    if not user.email:
        return

    if request:
        word_url = request.build_absolute_uri(
            reverse('single-word', kwargs={'slug': word.slug})
        )
    else:
        base = getattr(settings, 'SITE_URL', 'https://igalapedia.org').rstrip('/')
        word_url = f"{base}/dictionary/single-word/{word.slug}/"

    context = {
        'username': user.get_full_name() or user.username,
        'word': word.word,
        'meaning': meaning.meaning,
        'word_url': word_url,
    }

    subject = f'Your usage example for "{word.word}" has been approved — Igalapedia'
    html_content = render_to_string('email/example_approved.html', context)
    text_content = (
        f"Hello {context['username']},\n\n"
        f"Great news! Your usage example contribution has been approved and added to the Igalapedia dictionary.\n\n"
        f'Word: "{word.word}"\n'
        f'Meaning: {meaning.meaning}\n\n'
        f"Thank you for helping improve the dictionary. View it here: {word_url}\n\n"
        f"Keep contributing!\n\n"
        f"© Igalapedia."
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_content, 'text/html')
    msg.send(fail_silently=True)


def send_example_rejected_email(user, pending_example, request=None):
    """
    Send an email when a user's example contribution is rejected.

    Args:
        user: The User who submitted the example.
        pending_example: The PendingExampleContribution that was rejected.
        request: Optional HttpRequest for building absolute URLs.
    """
    if not user.email:
        return

    word = pending_example.meaning.word
    if request:
        word_url = request.build_absolute_uri(
            reverse('single-word', kwargs={'slug': word.slug})
        )
    else:
        base = getattr(settings, 'SITE_URL', 'https://igalapedia.org').rstrip('/')
        word_url = f"{base}/dictionary/single-word/{word.slug}/"

    context = {
        'username': user.get_full_name() or user.username,
        'word': word.word,
        'igala_example': pending_example.igala_example,
        'review_notes': pending_example.review_notes or '',
        'word_url': word_url,
    }

    subject = f'Update on your example submission for "{word.word}" — Igalapedia'
    html_content = render_to_string('email/example_rejected.html', context)
    text_content = (
        f"Hello {context['username']},\n\n"
        f"We've reviewed your usage example submission and unfortunately it could not be approved at this time.\n\n"
        f'Word: "{word.word}"\n'
        f'Example submitted: "{pending_example.igala_example}"\n\n'
    )
    if pending_example.review_notes:
        text_content += f"Feedback from our team:\n{pending_example.review_notes}\n\n"
    text_content += f"You can try submitting a revised example: {word_url}\n\n© Igalapedia."

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_content, 'text/html')
    msg.send(fail_silently=True)
