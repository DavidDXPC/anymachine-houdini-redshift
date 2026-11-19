# Da referência à máquina em Solaris

## Medir antes de modelar

Escolhe uma medida conhecida. Alinha frente, lado e topo pela mesma escala. Regista a unidade, o eixo vertical, o centro de cada junta e os limites observáveis. Conserva a imagem e a medida que justificam cada eixo. O palco do fork usa metros e Y-up. As receitas que partem de medições Z-up convertem os pontos uma vez, na saída.

Para uma peça nova, separa a silhueta, a estrutura e os detalhes que a câmara vai resolver. Usa SOPs de perfil e revolução para peças de torno, Sweep para tubagens e Copy to Points para repetições. Dá um nome funcional a cada corpo. Junta por material só na exportação que o exigir.

## Escolher o movimento

| Caso | Construção e medição |
|---|---|
| Dobradiça | Mede a origem e a direção do eixo na pose fechada. Divide o corpo fixo e a tampa. Varre o controlo e mede a distância ao teclado, incluindo as extremidades. |
| Pernas | Define a pose de repouso, o comprimento dos segmentos e o lado para onde o joelho dobra. Resolve a IK para o alvo do pé. Compara contacto e deslocamento no referencial do chão durante a fase de apoio. |
| Tecidos | Separa corpo, forro, aba, dentes, cursor, fivela e alças. Parametriza o zip por distância à curva. Verifica pares de controlos como enchimento e fecho. Regista os contactos previstos nas costuras. |
| Stilt | Mantém as matrizes de bind, o mapeamento de índices das juntas e os subconjuntos de material. Compara a deformação USD com o GLB nas mesmas frames e entre chaves. |
| Peças industriais | Usa a receita da peça e as vistas de referência. Compara a silhueta, o perfil das chapas e a posição das uniões. Nas luminárias, distingue a luminosidade da lente da luz que ilumina o cenário. |

## Lookdev e entrega

Trabalha em `/stage`. Confirma metros, Y-up e a câmara. Mantém o material por peça. Lê a cor base no espaço de cor da imagem. Lê normais, metal e rugosidade como dados Raw. Num mapa ORM, o verde é rugosidade e o azul metal. Seleciona o delegate Redshift da build instalada e confirma ACEScg no produto EXR. [Gestão de cor da Maxon](https://help.maxon.net/r3d/houdini/en-us/Content/html/Color%2BManagement%2B-%2BOCIO%2BACES.html)

Compara as vistas do mesmo ângulo e frame. Usa `--view front`, `left`, `right`, `rear`, `top`, `bottom` ou `hero`. Exporta HIP para edição, USD para composição e GLB para reprodução portátil. Reabre a entrega, lê os materiais e mede uma pose extrema. Quando houver render, confirma o delegate, as dimensões e o espaço de cor nos metadados do EXR.

As métricas de cada rig vêm de `check_rigs.py`. Os JSON dentro de `references/` documentam o original. As escolhas artísticas e a aprovação do resultado pertencem ao utilizador.
