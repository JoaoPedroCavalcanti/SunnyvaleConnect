"""Add kind classification and link news posts to their author user.

- ``kind`` (NOTICE/MAINTENANCE/EVENT) classifies the announcement.
- ``created_by`` links the post to the user that created it; SET_NULL
  on user deletion to preserve the audit trail.
- ``author`` (existing CharField) is repurposed as a denormalized
  snapshot of ``user.full_name`` and is widened to 150 chars to fit it.
- ``author_role`` is a new snapshot of ``user.role`` so the listing can
  render "criado por João Pedro · Administrador" even after the user is
  deleted.

No data migration: legacy rows keep their free-text ``author`` and end
up with ``created_by=NULL`` / ``author_role=""``. The front falls back
to showing only the name in that case.
"""

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sunny_vale_news", "0002_sunnyvalenewsmodel_title"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="sunnyvalenewsmodel",
            name="author",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.AddField(
            model_name="sunnyvalenewsmodel",
            name="kind",
            field=models.CharField(
                choices=[
                    ("NOTICE", "Aviso"),
                    ("MAINTENANCE", "Manutenção"),
                    ("EVENT", "Evento"),
                ],
                default="NOTICE",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="sunnyvalenewsmodel",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="news_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="sunnyvalenewsmodel",
            name="author_role",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
    ]
