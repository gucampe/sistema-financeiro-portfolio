<!-- Data de criação: 2026-07-31 -->
# Hero Person — GranaGo (ensaio fotográfico)

Conjunto de 8 imagens do mesmo sujeito para o hero da landing, com fundo transparente (WebP + PNG).

## Especificações

| Item | Valor |
|------|--------|
| Formato | WebP (preferencial) + PNG com alpha |
| Resolução | 1707 × 2560 px (≥ 2500 px de altura) |
| Fundo | Transparente (RGBA) |
| Estilo | Editorial comercial, iluminação tipo Apple |
| Sujeito | Homem brasileiro ~30 anos, camiseta branca lisa, celular sem marca |

## Estrutura

```
07_hero_person/
├── left/          # celular na mão ESQUERDA, dedo indicador direito
│   ├── 01_calm_realization.webp|.png
│   ├── 02_engaged.webp|.png
│   ├── 03_soft_smile.webp|.png
│   └── 04_premium_editorial.webp|.png
└── right/         # celular na mão DIREITA, dedo indicador esquerdo
    ├── 01_calm_realization.webp|.png
    ├── 02_engaged.webp|.png
    ├── 03_soft_smile.webp|.png
    └── 04_premium_editorial.webp|.png
```

## Conceitos

1. **calm_realization** — realização calma (“agora faz sentido”)
2. **engaged** — um pouco mais engajado interagindo com o celular
3. **soft_smile** — sorriso suave de satisfação após um insight
4. **premium_editorial** — versão editorial mais premium (campanha)

## Uso na landing

- Slot atual: `static/img/landing/hero-person.webp`
- Default copiado: `left/04_premium_editorial.webp` (celular na mão esquerda; espaço à direita para floats HTML)
- Alternar para `right/` se a composição dos cards flutuantes exigir espelhamento

## Convenção de pastas

- `left/` = celular na **mão esquerda** do sujeito (dedo indicador direito)
- `right/` = celular na **mão direita** do sujeito (dedo indicador esquerdo)

A lateralidade foi verificada por posição do aparelho no frame (não pelo nome original do arquivo de geração).

## Referência de identidade

`docs/hero_ai_assets/06_reference/founder.png`
