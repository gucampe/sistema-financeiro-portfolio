from django.core.management.base import BaseCommand

from relatorios.services.export.cleanup import limpar_exports_expirados


class Command(BaseCommand):
  help = "Remove arquivos de export expirados e jobs antigos."

  def handle(self, *args, **options):
    stats = limpar_exports_expirados()
    self.stdout.write(self.style.SUCCESS(f"Limpeza concluída: {stats}"))
