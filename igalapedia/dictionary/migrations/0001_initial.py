# Generated by Django 5.0.3 on 2024-03-28 10:12

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Dialect',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Words',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('word', models.CharField(max_length=100)),
                ('meaning', models.CharField(blank=True, max_length=200, null=True)),
                ('example', models.CharField(default=None, max_length=200, null=True)),
                ('pronunciation', models.FileField(blank=True, null=True, upload_to='word_sounds/')),
                ('slug', models.SlugField(blank=True, max_length=100, unique=True)),
                ('dialects', models.ManyToManyField(default='none', related_name='words', to='dictionary.dialect')),
            ],
            options={
                'verbose_name': 'Word',
            },
        ),
    ]
