---
name: anyscene-solaris
description: Build or revise a 3D environment and dress it from reference, a room plan, or an AnyScene preset in Houdini 22 Solaris with Redshift. Use for set layout, architecture, practical lights, metre-scale model placement, and USD handoff.
---

# AnyScene · Houdini 22 / Solaris / Redshift

Start from the reference, floor plan and hero action. Keep one labelled set under `/World/Set`. Work in metres with Y up. Leave camera coverage and room around the product. For a new set, agree the scale from one measured feature before mixing assets from different sources.

1. Run `hython solaris.py --list`. Choose a preset that matches the space. Use `--preset <name> --write-spec set.json` to see its editable layout. For a new space, supply the `architecture`, `props`, `materials` and `lights` fields in the same schema.
2. Block the structure first. Set the floor height, openings, support surfaces and available sightlines. Every object's `at` is its bottom centre. Align supported props to the actual top of the bench or shelf. Preserve scale, contact and projected width at the camera.
3. Read the preset's `catalog` for upstream IDs and dimensions. Separate placements by `id` and share models using the `asset` key. Put prepared USD models under `assets/` or give explicit paths in the `assets` map. Keep unavailable pieces labelled as blockouts. Record which references and dimensions remain approximate.
4. Choose material classes and set the visible light sources. Use Redshift Standard Material for the beauty and Preview Surface for portable inspection. Check the exact installed Redshift and Houdini builds before testing the delegate. Check that the Solaris stage and render use the intended OCIO/ACEScg setup.
5. Run `hython solaris.py --spec set.json --output set.usda` or call `solaris.author(stage,spec,base_dir)`. Layer the result in Solaris. Inspect model bounds, support contacts, sightlines and the returned proxy/reference lists. A stage authored with OpenUSD still needs review under the live Redshift delegate for appearance. Only cook, render, or open a session when the project permits it.

The 4 upstream manifests, 2 purpose-built studies and 1 original web fixture are documented in [README.md](README.md). The historical generation, Blender and Unreal workflows are in [UPSTREAM_WORKFLOW.md](UPSTREAM_WORKFLOW.md).
