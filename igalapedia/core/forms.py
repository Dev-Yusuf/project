from ckeditor.fields import RichTextField
from django import forms

from .sanitization import sanitize_rich_text


class SanitizedRichTextModelForm(forms.ModelForm):
    """Clean rich text before saving and before opening legacy content in editors."""
    def rich_text_fields(self):
        return [field.name for field in self._meta.model._meta.fields
                if isinstance(field, RichTextField) and field.name in self.fields]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.rich_text_fields():
            if name in self.initial:
                self.initial[name] = sanitize_rich_text(self.initial[name])
            # Bound invalid forms must not feed unsanitized HTML back to editors.
            if self.is_bound and self.add_prefix(name) in self.data:
                self.data = self.data.copy()
                self.data[self.add_prefix(name)] = sanitize_rich_text(self.data[self.add_prefix(name)])

    def clean(self):
        data = super().clean()
        for name in self.rich_text_fields():
            if name in data:
                data[name] = sanitize_rich_text(data[name])
        return data
