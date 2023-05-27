"""

flim - Bean's Filmic Transform

Input Color Space:   Linear BT.709 I-D65
Output Color Space:  sRGB 2.2

Repo:
https://github.com/bean-mhm/flim

"""


import numpy as np
import colour
import joblib

from utils import *


vt_name = 'flim'
vt_version = '0.3.0'


# Transform a 3D LUT
def apply_transform(table: np.ndarray, compress_lg2_min, compress_lg2_max, parallel):
    if len(table.shape) != 4:
        raise Exception('table must have 4 dimensions (3 for xyz, 1 for the color channels)')
    
    if table.shape[3] != 3:
        raise Exception('the fourth axis must have a size of 3 (RGB)')
    
    # Decompress: Map Range
    table = colour.algebra.linear_conversion(
        table,
        np.array([0.0, 1.0]),
        np.array([compress_lg2_min, compress_lg2_max])
    )
    
    # Decompress: Exponent
    colour.algebra.set_spow_enable(True)
    table = np.power(2.0, table)
    
    # Decompress: Black Point
    offset = (2.0**compress_lg2_min)
    table -= offset
    
    # Eliminate negative values
    table = np.maximum(table, 0.0)
    
    # Pre-Exposure
    pre_exposure = 1.5
    table *= (2**pre_exposure)
    
    # Apply element-wise transform (calls transform_rgb)
    if parallel:
        print('Starting parallel element-wise transform...')
        
        num_points = table.shape[0] * table.shape[1] * table.shape[2]
        stride_y = table.shape[0]
        stride_z = table.shape[0] * table.shape[1]
        
        results = joblib.Parallel(n_jobs=8)(
            joblib.delayed(run_parallel)(table, (i % stride_y, (i % stride_z) // stride_y, i // stride_z)) for i in range(num_points)
        )
    
        # Arrange the results
        print('Arranging the results...')
        for z in range(table.shape[2]):
            for y in range(table.shape[1]):
                for x in range(table.shape[0]):
                    index = x + (y * stride_y) + (z * stride_z)
                    table[x, y, z] = results[index]
    else:
        print('Starting serial element-wise transform...')
        for z in range(table.shape[2]):
            for y in range(table.shape[1]):
                print(f'at [0, {y}, {z}]')
                for x in range(table.shape[0]):
                    table[x, y, z] = transform_rgb(table[x, y, z])
    
    # OETF (Gamma 2.2)
    table = colour.algebra.spow(table, 1.0 / 2.2)
    
    return table


def run_parallel(table, indices):
    result = transform_rgb(table[indices])
    print(f'{indices} done')
    return result


# Transform a single RGB triplet
# This function should only be called by apply_transform.
def transform_rgb(inp):
    # Gamut Extension Matrix (Linear BT.709)
    extend_mat = flim_gamut_extension_mat(red_scale = 1.10, green_scale = 1.15, blue_scale = 1.05, red_rot = 2.0, green_rot = 4.0, blue_rot = 1.0)
    extend_mat_inv = np.linalg.inv(extend_mat)
    
    # Convert to extended gamut
    inp = np.matmul(extend_mat, inp)
    
    # Develop Negative
    inp = flim_rgb_develop(inp, exposure = 6.0, blue_sens = 1.0, green_sens = 1.0, red_sens = 1.0, max_density = 10.0)
    
    # Develop Print
    inp = flim_rgb_develop(inp, exposure = 6.0, blue_sens = 1.0, green_sens = 1.0, red_sens = 1.0, max_density = 16.0)
    
    # Convert from extended gamut
    inp = np.matmul(extend_mat_inv, inp)
    
    # Highlight Cap
    inp = inp / 0.796924
    
    # Black Point
    inp = rgb_uniform_offset(inp, black_point = 0.25, white_point = 0.0)
    
    # Clamp
    inp = np.clip(inp, 0, 1)
    
    # Midtone Saturation
    mono = rgb_avg(inp)
    mix = map_range_clamp(mono, 0.05, 0.5, 0.0, 1.0) if mono <= 0.5 else map_range_clamp(mono, 0.5, 0.95, 1.0, 0.0)
    inp = lerp(inp, blender_hue_sat(inp, 0.5, 1.02, 1.0), mix)
    
    # Clip and return
    return np.clip(inp, 0, 1)
