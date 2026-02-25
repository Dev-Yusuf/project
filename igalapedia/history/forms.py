from django import forms
from .models import PendingHistory


class HistorySubmissionForm(forms.ModelForm):
    class Meta:
        model = PendingHistory
        fields = [
            'title',
            'excerpt',
            'thumbnail',
            'content_english',
            'content_igala',
            'audio_english',
            'audio_igala',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter the title of the history',
            }),
            'excerpt': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Short summary for article cards (up to 300 characters)',
                'rows': 2,
                'maxlength': '300',
            }),
            'thumbnail': forms.FileInput(attrs={'class': 'form-control'}),
            'audio_english': forms.FileInput(attrs={'class': 'form-control', 'accept': 'audio/*'}),
            'audio_igala': forms.FileInput(attrs={'class': 'form-control', 'accept': 'audio/*'}),
        }
        labels = {
            'title': 'Title *',
            'excerpt': 'Short Excerpt',
            'thumbnail': 'Thumbnail Image',
            'content_english': 'Content (English) *',
            'content_igala': 'Content (Igala)',
            'audio_english': 'Audio (English)',
            'audio_igala': 'Audio (Igala)',
        }

    def clean(self):
        data = super().clean()
        if not data.get('content_english') and not data.get('content_igala'):
            raise forms.ValidationError('Please provide at least content in English or Igala.')
        return data
