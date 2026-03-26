from django.contrib import admin

from candidates.models import Application, ApplicationStageLog, Candidate, Document

# Register your models here.
admin.site.register(Application)
admin.site.register(ApplicationStageLog)
admin.site.register(Candidate)
admin.site.register(Document)