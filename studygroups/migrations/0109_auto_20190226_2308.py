# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2019-02-26 23:08
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('studygroups', '0108_auto_20181204_0729'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='discourse_topic_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='overall_rating',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='platform',
            field=models.CharField(blank=True, max_length=256),
        ),
        migrations.AddField(
            model_name='course',
            name='rating_step_counts',
            field=models.TextField(default='{}'),
        ),
        migrations.AddField(
            model_name='course',
            name='tagdorsement_counts',
            field=models.TextField(default='{}'),
        ),
        migrations.AddField(
            model_name='course',
            name='tagdorsements',
            field=models.CharField(blank=True, max_length=256),
        ),
        migrations.AddField(
            model_name='course',
            name='total_ratings',
            field=models.SmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='total_reviewers',
            field=models.SmallIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='application',
            name='goal_met',
            field=models.SmallIntegerField(blank=True, null=True),
        ),
    ]
