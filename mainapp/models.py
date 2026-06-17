from django.db import models

# Create your models here.
class Projects(models.Model):
    SNo = models.AutoField(primary_key=True)
    Name = models.CharField(max_length=100)
    Category = models.CharField(max_length=100)
    Description = models.TextField()
    Detail = models.TextField()
    Github = models.URLField(max_length=300)
    Project = models.URLField(max_length=300, blank=True, null=True)
    def __str__(self):
        return self.Name