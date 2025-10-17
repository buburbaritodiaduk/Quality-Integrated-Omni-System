from django.db import models

class DailyRecord(models.Model):
    date = models.DateField()
    income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expense = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    orders_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-date'] # Urutkan dari yang terbaru

    def __str__(self):
        return f"Record for {self.date}"