# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2018-02-13 07:46
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('VEDA_OS01', '0006_auto_20180116_0939'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='institution',
            field=models.CharField(help_text=b'Organization of the course.', max_length=255, verbose_name=b'Inst. Code'),
        ),
    ]
