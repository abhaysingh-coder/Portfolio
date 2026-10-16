from django.db import models

# Create your models here.
class Projects(models.Model):
    SNo = models.AutoField(primary_key=True)
    Name = models.CharField(max_length=100)
    Category = models.CharField(max_length=100)
    Description = models.TextField()
    Detail = models.TextField()
    Github = models.CharField(max_length=200)
    Project = models.CharField(max_length=200)

    def __str__(self):
        return self.Name


class Request(models.Model):
    SNo = models.AutoField(primary_key=True)
    Name = models.CharField(max_length=100)
    Email = models.EmailField()
    Subject = models.TextField()
    Message = models.TextField()
    def __str__(self):
        return self.Name