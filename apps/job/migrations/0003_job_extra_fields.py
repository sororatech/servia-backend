from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('job', '0002_alter_job_unique_together'),
    ]

    operations = [
        # Columns already exist in the DB; only update Django's internal state.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='job',
                    name='openings_count',
                    field=models.PositiveIntegerField(default=1),
                ),
                migrations.AddField(
                    model_name='job',
                    name='salary_min',
                    field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
                ),
                migrations.AddField(
                    model_name='job',
                    name='salary_max',
                    field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
                ),
                migrations.AddField(
                    model_name='job',
                    name='salary_currency',
                    field=models.CharField(default='ETB', max_length=10),
                ),
                migrations.AddField(
                    model_name='job',
                    name='salary_period',
                    field=models.CharField(
                        choices=[
                            ('hourly', 'Hourly'),
                            ('daily', 'Daily'),
                            ('weekly', 'Weekly'),
                            ('monthly', 'Monthly'),
                            ('yearly', 'Yearly'),
                        ],
                        default='monthly',
                        max_length=20,
                    ),
                ),
                migrations.AddField(
                    model_name='job',
                    name='core_skills',
                    field=models.JSONField(default=list),
                ),
            ],
            database_operations=[],
        ),
    ]
