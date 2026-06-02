import necpp
import numpy as np

from ..core.geometry.primitives import Wire
from ..core.geometry.topology import AntennaGraph


class NECGeometryConverter:
    def __init__(self, frequency_hz: float):
        self.frequency = frequency_hz
        self.wavelength = 299792458.0 / frequency_hz
        # NEC recommendation: segments should be less than lambda/10
        # Using lambda/20 for better accuracy
        self.segment_length = self.wavelength / 20.0

    def apply_to_context(self, nec, graph: AntennaGraph):
        """
        Converts the AntennaGraph geometry into NEC wire commands.
        Returns a mapping of edge_id -> tag.
        """
        tag_map = {}  # edge_id -> tag

        # Add wires
        for edge_id, edge in graph.edges.items():
            # Check if geometry is a Wire or derived type
            # We assume for now most edges are Wires in the graph
            # If edge.geometry is None, skip or assume wire if it's a simple connection

            radius = 0.001  # Default 1mm
            if edge.geometry and isinstance(edge.geometry, Wire):
                radius = edge.geometry.radius
            elif hasattr(edge, "radius"):  # Fallback if radius is direct property
                radius = edge.radius

            start_node = graph.nodes[edge.start_node]
            end_node = graph.nodes[edge.end_node]

            p1 = start_node.position
            p2 = end_node.position

            length = np.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2 + (p2.z - p1.z) ** 2)

            if length < 1e-9:
                continue  # Skip zero length edges

            # Number of segments
            n_segments = max(1, int(np.ceil(length / self.segment_length)))

            # Tag = edge_id + 1 (NEC tags must be > 0)
            tag = edge_id + 1
            tag_map[edge_id] = tag

            necpp.nec_wire(
                nec,
                tag,
                n_segments,
                p1.x,
                p1.y,
                p1.z,
                p2.x,
                p2.y,
                p2.z,
                radius,
                1.0,
                1.0,
            )

        necpp.nec_geometry_complete(nec, 1)  # 1 = check connections

        return tag_map

    def find_excitation_segment(self, graph: AntennaGraph, tag_map: dict):
        """
        Finds the (tag, segment) tuple corresponding to the antenna's feed point.
        """
        if not graph.feed_point:
            return None

        # Strategy: Find the node closest to feed_point
        min_dist = float("inf")
        closest_node_id = None

        fp_x = graph.feed_point.x
        fp_y = graph.feed_point.y
        fp_z = graph.feed_point.z

        for node_id, node in graph.nodes.items():
            dist = np.sqrt(
                (node.position.x - fp_x) ** 2
                + (node.position.y - fp_y) ** 2
                + (node.position.z - fp_z) ** 2
            )
            if dist < min_dist:
                min_dist = dist
                closest_node_id = node_id

        if closest_node_id is None:
            return None

        # Find connected edge
        # We prioritize edges where this node is the start node for simplicity (segment 1)
        for edge_id, edge in graph.edges.items():
            tag = tag_map.get(edge_id)
            if not tag:
                continue

            if edge.start_node == closest_node_id:
                return (tag, 1)  # First segment
            elif edge.end_node == closest_node_id:
                # Need number of segments to know the last one
                start_node = graph.nodes[edge.start_node]
                end_node = graph.nodes[edge.end_node]
                p1 = start_node.position
                p2 = end_node.position
                length = np.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2 + (p2.z - p1.z) ** 2)
                n_segments = max(1, int(np.ceil(length / self.segment_length)))
                return (tag, n_segments)

        return None
