
MATERIALS = {
    'conductors': [
        {'name': 'COPPER', 'sigma': 5.96e7, 'color': '#b87333'},
        {'name': 'ALUMINUM', 'sigma': 3.77e7, 'color': '#848789'},
        {'name': 'GOLD', 'sigma': 4.1e7, 'color': '#ffd700'},
        {'name': 'SILVER', 'sigma': 6.3e7, 'color': '#c0c0c0'},
        {'name': 'PEC', 'sigma': 1e30, 'color': '#333333'}
    ],
    'dielectrics': [
        {'name': 'FR4', 'epsilon_r': 4.4, 'tan_delta': 0.02, 'color': '#2e8b2e'},
        {'name': 'ROGERS_4003C', 'epsilon_r': 3.55, 'tan_delta': 0.0027, 'color': '#8b4513'},
        {'name': 'TEFLON', 'epsilon_r': 2.1, 'tan_delta': 0.0002, 'color': '#f5f5f5'},
        {'name': 'AIR', 'epsilon_r': 1.0, 'tan_delta': 0, 'color': '#87ceeb'}
    ]
}

ANTENNA_TYPES = [
    {
        'id': 'dipole',
        'name': 'Dipolo',
        'description': 'Antena dipolo de meia onda (λ/2)',
        'icon': '📡',
        'params': ['frequency', 'length', 'radius']
    },
    {
        'id': 'v_dipole',
        'name': 'Dipolo em V',
        'description': 'Dipolo em V com ângulo entre braços',
        'icon': '✅',
        'params': ['frequency', 'length', 'radius']
    },
    {
        'id': 'folded_dipole',
        'name': 'Dipolo Dobrado',
        'description': 'Dipolo de meia onda dobrado para maior impedância',
        'icon': '🧷',
        'params': ['frequency', 'length', 'radius']
    },
    {
        'id': 'monopole',
        'name': 'Monopolo',
        'description': 'Antena monopolo com plano de terra (λ/4)',
        'icon': '📶',
        'params': ['frequency', 'length', 'radius']
    },
    {
        'id': 'yagi',
        'name': 'Yagi-Uda',
        'description': 'Antena direcional com elementos parasitas',
        'icon': '📺',
        'params': ['frequency', 'num_directors']
    },
    {
        'id': 'patch',
        'name': 'Patch Microstrip',
        'description': 'Antena planar para aplicações compactas',
        'icon': '📱',
        'params': ['frequency', 'substrate_er', 'substrate_h']
    },
    {
        'id': 'helix',
        'name': 'Helicoidal',
        'description': 'Antena para polarização circular',
        'icon': '🌀',
        'params': ['frequency', 'turns']
    },
    {
        'id': 'horn',
        'name': 'Corneta (Horn)',
        'description': 'Antena de abertura para alto ganho',
        'icon': '📢',
        'params': ['frequency', 'aperture_width', 'aperture_height', 'flare_length']
    },
    {
        'id': 'dish',
        'name': 'Parabólica',
        'description': 'Refletor parabólico de alto ganho',
        'icon': '📡',
        'params': ['frequency', 'dish_diameter', 'focal_length']
    },
    {
        'id': 'lpda',
        'name': 'Log-Periódica',
        'description': 'Antena direcional de banda larga',
        'icon': '📶',
        'params': ['frequency', 'tau', 'sigma']
    },
    {
        'id': 'loop',
        'name': 'Loop',
        'description': 'Antena loop circular',
        'icon': '⭕',
        'params': ['frequency', 'loop_radius', 'radius']
    },
    {
        'id': 'biquad',
        'name': 'Biquad',
        'description': 'Antena Quad Dupla com Refletor',
        'icon': '💠',
        'params': ['frequency', 'side_length', 'reflector_distance']
    },
    {
        'id': 'discone',
        'name': 'Discone',
        'description': 'Antena de banda larga omnidirecional',
        'icon': '☂️',
        'params': ['frequency', 'disc_radius', 'cone_radius', 'cone_height']
    }
]
