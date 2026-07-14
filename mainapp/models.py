from django.db import models

# Create your models here.
class Request(models.Model):
    SNo = models.AutoField(primary_key=True)
    Name = models.CharField(max_length=100)
    Email = models.EmailField()
    Subject = models.TextField()
    Message = models.TextField()
    def __str__(self):
        return self.Name