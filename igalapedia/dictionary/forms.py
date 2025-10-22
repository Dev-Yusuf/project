from django import forms
from .models import PendingWord, PendingMeaning, PendingExample, PartOfSpeech


class WordSubmissionForm(forms.ModelForm):
    """
    Form for submitting a new word to the dictionary
    """
    class Meta:
        model = PendingWord
        fields = ['word', 'pronunciation_file', 'dialects', 'related_terms']
        widgets = {
            'word': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter the Igala word',
                'required': True
            }),
            'pronunciation_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'audio/*'
            }),
            'dialects': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Ankpa, Idah, Ajaka (optional)'
            }),
            'related_terms': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Related words separated by commas (optional)'
            }),
        }
        labels = {
            'word': 'Igala Word *',
            'pronunciation_file': 'Audio Pronunciation (optional)',
            'dialects': 'Dialects',
            'related_terms': 'Related Terms',
        }
        help_texts = {
            'word': 'Enter the word in Igala language',
            'pronunciation_file': 'Upload an audio file of the pronunciation (MP3, WAV)',
            'dialects': 'Specify which Igala dialects use this word',
            'related_terms': 'List related words separated by commas',
        }


class MeaningSubmissionForm(forms.ModelForm):
    """
    Form for submitting a meaning for a word
    """
    class Meta:
        model = PendingMeaning
        fields = ['meaning', 'part_of_speech']
        widgets = {
            'meaning': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter the English meaning',
                'required': True
            }),
            'part_of_speech': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
        }
        labels = {
            'meaning': 'English Meaning *',
            'part_of_speech': 'Part of Speech *',
        }


class ExampleSubmissionForm(forms.ModelForm):
    """
    Form for submitting usage examples
    """
    class Meta:
        model = PendingExample
        fields = ['igala_example', 'english_meaning']
        widgets = {
            'igala_example': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example sentence in Igala',
                'required': True
            }),
            'english_meaning': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'English translation',
                'required': True
            }),
        }
        labels = {
            'igala_example': 'Igala Example *',
            'english_meaning': 'English Translation *',
        }


# Formsets for multiple meanings and examples
from django.forms import formset_factory, inlineformset_factory

# Formset for multiple meanings
MeaningFormSet = formset_factory(
    MeaningSubmissionForm,
    extra=1,
    max_num=5,
    can_delete=True
)

# Formset for multiple examples  
ExampleFormSet = formset_factory(
    ExampleSubmissionForm,
    extra=1,
    max_num=3,
    can_delete=True
)

