"""
Email sending utilities for the main app.
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_welcome_email(user, request=None):
    """
    Send a welcome email to a newly registered user.

    Args:
        user: The User instance (must have email and username).
        request: Optional HttpRequest for building absolute URLs.
    """
    if not user.email:
        return

    # Build site URL for the "Visit Igalapedia" link
    if request:
        from django.urls import reverse
        site_url = request.build_absolute_uri(reverse('index'))
    else:
        site_url = getattr(settings, 'SITE_URL', 'https://igalapedia.org')

    context = {
        'username': user.get_full_name() or user.username,
        'site_url': site_url,
    }

    subject = 'Welcome to Igalapedia!'
    html_content = render_to_string('email/welcome.html', context)
    text_content = (
        f"Hello {context['username']},\n\n"
        f"Welcome to Igalapedia — the community-driven platform for preserving and sharing "
        f"the Igala language and culture.\n\n"
        f"Your account has been created successfully. You can now explore the dictionary, "
        f"submit new words, and track your contributions.\n\n"
        f"Visit Igalapedia: {site_url}\n\n"
        f"© Igalapedia. Preserving Igala heritage through technology."
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_content, 'text/html')
    msg.send(fail_silently=True)
