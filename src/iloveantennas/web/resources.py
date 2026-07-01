from iloveantennas.simulator.core.materials import MaterialLibrary


def _conductor(name: str) -> dict:
    material = getattr(MaterialLibrary, name)
    return {
        "name": name,
        "sigma": material.api_sigma,
        "color": material.color_hex,
    }


def _dielectric(name: str) -> dict:
    material = getattr(MaterialLibrary, name)
    return {
        "name": name,
        "epsilon_r": material.epsilon_r,
        "tan_delta": material.tan_delta,
        "color": material.color_hex,
    }


MATERIALS = {
    "conductors": [_conductor(name) for name in ("COPPER", "ALUMINUM", "GOLD", "SILVER", "PEC")],
    "dielectrics": [_dielectric(name) for name in ("FR4", "ROGERS_4003C", "TEFLON", "AIR")],
}

ANTENNA_TYPES = [
    {
        "id": "dipole",
        "name": "Dipolo",
        "description": "Antena dipolo de meia onda (λ/2)",
        "icon": "📡",
        "params": ["frequency", "length", "radius"],
    },
    {
        "id": "v_dipole",
        "name": "Dipolo em V",
        "description": "Dipolo em V com ângulo entre braços",
        "icon": "✅",
        "params": ["frequency", "length", "radius"],
    },
    {
        "id": "folded_dipole",
        "name": "Dipolo Dobrado",
        "description": "Dipolo de meia onda dobrado para maior impedância",
        "icon": "🧷",
        "params": ["frequency", "length", "radius"],
    },
    {
        "id": "monopole",
        "name": "Monopolo",
        "description": "Antena monopolo com plano de terra (λ/4)",
        "icon": "📶",
        "params": ["frequency", "length", "radius"],
    },
    {
        "id": "yagi",
        "name": "Yagi-Uda",
        "description": "Antena direcional com elementos parasitas",
        "icon": "📺",
        "params": ["frequency", "num_directors"],
    },
    {
        "id": "patch",
        "name": "Patch Microstrip",
        "description": "Antena planar para aplicações compactas",
        "icon": "📱",
        "params": ["frequency", "substrate_er", "substrate_h"],
    },
    {
        "id": "helix",
        "name": "Helicoidal",
        "description": "Antena para polarização circular",
        "icon": "🌀",
        "params": ["frequency", "turns"],
    },
    {
        "id": "horn",
        "name": "Corneta (Horn)",
        "description": "Antena de abertura para alto ganho",
        "icon": "📢",
        "params": ["frequency", "aperture_width", "aperture_height", "flare_length"],
    },
    {
        "id": "dish",
        "name": "Parabólica",
        "description": "Refletor parabólico de alto ganho",
        "icon": "📡",
        "params": ["frequency", "dish_diameter", "focal_length"],
    },
    {
        "id": "lpda",
        "name": "Log-Periódica",
        "description": "Antena direcional de banda larga",
        "icon": "📶",
        "params": ["frequency", "tau", "sigma"],
    },
    {
        "id": "loop",
        "name": "Loop",
        "description": "Antena loop circular",
        "icon": "⭕",
        "params": ["frequency", "loop_radius", "radius"],
    },
    {
        "id": "biquad",
        "name": "Biquad",
        "description": "Antena Quad Dupla com Refletor",
        "icon": "💠",
        "params": ["frequency", "side_length", "reflector_distance"],
    },
    {
        "id": "discone",
        "name": "Discone",
        "description": "Antena de banda larga omnidirecional",
        "icon": "☂️",
        "params": ["frequency", "disc_radius", "cone_radius", "cone_height"],
    },
]
