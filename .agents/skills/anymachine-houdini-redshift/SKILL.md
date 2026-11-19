---
name: anymachine-houdini-redshift
description: Modela máquinas por referência, constrói rigs mecânicos e tecidos articulados em Houdini 22 e prepara materiais, luz, validação e render Redshift no Solaris. Usa para dobradiças, robôs com pernas, mecanismos de mochilas e props industriais.
---

# AnyMachine para Houdini 22 e Redshift

Começa pelo movimento pedido. Identifica a peça fixa, as peças móveis, as superfícies que se tocam e o controlo que o artista vai animar. Usa metros e Y como eixo vertical. Responde na língua do utilizador. Conserva os nomes de nós e parâmetros em inglês.

1. **Lê a referência.** Fixa uma dimensão conhecida e o mesmo enquadramento para comparação. Distingue o que se mede, o que se infere e o que precisa de outra vista. Um detalhe invisível pode ficar por decidir.
2. **Escolhe a receita.** Na raiz do fork, executa `hython anymachine.py list` e depois `list <asset>`. Usa `houdini/rigs` para dobradiças, pernas e tecidos, `houdini/industrial` para peças rígidas ou `houdini/stilt_asset.py` para o esqueleto publicado. Para uma máquina nova, começa pela receita de comportamento mais próxima.
3. **Define os controlos no repouso.** Mede o eixo e os extremos. Separa a carcaça do mecanismo. Expõe o intervalo 0–1 e descreve a unidade física que lhe corresponde. Fecha o laptop antes de medir a folga. Mede o pé no referencial do chão durante o apoio. Testa o fecho da mochila também com a mochila cheia.
4. **Trabalha no Solaris.** Abre ou gera o HIP da licença em uso. Em `/stage/MACHINE`, seleciona o clip ou a pose manual. Usa os nomes sob `/Machine/Parts` para ajustar peças com SOP Modify ou transformar rigidamente com Xform. Para o Stilt, edita as poses através de UsdSkel/KineFX e preserva bind pose, ordem das juntas e pesos. Em `/Machine/Looks`, confirma material, UV e espaço de cor por mapa.
5. **Ilumina e mede.** Usa `/stage/STUDIO` para a vista e resolução. Em `/stage/REDSHIFT`, confirma o delegate da build instalada, o produto EXR, a câmara e ACEScg. Usa as amostras e a exposição medidas para a cena. Quando o utilizador pedir uma verificação, abre o ficheiro exportado, lê o EXR e compara a mesma vista e frame com a referência.
6. **Entrega o que foi verificado.** Indica a versão da cena, controlos, clips, dependências externas, resultados e aproximações. Guarda as escolhas artísticas para o utilizador. Na pasta de produção dele, segue as regras locais de autorização de cook e render.

O [pipeline](../../../PIPELINE.md) explica a construção e as medições por família. Os [comandos](../../../README.md) geram HIP, USD e GLB. Os relatórios e imagens históricos são evidência sobre o original.
