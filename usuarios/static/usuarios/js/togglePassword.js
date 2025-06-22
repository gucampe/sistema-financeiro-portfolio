document.addEventListener('DOMContentLoaded', function () {
  const toggleSenhaBtn = document.getElementById('toggleSenha');
  const senhaInput = document.getElementById('senha');
  const iconOlho = document.getElementById('iconOlho');

  if (toggleSenhaBtn && senhaInput) {
    toggleSenhaBtn.addEventListener('click', () => {
      const tipoAtual = senhaInput.getAttribute('type');
      const novoTipo = tipoAtual === 'password' ? 'text' : 'password';
      senhaInput.setAttribute('type', novoTipo);

      // Alterar ícone se quiser (opcional)
      if (iconOlho) {
        iconOlho.setAttribute(
          'd',
          novoTipo === 'text'
            ? 'M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.542-7a10.043 10.043 0 013.68-5.106'
            : 'M2.458 12C3.732 7.943 7.523 5 12 5c4.477 0 8.268 2.943 9.542 7-1.274 4.057-5.065 7-9.542 7-4.477 0-8.268-2.943-9.542-7z'
        );
      }
    });
  }
});
