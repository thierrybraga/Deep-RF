import numpy as np
from core.constants import C0
from core.geometry import AntennaFactory
from config import AntennaConfig

def create_antenna(config: AntennaConfig):
    """Cria antena baseada na configuração"""
    wavelength = C0 / config.frequency
    
    if config.type == 'dipole':
        length = config.length or wavelength / 2
        return AntennaFactory.create_dipole(length=length, radius=config.radius)
    
    elif config.type == 'v_dipole':
        length = config.length or wavelength / 2
        return AntennaFactory.create_v_dipole(
            length=length,
            radius=config.radius
        )
    
    elif config.type == 'folded_dipole':
        length = config.length or wavelength / 2
        spacing = length * 0.02
        return AntennaFactory.create_folded_dipole(
            length=length,
            radius=config.radius,
            spacing=spacing
        )
    
    elif config.type == 'monopole':
        length = config.length or wavelength / 4
        ground_size = wavelength
        return AntennaFactory.create_monopole(
            length=length,
            radius=config.radius,
            ground_size=ground_size
        )
    
    elif config.type == 'yagi':
        return AntennaFactory.create_yagi(
            frequency=config.frequency,
            num_directors=config.num_directors
        )
    
    elif config.type == 'patch':
        return AntennaFactory.create_patch(
            frequency=config.frequency,
            substrate_er=config.substrate_er,
            substrate_h=config.substrate_h
        )
    
    elif config.type == 'helix':
        return AntennaFactory.create_helix(
            frequency=config.frequency,
            num_turns=config.turns
        )
    
    elif config.type == 'horn':
        return AntennaFactory.create_horn(
            frequency=config.frequency,
            aperture_width=config.aperture_width or wavelength,
            aperture_height=config.aperture_height or wavelength*0.75,
            length=config.flare_length or wavelength*1.5
        )
        
    elif config.type == 'dish':
        return AntennaFactory.create_parabolic(
            frequency=config.frequency,
            diameter=config.dish_diameter or wavelength*4,
            focal_length=config.focal_length or wavelength*1.5
        )
        
    elif config.type == 'lpda':
        return AntennaFactory.create_log_periodic(
            frequency_min=config.frequency * 0.7,
            frequency_max=config.frequency * 1.3,
            tau=config.tau,
            sigma=config.sigma
        )
        
    elif config.type == 'loop':
        radius = config.loop_radius or wavelength / (2 * np.pi) # 1 comprimento de onda de circunferência
        return AntennaFactory.create_loop(
            radius=radius,
            wire_radius=config.radius
        )

    elif config.type == 'biquad':
        return AntennaFactory.create_biquad(
            side_length=config.side_length,
            frequency=config.frequency,
            wire_radius=config.radius,
            reflector_distance=config.reflector_distance
        )
        
    elif config.type == 'discone':
        return AntennaFactory.create_discone(
            frequency=config.frequency,
            disc_radius=config.disc_radius,
            cone_radius=config.cone_radius,
            cone_height=config.cone_height,
            wire_radius=config.radius
        )
    
    else:
        raise ValueError(f"Tipo de antena não suportado: {config.type}")


def get_antenna_geometry_data(antenna) -> dict:
    """Extrai dados de geometria para renderização 3D"""
    geometries = []
    
    for geom in antenna.geometries:
        geom_type = type(geom).__name__
        
        if geom_type == 'Wire':
            geometries.append({
                'type': 'wire',
                'start': [geom.start.x, geom.start.y, geom.start.z],
                'end': [geom.end.x, geom.end.y, geom.end.z],
                'radius': geom.radius,
                'material': geom.material.name if geom.material else 'copper'
            })
        
        elif geom_type == 'Rectangle':
            geometries.append({
                'type': 'rectangle',
                'center': [geom.center.x, geom.center.y, geom.center.z],
                'width': geom.width,
                'height': geom.height,
                'normal': [geom.normal.x, geom.normal.y, geom.normal.z],
                'material': geom.material.name if geom.material else 'copper'
            })
        
        elif geom_type == 'Cylinder':
            geometries.append({
                'type': 'cylinder',
                'base': [geom.base.x, geom.base.y, geom.base.z],
                'axis': [geom.axis.x, geom.axis.y, geom.axis.z],
                'radius': geom.radius,
                'height': geom.height,
                'material': geom.material.name if geom.material else 'copper'
            })
        
        elif geom_type == 'Helix':
            # Gera pontos da hélice
            points = []
            n_points = 200  # Aumentado para 200 pontos para suavizar curva
            for i in range(n_points):
                t = i / (n_points - 1) * geom.turns * 2 * np.pi
                x = geom.center.x + geom.radius * np.cos(t)
                y = geom.center.y + geom.radius * np.sin(t)
                z = geom.center.z + geom.pitch * t / (2 * np.pi)
                points.append([x, y, z])
            
            geometries.append({
                'type': 'helix',
                'points': points,
                'wire_radius': geom.wire_radius,
                'material': geom.material.name if geom.material else 'copper'
            })
        
        elif geom_type == 'Horn':
            geometries.append({
                'type': 'horn',
                'center': [geom.center.x, geom.center.y, geom.center.z],
                'aperture_width': geom.aperture_width,
                'aperture_height': geom.aperture_height,
                'throat_width': geom.throat_width,
                'throat_height': geom.throat_height,
                'length': geom.length,
                'wall_thickness': geom.wall_thickness,
                'material': geom.material.name if geom.material else 'copper'
            })
            
        elif geom_type == 'ParabolicDish':
            geometries.append({
                'type': 'dish',
                'center': [geom.center.x, geom.center.y, geom.center.z],
                'diameter': geom.diameter,
                'focal_length': geom.focal_length,
                'thickness': geom.thickness,
                'axis': [geom.axis.x, geom.axis.y, geom.axis.z],
                'material': geom.material.name if geom.material else 'copper'
            })
    
    # Bounding box
    bb = antenna.get_bounding_box()
    
    return {
        'geometries': geometries,
        'bounding_box': {
            'min': [bb.min_point.x, bb.min_point.y, bb.min_point.z],
            'max': [bb.max_point.x, bb.max_point.y, bb.max_point.z],
            'size': [bb.size.x, bb.size.y, bb.size.z],
            'center': [bb.center.x, bb.center.y, bb.center.z]
        },
        'feed_point': [antenna.feed_point.x, antenna.feed_point.y, antenna.feed_point.z] if antenna.feed_point else [0, 0, 0],
        'num_nodes': len(antenna.nodes),
        'num_edges': len(antenna.edges)
    }
