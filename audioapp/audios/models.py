from django.contrib.auth.models import User
from django.db import models


class Audio(models.Model):
    name = models.TextField()
    url = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.name)
