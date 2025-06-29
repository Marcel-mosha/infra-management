# Generated by Django 5.1.7 on 2025-06-18 13:38

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("infrastructure", "0015_equipment_block_equipment_floor"),
    ]

    operations = [
        migrations.AlterField(
            model_name="maintenancerequest",
            name="room",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="infrastructure.room",
            ),
        ),
    ]
