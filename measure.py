import open3d as o3d
import numpy as np
import copy
import os

def label_planes(planes):
    horizontals = [(pl, pc) for pl, pc in planes if abs(pl[1]) > 0.8]
    horizontals = sorted(horizontals, key=lambda x: x[0][3])
    floor, ceiling = horizontals[0], horizontals[-1]
    walls = [(pl, pc) for pl, pc in planes if abs(pl[1]) < 0.5]
    return floor, ceiling, walls

def plane_distance(plane1, plane2):
    n = np.array(plane1[0][:3])
    return abs(plane1[0][3] - plane2[0][3]) / np.linalg.norm(n)

def measure_extent(pc):
    obb = pc.get_oriented_bounding_box()
    extent = obb.extent
    return float(np.max(extent)), float(np.min(extent))

def colorize_planes_and_export(floor, ceiling, walls, filename='colored_planes.ply'):
    base_colors = [
        [0.9, 0.7, 0.1],
        [0.8, 0.8, 0.8],
        [0.9, 0.1, 0.1],
        [0.1, 0.9, 0.1],
        [0.1, 0.1, 0.9],
        [0.8, 0.3, 0.6],
        [0.6, 0.5, 0.2]
    ]
    vis_parts = []
    ceiling_pc = copy.deepcopy(ceiling[1])
    ceiling_pc.paint_uniform_color(base_colors[0])
    vis_parts.append(ceiling_pc)
    floor_pc = copy.deepcopy(floor[1])
    floor_pc.paint_uniform_color(base_colors[1])
    vis_parts.append(floor_pc)
    wall_measurements = []
    for idx, (pl, pc) in enumerate(walls):
        wall_pc = copy.deepcopy(pc)
        wall_pc.paint_uniform_color(base_colors[2 + (idx % (len(base_colors)-2))])
        vis_parts.append(wall_pc)
        l, w = measure_extent(pc)
        wall_measurements.append({'name': f'Wall_{idx+1}', 'length': l, 'width': w})
    o3d.io.write_point_cloud(filename, sum(vis_parts[1:], vis_parts[0]))
    return wall_measurements

def tag_and_measure(obj_path, output_ply_path):
    mesh = o3d.io.read_triangle_mesh(obj_path)
    if mesh.is_empty():
        raise RuntimeError("Loaded mesh is empty or invalid.")
    mesh.compute_vertex_normals()
    pc = mesh.sample_points_uniformly(200000)
    planes, rest = [], pc
    while True:
        pl, inl = rest.segment_plane(distance_threshold=0.01, ransac_n=3, num_iterations=1000)
        if len(inl) < 5000: break
        pc_in = rest.select_by_index(inl)
        planes.append((pl, pc_in))
        rest = rest.select_by_index(inl, invert=True)
    floor, ceiling, walls = label_planes(planes)
    height = plane_distance(floor, ceiling)
    
    fl_l, fl_w = measure_extent(floor[1])
    ce_l, ce_w = measure_extent(ceiling[1])
    
    wall_measurements = colorize_planes_and_export(floor, ceiling, walls, filename=output_ply_path)
    
    measurements = {
        "ceiling": {"length": ce_l, "width": ce_w},
        "floor": {"length": fl_l, "width": fl_w},
        "walls": wall_measurements,
        "height": height,
        "ply_file": output_ply_path
    }
    return measurements

