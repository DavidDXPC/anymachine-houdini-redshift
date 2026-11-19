# AnyShot no Solaris

O exemplo incluído tem um dolly de 48 frames com uma lente de 42 mm. A frame 49 corta para uma órbita de 65 mm com mudança de foco. O plano termina na frame 84, a 24 fps. [Manifesto](camera/examples/solaris_shots.json)

## Preparar a realização

1. Lê o briefing, o storyboard e o animatic. Anota os cortes na timeline. Usa os nomes e caminhos das peças e personagens existentes no Stage.
2. Traduz a intenção para um movimento mensurável. Para «aproxima-te devagar», indica o ponto inicial e o final, a duração e a lente. Para «muda o foco do comando para o visor», usa `focus.mode = rack` com duas posições ou dois nomes de prims. Repetir o primeiro alvo num segundo key cria uma pausa antes da mudança.
3. Para aproveitar uma planta, alinha uma distância conhecida, a origem e a direção das paredes com o cenário. Converte as marcas em coordenadas em metros. O agente faz esta leitura antes de escrever o manifesto.
4. Carrega as câmaras no Solaris. Revê a primeira, a última e uma frame intermédia de cada plano. Confirma o alvo, os cortes, o foco e as colisões antes dos finais.

## Usar a cena

Com o Python do Houdini 22 ou com Python, NumPy e OpenUSD, corre o exemplo a partir desta pasta.

```powershell
hython solaris.py camera/examples/solaris_shots.json corte.usda
hython solaris.py camera/examples/solaris_shots.json corte_com_cenario.usda --scene cenario.usdc --settings /Render/Settings
```

O primeiro comando cria as câmaras numa cena vazia, em metros e com Y para cima. O segundo escreve uma camada que compõe o cenário e liga a câmara à prim `UsdRenderSettings` indicada. O relatório JSON identifica a câmara final, os intervalos inclusivos e as ocorrências de clearance. Numa produção conjunta, o host pode chamar o módulo diretamente.

```python
from family.anyshot import solaris
cut = solaris.author(stage, manifest, manifest_folder)
settings.CreateCameraRel().SetTargets([cut["camera"]])
```

Para uma imagem, usa o Redshift no Solaris e renderiza a frame pretendida. Para vídeo, renderiza as frames 1 a `cut["frames"]` para EXR e monta a sequência a `cut["fps"]`. Cada plano conserva uma câmara editável em `/World/Shots`. A câmara `Cut` contém a montagem com as mudanças de posição e de lente no início de cada plano.

## Campos do manifesto

| Campo | Utilização |
|---|---|
| `fps`, `defaults`, `shots` | A sequência usa uma cadência. Cada plano pode substituir os valores comuns. A duração é dada em `frames` ou `seconds`. |
| `input_axes` | As coordenadas e os offsets são em metros. O valor por omissão é o eixo vertical do Stage. Para importar coordenadas dos manifestos originais, usa `"Z"`. |
| `eye`, `end_eye`, `target`, `end_target` | Coordenadas, caminho absoluto USD ou nome único de prim. O alvo segue o centro dos limites dessa prim em cada frame. |
| `keys` | Usa `t` de 0 a 1, `pos`, `aim`, `pos_obj`, `aim_obj`, `pos_offset` e `aim_offset`. Dois pontos interpolam em linha reta. Três ou mais dão uma curva Catmull–Rom. Um campo omitido mantém o valor anterior. |
| `move`, `ease` | `static`, `dolly`, `push_in`, `truck`, `pedestal`, `crane`, `pan`, `tilt`, `path`, `walkthrough`, `orbit`, `zoom` e `dolly_zoom`. As acelerações são `linear`, `in`, `out` ou `inout`. |
| `orbit` | `center` ou `center_obj`, `radius`, `height`, `start_deg`, `end_deg`. A altura é absoluta e o ângulo começa em +X. |
| `lens`, `end_lens`, `sensor`, `aspect`, `res` | Distância focal e largura do sensor em milímetros. `s35` tem 24,89 mm e `ff` tem 36 mm. O ângulo de visão usa o `aspect` explícito ou a proporção de `res`. O dolly zoom corrige a lente pela distância ao `subject`. |
| `focus`, `fstop`, `fstop_keys` | `track_aim`, `point`, `track`, `rack` e `none`. Um rack usa chaves `t` e `pos` ou `obj`. A distância de foco é medida ao longo do eixo ótico. |
| `roll`, `handheld` | O roll é em graus e também pode ter keys. `handheld` aceita uma intensidade ou os perfis `none`, `subtle` e `walk`. São oscilações locais determinísticas. |
| `clearance` | Por omissão, verifica 0,45 m em cada frame. `include` e `exclude` aceitam listas de caminhos de prims e incluem os descendentes. `on_hit: "error"` interrompe a montagem ou `"report"` entrega os resultados com o caminho, a frame e a distância em metros. |

## Alcance

O controlo de clearance mede a distância da posição da câmara às superfícies das malhas USD visíveis a cada frame inteira. Primitivas analíticas, como esferas, usam limites conservadores. Malhas com polígonos côncavos devem ser trianguladas pelo autor. Personagens deformadas por esqueleto e instâncias de pontos precisam de uma malha de colisão animada que já contenha as posições deformadas. A verificação cobre o centro da câmara. Para conferir o enquadramento e as margens da lente, usa as imagens de revisão.

O porto preserva a interpolação dos percursos, o dolly zoom, as curvas de lente e o rack de foco do AnyShot. Os perfis de câmara ao ombro são aproximações procedurais. As definições de amostragem, shutter, efeitos de lente, exposição e grade pertencem à produção Solaris/Redshift e à pós-produção. O briefing em texto e a planta entram na preparação pelo agente. Esta entrada local recebe o manifesto resultante e ficheiros USD. Os endpoints fal, credenciais e workers documentados no [serviço original](README.md#serviço-de-origem) pertencem ao fluxo upstream.
