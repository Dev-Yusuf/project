from django import forms
from .models import PendingBook, PendingHallOfFameProfile


class BookSubmissionForm(forms.ModelForm):
    class Meta:
        model = PendingBook
        fields = [
            "title",
            "author",
            "description",
            "cover_image",
            "file",
            "external_url",
            "language",
            "publication_year",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }


class HallOfFameSubmissionForm(forms.ModelForm):
    class Meta:
        model = PendingHallOfFameProfile
        fields = [
            "name",
            "title_role",
            "era",
            "bio",
            "achievements",
            "profile_image",
            "external_links",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 6}),
            "achievements": forms.Textarea(attrs={"rows": 5}),
            "external_links": forms.Textarea(attrs={"rows": 3, "placeholder": "Add links separated by commas"}),
        }
