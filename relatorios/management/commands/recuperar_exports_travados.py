from django.core.management.base import BaseCommand

from relatorios.services.export.recovery import recuperar_jobs_travados


class Command(BaseCommand):
  help = "Recupera jobs de export travados e re-despacha pendentes antigos."

  def handle(self, *args, **options):
    stats = recuperar_jobs_travados()
    self.stdout.write(self.style.SUCCESS(f"Recuperação concluída: {stats}"))
