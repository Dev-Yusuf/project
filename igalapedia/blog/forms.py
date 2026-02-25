from django import forms
from .models import BlogPost, BlogPostComment


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ['title', 'body', 'cover_image', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Post title'}),
            'cover_image': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'title': 'Title',
            'body': 'Content',
            'cover_image': 'Cover image',
            'status': 'Publish as',
        }


class BlogCommentForm(forms.ModelForm):
    class Meta:
        model = BlogPostComment
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Write a comment...',
            }),
        }
        labels = {'body': ''}
