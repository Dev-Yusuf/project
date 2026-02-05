from django import forms
from .models import PendingWord, PendingMeaning, PendingExample, PendingExampleContribution, PartOfSpeech, Meaning, Words


class WordSubmissionForm(forms.ModelForm):
    """
    Form for submitting a new word to the dictionary
    """
    class Meta:
        model = PendingWord
        fields = ['word', 'dialects', 'related_terms']
        widgets = {
            'word': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter the Igala word',
                'required': True,
                'id': 'id_word',
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
            'dialects': 'Dialects',
            'related_terms': 'Related Terms',
        }
        help_texts = {
            'word': 'Enter the word in Igala language',
            'dialects': 'Specify which Igala dialects use this word',
            'related_terms': 'List related words separated by commas',
        }
    
    def clean_word(self):
        """
        Validate that the word doesn't already exist in the approved dictionary.
        """
        word = self.cleaned_data.get('word', '').strip()
        if not word:
            raise forms.ValidationError('This field is required.')
        
        # Check if word already exists in approved dictionary (case-insensitive)
        existing = Words.objects.filter(word__iexact=word).first()
        if existing:
            raise forms.ValidationError(
                f'The word "{word}" already exists in the dictionary. '
                f'View it at: /dictionary/single-word/{existing.slug}/'
            )
        
        return word


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

# Formset for multiple examples (used in admin / other contexts)
ExampleFormSet = formset_factory(
    ExampleSubmissionForm,
    extra=1,
    max_num=3,
    can_delete=True
)


class ExampleInlineForm(forms.Form):
    """
    Inline form for usage examples when submitting a word.
    meaning_index links the example to the Nth meaning in the formset.
    """
    meaning_index = forms.IntegerField(min_value=0, widget=forms.HiddenInput())
    igala_example = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Example sentence in Igala',
        })
    )
    english_meaning = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'English translation',
        })
    )


# Formset for examples per meaning on submit word page (extra=0, add via JS)
ExampleInlineFormSet = formset_factory(
    ExampleInlineForm,
    extra=0,
    max_num=30,
    can_delete=True
)


class ExampleContributionForm(forms.ModelForm):
    """
    Form for submitting a usage example for an existing approved word/meaning.
    """
    meaning = forms.ModelChoiceField(
        queryset=Meaning.objects.none(),  # Will be set dynamically in the view
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label='Select Meaning *',
        help_text='Choose the meaning this example illustrates'
    )
    
    class Meta:
        model = PendingExampleContribution
        fields = ['meaning', 'igala_example', 'english_meaning']
        widgets = {
            'igala_example': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example sentence in Igala',
                'required': True
            }),
            'english_meaning': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'English translation of the example',
                'required': True
            }),
        }
        labels = {
            'igala_example': 'Igala Example Sentence *',
            'english_meaning': 'English Translation *',
        }
        help_texts = {
            'igala_example': 'Write a sentence in Igala that uses this word',
            'english_meaning': 'Translate the example sentence to English',
        }
    
    def __init__(self, *args, word=None, **kwargs):
        super().__init__(*args, **kwargs)
        if word:
            # Filter meanings to those belonging to this word
            self.fields['meaning'].queryset = word.meanings.all()
            # Custom label_from_instance to show PoS + meaning
            self.fields['meaning'].label_from_instance = lambda m: f"({m.part_of_speech.name}) {m.meaning}"

