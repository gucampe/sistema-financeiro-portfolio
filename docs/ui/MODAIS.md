# Modais (GranaGo)

Padrão único para overlays, acessibilidade e fechamento.

## Markup

```html
<div id="overlay-exemplo" data-modal class="modal-overlay hidden"
     data-modal-labelledby="titulo-exemplo"
     data-modal-fade="300">
  <div data-modal-panel class="modal-panel mx-auto w-full max-w-lg">
    <h2 id="titulo-exemplo">Título</h2>
    <button type="button" data-modal-close aria-label="Fechar">✕</button>
    <!-- conteúdo -->
  </div>
</div>
```

- `data-modal` — raiz do overlay (obrigatório).
- `data-modal-panel` — painel que **não** fecha ao clicar dentro.
- `data-modal-close` — botões Cancelar / ✕ (delegação global).
- `data-modal-labelledby` — id do título para `aria-labelledby`.
- `data-modal-fade` — ms do fade do backdrop ao fechar/abrir (padrão **300**, igual ao modal de transação). Use `data-modal-fade="0"` para desativar.
- `data-modal-panel-scale="0"` — desativa a animação de escala do painel (`scale-95` → `scale-100`); o fade do overlay continua.

Ao abrir, `GranaGoModal` aplica automaticamente fade do overlay e zoom suave do `[data-modal-panel]` (não é necessário `scale-95` no HTML).

Modais empilhados: use `z-[60]` no overlay secundário (ex.: ícone da conta).

## JavaScript

Carregue `static/js/modal.js` (já incluído em `base.html`).

```javascript
const overlay = document.getElementById("overlay-exemplo");

GranaGoModal.bind(overlay, {
  onOpen() {
    // preparar formulário (opcional; `open` já aplica fade + escala do painel antes)
  },
  onClose() {
    // apenas limpar estado; o módulo esconde o overlay em seguida (fade se `data-modal-fade`)
  },
  onEscape(e) {
    // return false para impedir fechar (ex.: combobox aberto)
  },
});

// Abrir (salva foco para devolver ao fechar)
GranaGoModal.open(overlay, { trigger: document.getElementById("btn-abrir") });

// Fechar (backdrop, ESC, data-modal-close ou API)
GranaGoModal.close(overlay);
```

## Comportamentos automáticos

- Clique no backdrop (fora do painel) → fecha o modal do topo.
- `Escape` → fecha o modal do topo (respeita `onEscape`).
- `[data-modal-close]` → fecha o modal ancestral.
- Focus trap (Tab) no painel do modal aberto.
- `aria-modal`, `aria-hidden`, `role="dialog"`.
- Bloqueio de scroll do `documentElement` enquanto houver modal aberto.

## Novos módulos (metas, planejamentos, etc.)

1. Copie o markup acima.
2. Registre com `GranaGoModal.bind` e use `open` / `close`.
3. Não adicione listeners próprios em backdrop, ESC ou botão fechar.
