document.addEventListener("click", function(e){
    const editar = e.target.closest(".editar-transacao");
  
    if (editar){
        const id = editar.dataset.id;
  
        // Buscar dados da transação via AJAX
        fetch(`/transacoes/${id}/editar/?ajax=1`)
          .then(response => response.json())
          .then(data => {
              // Preencher o modal existente
              const modal = document.getElementById("overlay-adicionar");
              
              document.getElementById("tipo").value = data.tipo;
              document.getElementById("valor").value = data.valor;
              document.getElementById("descricao").value = data.descricao;
              document.getElementById("data").value = data.data;
  
              // Preencher conta
              const selectConta = document.getElementById("id_conta");
              if (selectConta) {
                  selectConta.value = data.conta ? data.conta.id : "";
              }
              const selectCartao = document.getElementById("id_cartao");
              if (selectCartao) {
                  selectCartao.value = data.cartao ? data.cartao.id : "";
              }
  
              // Preencher categoria
              const selectCategoria = document.getElementById("categoria");
              if (selectCategoria) {
                  selectCategoria.value = data.categoria.id;
              }
  
              // Marcar que é edição
              modal.dataset.editando = id;
  
              // Abrir modal
              modal.classList.remove("hidden", "opacity-0");
              modal.classList.add("flex", "opacity-100");
          })
          .catch(err => console.error("Erro ao carregar transação:", err));
    }
  });