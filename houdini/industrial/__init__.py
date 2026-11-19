"""Civil industrial models. All published coordinates are Y-up and measured in metres."""
from importlib import import_module

EQUIPMENT = (
    "air_receiver", "bottle_rack", "cable_reel", "chem_skid", "control_station",
    "heat_exchanger", "hpu", "ibc_stack", "pipe_bolster", "tugger_winch",
    "waste_skip", "xmas_tree",
)
STRUCTURES = ("survival_craft", "lifeboat_davit", "helicopter")
LIGHTING = {
    "beacon": ("beacon_pole","beacon_wall","beacon_lens"),
    "escape_route": ("escape_sign","escape_strip"),
    "flood": ("flood_head","flood_pole","flood_pole_pair","flood_rail"),
    "helideck_lights": ("helideck_perimeter","helideck_circle","helideck_edge_flood"),
    "obstruction_light": ("obstruction_light",),
    "tube_light": ("tube_light_ceiling","tube_light_pole","tube_light_broken"),
    "wellglass": ("wellglass",),
    "work_light": ("work_tripod","work_handlamp"),
}
FIXTURES = {asset: family for family, assets in LIGHTING.items() for asset in assets}


def names():
    return (*EQUIPMENT, *STRUCTURES, *FIXTURES)


def _meshes(asset):
    if asset not in names():
        raise ValueError(f"Unknown industrial asset {asset!r}")
    module = import_module(f".recipes.{FIXTURES.get(asset, asset)}", __name__)
    if asset in FIXTURES:
        from .lighting import Fam
        family = Fam()
        module.define(family)
        for part_name, instance in family.objects[asset]["inst"]:
            part = family.parts[part_name]
            placement = instance @ part["base"].inverted()
            for piece in family.b.lo + family.b.hi:
                if piece.tag == part["tag"] and piece.faces:
                    yield piece.output(placement)
    else:
        for piece in module.build():
            if piece.faces:
                yield piece.output()



def parts(asset):
    used = set()
    counts = {}
    for data in _meshes(asset):
        base = data["name"]
        number = counts.get(base, 0) + 1
        name = base if number == 1 else f"{base}_{number:03}"
        while name in used:
            number += 1
            name = f"{base}_{number:03}"
        counts[base] = number
        used.add(name)
        data["name"] = name
        yield data


def surface(name, asset=None):
    from .surfaces import lookup
    return lookup(name, asset, FIXTURES)
