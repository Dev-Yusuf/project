# Generated by Django 5.0.3 on 2024-04-25 11:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0006_remove_words_example_remove_words_example_meaning_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='words',
            name='dialects',
        ),
        migrations.RemoveField(
            model_name='words',
            name='part_of_speech',
        ),
        migrations.DeleteModel(
            name='Dialect',
        ),
        migrations.AddField(
            model_name='words',
            name='dialects',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.DeleteModel(
            name='PartOfSpeech',
        ),
        migrations.AddField(
            model_name='words',
            name='part_of_speech',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
