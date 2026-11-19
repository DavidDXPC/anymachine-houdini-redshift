# AnyKit para Houdini 22 e Redshift

Cria uma biblioteca de props em metros para o Solaris. O mesmo manifesto controla a paleta, o acabamento, as dimensões e a posição de cada peça. Os materiais incluem Redshift Standard Material e USD Preview Surface.

## Começar

Na raiz do repositório, usa o `hython` do Houdini 22. Também podes usar Python com `usd-core` e `numpy` para preparar o USD. A escrita do ficheiro corre em CPU.

```powershell
hython -m solaris examples/workshop.json out/workshop.usdz --per-item
```

Abre `out/workshop.usdz` com um **Reference LOP**. O kit fica em `/World/Kit`. A pasta `out/workshop_items/` contém um USDZ autónomo por prop, com a origem no centro da base. O relatório `out/workshop.manifest.json` regista dimensões, triângulos e variantes. Escolhe **Redshift** no viewport do Solaris para rever os materiais.

## Compor numa cena

```python
import json
from pathlib import Path
from pxr import Usd
from solaris import author

manifest = Path("examples/workshop.json")
spec = json.loads(manifest.read_text(encoding="utf-8"))
stage = Usd.Stage.CreateNew("workshop.usda")
report = author(stage, spec, manifest.parent)
stage.GetRootLayer().Save()
```

No repositório da família, importa `from family.anykit.solaris import author`. Podes voltar a chamar a função para substituir `/World/Kit` e conservar o resto da cena.

## Manifesto

O [exemplo de oficina](examples/workshop.json) coloca a bancada no chão e o candeeiro sobre o tampo a 0,90 m. As coordenadas são XYZ, com Y para cima e +Z para a frente. As peças têm posição relativa ao kit. A posição predefinida é a origem. Usa posições diferentes para montar o conjunto.

| Campo | Uso |
|---|---|
| `name`, `style.description` | Nome do conjunto e direção visual partilhada |
| `references` | Até quatro caminhos locais para fotografias ou pranchas. São resolvidos junto do manifesto e registados no relatório |
| `style.palette`, `style.wear` | Cores hexadecimais em sRGB por acabamento e desgaste de 0 a 1 que altera a rugosidade dos props procedurais |
| `items[].id`, `label` | Identificador USD único e legenda opcional |
| `kind` | `workbench`, `stool`, `cabinet`, `crate`, `shelf`, `toolbox`, `desk_lamp`, `mug`, `bottle`, `monitor` |
| `position`, `yaw` | Centro da base em metros e orientação final em graus sobre Y |
| `height_m` ou `size_m` | Altura proporcional ou ajuste explícito de largura, altura e profundidade em metros |
| `source`, `prim` | Ficheiro USD, USDZ, GLB ou glTF estático. Em USD, `prim` substitui a primitiva predefinida da fonte |
| `source_yaw`, `meters_per_unit` | Corrigem a frente e a escala de uma fonte que traga metadados incorretos |
| `lod`, `lod1_source` | Seleciona `high` ou `low` e permite fornecer a versão simplificada de uma malha externa |
| `why`, `tags` | Motivo de seleção e classificação gravados na primitiva |

A paleta aceita `enamel`, `metal`, `dark`, `wood`, `rubber`, `accent`, `ceramic`, `glass` e `screen`. Os materiais de uma fonte externa acompanham o asset. O vidro procedural usa transmissão e o ecrã tem emissão.

Para reaproveitar um manifesto de preparação anterior, o leitor aceita `glb`, `h` e `fit`. Neste último, a ordem original é largura, profundidade, altura. Com `gen: "tripo"`, a frente +X roda para +Z. Se a pose de referência vier aplicada à raiz de um glTF, ativa `strip_root_rotation: true`.

## Referências, revisão e entrega

1. Escolhe fotografias do mesmo universo visual. Regista época, materiais, paleta e fabricante fictício em `style.description`. Confirma a silhueta e uma dimensão real de cada item.
2. Junta as pranchas dos candidatos. Para uma peça externa, compara as alternativas sob a mesma câmara e luz e regista a escolha em `why`. O importador trabalha com ficheiros locais. A geração de novas imagens ou malhas continua a ser uma etapa separada.
3. Revê as peças montadas à escala, em material e em cinzento. Confirma a orientação, as juntas, o vidro, a legibilidade de etiquetas e a continuidade dos materiais. Usa `size_m` apenas quando as três dimensões forem conhecidas.
4. Seleciona a variante `lod` em **Set Variant LOP**. As receitas baixam o número de lados das superfícies curvas ou retiram detalhes pequenos. Para uma malha externa, fornece `lod1_source` ou coloca `nome_lod1.glb` junto de `nome.glb`.
5. Entrega USDZ para reunir geometria, materiais e dependências locais. USD/USDA/USDC permitem editar ou referenciar assets nos caminhos de origem. O manifesto e os ficheiros de referência podem acompanhar a entrega.

O importador glTF lê malhas trianguladas estáticas, hierarquias, normais, o primeiro canal UV e texturas de cor, normal e ORM em PNG/JPEG/WebP. GLB comprimido com Draco, rigs, morph targets, transformações de UV e malhas com linhas requerem um USD preparado. Para uma textura embebida, o importador usa uma cache temporária identificada pelo conteúdo antes de empacotar o USDZ. O modo local conserva as texturas de origem e aceita LOD externo preparado. O relatório permite medir o orçamento final.

A licença e as ferramentas do [AnyKit original](https://github.com/apekshik/anykit/tree/9ab61cac00a5eb3afdd87d5ee989134930c307b8) acompanham o fork. O guia anterior descreve a geração remota com fal, Meshy e Tripo. [Guia original](https://github.com/apekshik/anykit/blob/9ab61cac00a5eb3afdd87d5ee989134930c307b8/README.md)