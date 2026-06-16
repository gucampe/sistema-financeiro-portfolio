from relatorios.services.export.jobs import executar_job


def dispatch(job_id: int) -> None:
  executar_job(job_id)
