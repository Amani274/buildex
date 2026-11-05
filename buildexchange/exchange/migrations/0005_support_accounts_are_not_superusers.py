from django.db import migrations

def restrict_support(apps,schema_editor):
    Profile=apps.get_model('exchange','Profile')
    User=apps.get_model('auth','User')
    User.objects.filter(id__in=Profile.objects.filter(role='admin').values('user_id')).update(is_staff=False,is_superuser=False)

class Migration(migrations.Migration):
    dependencies=[('exchange','0004_paymentattempt_refunded_ngwee_and_more')]
    operations=[migrations.RunPython(restrict_support,migrations.RunPython.noop)]
