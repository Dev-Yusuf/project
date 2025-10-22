from django.db import models

# Create your models here.
class Community(models.Model):
    social_link = models.CharField(max_length=100, null=True, blank=True)
    github_stars = models.IntegerField(null=True, blank=True)
    whatsapp_members = models.IntegerField(null=True, blank=True) 

    def __str__(self):
        return self.social_link
class Pioneer(models.Model):
    pioneer_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Name")
    position = models.CharField(max_length=200, null=True, blank=True, verbose_name="Position/Title")
    bio = models.TextField(null=True, blank=True, verbose_name="Biography")
    profile_image = models.ImageField(null=True, blank=True, upload_to='pioneers/')
    pioneer_social_link = models.CharField(max_length=200, null=True, blank=True, verbose_name="Social Link")
    
    class Meta:
        verbose_name = "Pioneer"
        verbose_name_plural = "Pioneers"
        ordering = ['-id']
    
    def __str__(self):
        return self.pioneer_name if self.pioneer_name else "Unnamed Pioneer" 