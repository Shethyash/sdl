from datetime import datetime

from PIL import Image
from django.db import models


# Create your models here.


class Nodes(models.Model):
    name = models.CharField(max_length=100)
    user_id = models.IntegerField(default=0)
    status = models.BooleanField(default=False)
    description = models.TextField(default='')
    latitude = models.FloatField()
    longitude = models.FloatField()
    last_feed_time = models.DateTimeField(null=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return self.name


class Feeds(models.Model):
    node_id = models.IntegerField()
    temperature = models.FloatField(null=True)
    humidity = models.FloatField(null=True)
    LWS = models.FloatField(null=True)
    soil_temperature = models.FloatField(null=True)
    soil_moisture = models.FloatField(null=True)
    battery_status = models.FloatField(null=True)
    created_at = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return str(self.node_id)


class CropImage(models.Model):
    node_id = models.IntegerField()
    image = models.ImageField(upload_to='crop_images')
    description = models.TextField(default='')
    created_at = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return str(self.node_id)

    # resizing images
    def save(self, *args, **kwargs):
        super().save()

        img = Image.open(self.image.path)

        if img.height > 100 or img.width > 100:
            new_img = (100, 100)
            img.thumbnail(new_img)
            img.save(self.image.path)
