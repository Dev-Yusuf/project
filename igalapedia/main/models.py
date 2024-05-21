from django.db import models

# Create your models here.
class Community(models.Model):
    social_link = models.CharField(max_length=100, null=True, blank=True)
    github_stars = models.IntegerField(null=True, blank=True)
    whatsapp_members = models.IntegerField(null=True, blank=True) 

    def __str__(self):
        return self.social_link
class Pioneer(models.Model):
    pioneer_name = models.CharField(max_length=100, null=True, blank=True)
    profile_image = models.ImageField( null=True, blank=True, upload_to='images/', default='images/user-default.jpg')
    pioneer_social_link = models.CharField(max_length=100, null=True, blank=True) 