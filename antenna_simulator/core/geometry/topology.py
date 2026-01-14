"""
Módulo de Topologia de Antenas
Implementa o sistema de grafos para representar a estrutura física e elétrica das antenas.
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import networkx as nx

from .primitives import Vector3D, GeometryPrimitive, Wire, BoundingBox, Rectangle
from ..constants import Material, MaterialLibrary

@dataclass
class AntennaNode:
    """
    Nó no grafo da antena (ponto de conexão).
    
    Attributes:
        id: Identificador único
        position: Posição 3D
        node_type: Tipo (feed, ground, junction, terminal)
        properties: Propriedades adicionais
    """
    id: int
    position: Vector3D
    node_type: str = "junction"  # feed, ground, junction, terminal
    properties: dict = field(default_factory=dict)


@dataclass
class AntennaEdge:
    """
    Aresta no grafo da antena (segmento condutor).
    
    Attributes:
        id: Identificador único
        start_node: ID do nó inicial
        end_node: ID do nó final
        geometry: Geometria associada (Wire, etc.)
        material: Material do segmento
    """
    id: int
    start_node: int
    end_node: int
    geometry: GeometryPrimitive = None
    material: Material = None


class AntennaGraph:
    """
    Representa a topologia da antena como um grafo.
    
    Permite:
    - Adicionar/remover elementos
    - Verificar conectividade
    - Encontrar caminhos de corrente
    - Validar estrutura
    """
    
    def __init__(self, name: str = "Antenna"):
        self.name = name
        self.nodes: Dict[int, AntennaNode] = {}
        self.edges: Dict[int, AntennaEdge] = {}
        self.geometries: List[GeometryPrimitive] = []
        
        self._next_node_id = 0
        self._next_edge_id = 0
        
        # Grafo NetworkX para análise
        self._graph = nx.Graph()
        
        self.feed_point: Optional[Vector3D] = None
    
    def add_node(
        self, 
        position: Vector3D, 
        node_type: str = "junction",
        properties: dict = None
    ) -> int:
        """Adiciona um nó ao grafo"""
        node_id = self._next_node_id
        self._next_node_id += 1
        
        node = AntennaNode(
            id=node_id,
            position=position,
            node_type=node_type,
            properties=properties or {}
        )
        
        self.nodes[node_id] = node
        self._graph.add_node(node_id, pos=position.to_tuple(), type=node_type)
        
        return node_id
    
    def add_edge(
        self,
        start_node: int,
        end_node: int,
        geometry: GeometryPrimitive = None,
        material: Material = None
    ) -> int:
        """Adiciona uma aresta (segmento) ao grafo"""
        if start_node not in self.nodes or end_node not in self.nodes:
            raise ValueError("Nós não existem no grafo")
        
        edge_id = self._next_edge_id
        self._next_edge_id += 1
        
        # Cria geometria automática se não fornecida
        if geometry is None:
            start_pos = self.nodes[start_node].position
            end_pos = self.nodes[end_node].position
            geometry = Wire(start=start_pos, end=end_pos)
        
        geometry.material = material or MaterialLibrary.COPPER
        
        edge = AntennaEdge(
            id=edge_id,
            start_node=start_node,
            end_node=end_node,
            geometry=geometry,
            material=geometry.material
        )
        
        self.edges[edge_id] = edge
        self.geometries.append(geometry)
        
        # Calcula comprimento para peso no grafo
        length = (self.nodes[end_node].position - 
                  self.nodes[start_node].position).magnitude
        self._graph.add_edge(start_node, end_node, id=edge_id, weight=length)
        
        return edge_id
    
    def add_wire(
        self,
        start: Vector3D,
        end: Vector3D,
        radius: float = 0.001,
        material: Material = None,
        start_type: str = "terminal",
        end_type: str = "terminal"
    ) -> Tuple[int, int, int]:
        """
        Adiciona um fio criando nós e aresta automaticamente.
        
        Returns:
            Tupla (node_start_id, node_end_id, edge_id)
        """
        # Verifica se já existe nó próximo
        start_node = self._find_or_create_node(start, start_type)
        end_node = self._find_or_create_node(end, end_type)
        
        wire = Wire(start=start, end=end, radius=radius)
        edge_id = self.add_edge(start_node, end_node, wire, material)
        
        return start_node, end_node, edge_id
    
    def _find_or_create_node(
        self, 
        position: Vector3D, 
        node_type: str,
        tolerance: float = 1e-6
    ) -> int:
        """Encontra nó existente ou cria um novo"""
        for node_id, node in self.nodes.items():
            if (node.position - position).magnitude < tolerance:
                return node_id
        
        return self.add_node(position, node_type)
    
    def set_feed_point(self, node_id: int) -> None:
        """Define um nó como ponto de alimentação"""
        if node_id in self.nodes:
            self.nodes[node_id].node_type = "feed"
            self._graph.nodes[node_id]['type'] = "feed"
            self.feed_point = self.nodes[node_id].position
    
    def set_ground(self, node_id: int) -> None:
        """Define um nó como terra"""
        if node_id in self.nodes:
            self.nodes[node_id].node_type = "ground"
            self._graph.nodes[node_id]['type'] = "ground"
    
    def get_feed_points(self) -> List[int]:
        """Retorna lista de IDs dos pontos de alimentação"""
        return [n.id for n in self.nodes.values() if n.node_type == "feed"]
    
    def get_ground_nodes(self) -> List[int]:
        """Retorna lista de IDs dos nós de terra"""
        return [n.id for n in self.nodes.values() if n.node_type == "ground"]
    
    def is_connected(self) -> bool:
        """Verifica se o grafo é conexo"""
        return nx.is_connected(self._graph)
    
    def find_path(self, start: int, end: int) -> List[int]:
        """Encontra caminho entre dois nós"""
        try:
            return nx.shortest_path(self._graph, start, end)
        except nx.NetworkXNoPath:
            return []
    
    def get_total_length(self) -> float:
        """Retorna comprimento total de todos os fios"""
        total = 0
        for edge in self.edges.values():
            if isinstance(edge.geometry, Wire):
                total += edge.geometry.length
        return total
    
    def get_bounding_box(self) -> BoundingBox:
        """Retorna bounding box de toda a antena"""
        if not self.geometries:
            return BoundingBox(Vector3D(), Vector3D())
        
        boxes = [g.get_bounding_box() for g in self.geometries]
        return BoundingBox.union(boxes)
    
    def validate(self) -> List[str]:
        """
        Valida a estrutura da antena.
        
        Returns:
            Lista de problemas encontrados (vazia se válido)
        """
        issues = []
        
        # Verifica conectividade
        if not self.is_connected():
            issues.append("Antena não é conexa - existem partes desconectadas")
        
        # Verifica ponto de alimentação
        feeds = self.get_feed_points()
        if not feeds:
            issues.append("Nenhum ponto de alimentação definido")
        elif len(feeds) > 1:
            issues.append(f"Múltiplos pontos de alimentação ({len(feeds)})")
        
        # Verifica nós isolados
        isolated = list(nx.isolates(self._graph))
        if isolated:
            issues.append(f"Nós isolados encontrados: {isolated}")
        
        return issues
    
    def to_dict(self) -> dict:
        """Serializa o grafo para dicionário"""
        # Coleta todas as geometrias
        geometries = []
        
        # Geometrias (inclui geometrias explícitas e fios das arestas)
        for geom in self.geometries:
            geometries.append(geom.to_dict())
            
        return {
            'name': self.name,
            'bounding_box': self.get_bounding_box().to_dict(),
            'feed_point': self.feed_point.to_tuple() if self.feed_point else None,
            'geometries': geometries,
            'nodes': {
                str(k): {
                    'id': v.id,
                    'position': v.position.to_tuple(),
                    'type': v.node_type,
                    'properties': v.properties
                }
                for k, v in self.nodes.items()
            },
            'edges': {
                str(k): {
                    'id': v.id,
                    'start': v.start_node,
                    'end': v.end_node,
                    'geometry': v.geometry.to_dict() if v.geometry else None
                }
                for k, v in self.edges.items()
            }
        }
    
    def save(self, filepath: str) -> None:
        """Salva o grafo em arquivo JSON"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'AntennaGraph':
        """Carrega grafo de arquivo JSON"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        graph = cls(name=data.get('name', 'Antenna'))
        
        # Carrega nós
        for node_data in data['nodes'].values():
            graph.add_node(
                Vector3D(*node_data['position']),
                node_data['type'],
                node_data.get('properties', {})
            )
        
        # Carrega arestas
        for edge_data in data['edges'].values():
            geom_data = edge_data.get('geometry')
            if geom_data:
                geom_type = geom_data['type']
                if geom_type == 'wire':
                    geometry = Wire.from_dict(geom_data)
                elif geom_type == 'rectangle':
                    geometry = Rectangle.from_dict(geom_data)
                else:
                    geometry = None
            else:
                geometry = None
            
            graph.add_edge(
                edge_data['start'],
                edge_data['end'],
                geometry
            )
        
        return graph
