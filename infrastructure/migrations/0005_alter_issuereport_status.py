# Generated by Django 5.1.7 on 2025-03-26 19:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0004_rename_user_issuereport_reported_by'),
    ]

    operations = [
        migrations.AlterField(
            model_name='issuereport',
            name='status',
            field=models.CharField(choices=[('Pending', 'Pending'), ('In Progress', 'In Progress'), ('Fixed', 'Fixed')], default='Pending', max_length=20),
        ),
    ]
