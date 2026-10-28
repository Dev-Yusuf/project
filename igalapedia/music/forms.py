from django import forms
from .models import Artist, MusicSubmission, Playlist


class SubmissionForm(forms.ModelForm):
    rights_confirmed = forms.BooleanField(label='I have permission to submit this recording for streaming.')
    class Meta:
        model = MusicSubmission
        fields = ['title', 'artist_name', 'genre', 'audio', 'artwork', 'rights_contact', 'rights_notes', 'rights_confirmed']
        labels = {'audio': 'Audio · MP3, M4A or WAV · up to 25 MB', 'artwork': 'Cover artwork (optional)',
                  'rights_contact': 'Rights-holder contact', 'rights_notes': 'Permission details'}
        widgets = {'rights_notes': forms.Textarea(attrs={'rows': 3}),
                   'audio': forms.ClearableFileInput(attrs={'accept': '.mp3,.m4a,.wav'}),
                   'artwork': forms.ClearableFileInput(attrs={'accept': '.jpg,.jpeg,.png,.webp'})}


class ReviewForm(forms.Form):
    artist = forms.ModelChoiceField(queryset=Artist.objects.filter(is_published=True), required=False)
    review_notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)


class PlaylistForm(forms.ModelForm):
    class Meta:
        model = Playlist
        fields = ['title']
        widgets = {'title': forms.TextInput(attrs={'placeholder': 'Playlist name', 'maxlength': 120})}
