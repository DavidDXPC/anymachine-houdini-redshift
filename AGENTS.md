# AnyMachine

Quando o pedido envolver cenário, adereços e realização, usa a produção integrada. Lê `examples/workshop.json` e a secção «Produção integrada» da skill abaixo. O resultado é uma única cena Solaris com os quatro módulos. O código nos forks em `family/` inclui fluxos históricos; para Houdini usa a entrada `solaris` de cada módulo.

Para trabalho de modelação, rig, lookdev e render, segue a [skill AnyMachine para Houdini 22 e Redshift](.agents/skills/anymachine-houdini-redshift/SKILL.md). A execução normal começa em `anymachine.py`. As receitas estão em `houdini/`. Os comandos e os formatos de entrega estão no [README](README.md).

Mantém a escala em metros, o palco USD em Y-up e os materiais separados por peça. Lê as regras da produção que recebe o asset antes de abrir sessões, fazer cooks ou renderizar.
