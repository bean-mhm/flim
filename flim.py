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
vt_version = '0.6.0'

# Use parallel processing?
parallel = True

# Print the current indices while processing? (slow)
print_indices = False


# Transform a 3D LUT
def apply_transform(table: np.ndarray, preset: dict):
    if len(table.shape) != 4:
        raise Exception('table must have 4 dimensions (3 for xyz, 1 for the color channels)')
    
    if table.shape[3] != 3:
        raise Exception('the fourth axis must have a size of 3 (RGB)')
    
    # LUT Decompression: Map Range
    table = colour.algebra.linear_conversion(
        table,
        np.array([0.0, 1.0]),
        np.array([preset['lut_compress_log2_min'], preset['lut_compress_log2_max']])
    )
    
    # LUT Decompression: Exponent
    colour.algebra.set_spow_enable(True)
    table = np.power(2.0, table)
    
    # LUT Decompression: Black Offset
    offset = (2.0**preset['lut_compress_log2_min'])
    table -= offset
    
    # Eliminate negative values (useless)
    table = np.maximum(table, 0.0)
    
    # Pre-Exposure
    table *= (2**preset['pre_exposure'])
    
    # Gamut Extension Matrix (Linear BT.709)
    extend_mat = flim_gamut_extension_mat(
        preset['extended_gamut_red_scale'],
        preset['extended_gamut_green_scale'],
        preset['extended_gamut_blue_scale'],
        preset['extended_gamut_red_rot'],
        preset['extended_gamut_green_rot'],
        preset['extended_gamut_blue_rot'],
        preset['extended_gamut_red_mul'],
        preset['extended_gamut_green_mul'],
        preset['extended_gamut_blue_mul']
    )
    extend_mat_inv = np.linalg.inv(extend_mat)
    
    # Apply element-wise transform (calls transform_rgb)
    if parallel:
        print('Starting parallel element-wise transform...')
        
        num_points = table.shape[0] * table.shape[1] * table.shape[2]
        stride_y = table.shape[0]
        stride_z = table.shape[0] * table.shape[1]
        
        results = joblib.Parallel(n_jobs=8)(
            joblib.delayed(run_parallel)(
                table,
                (i % stride_y, (i % stride_z) // stride_y, i // stride_z),
                preset,
                extend_mat,
                extend_mat_inv)
            for i in range(num_points)
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
                if print_indices:
                    print(f'at [0, {y}, {z}]')
                for x in range(table.shape[0]):
                    table[x, y, z] = transform_rgb(table[x, y, z], preset, extend_mat, extend_mat_inv)
    
    # OETF (Gamma 2.2)
    table = colour.algebra.spow(table, 1.0 / 2.2)
    
    return table


# Calls transform_rgb
def run_parallel(table, indices, preset: dict, extend_mat, extend_mat_inv):
    result = transform_rgb(table[indices], preset, extend_mat, extend_mat_inv)
    
    if print_indices:
        print(f'{indices} done')
    
    return result


# Transform a single RGB triplet
# You should never directly call this function.
def transform_rgb(inp, preset: dict, extend_mat, extend_mat_inv):
    # Convert to extended gamut
    inp = np.matmul(extend_mat, inp)
    
    # Develop Negative
    inp = flim_rgb_develop(inp, exposure=preset['negative_film_exposure'], blue_sens=1.0, green_sens=1.0, red_sens=1.0, max_density=preset['negative_film_density'])
    
    # Backlight
    inp = inp * preset['print_backlight']
    
    # Develop Print
    inp = flim_rgb_develop(inp, exposure=preset['print_film_exposure'], blue_sens=1.0, green_sens=1.0, red_sens=1.0, max_density=preset['print_film_density'])
    
    # Convert from extended gamut
    inp = np.matmul(extend_mat_inv, inp)
    
    # Eliminate negative values
    inp = np.maximum(inp, 0.0)
    
    # Highlight Cap
    inp = inp / preset['highlight_cap']
    
    # Black Point
    inp = rgb_uniform_offset(inp, preset['black_point'], preset['white_point'])
    
    # Clamp
    inp = np.clip(inp, 0, 1)
    
    # Midtone Saturation
    mono = rgb_avg(inp)
    mix = map_range_clamp(mono, 0.05, 0.5, 0.0, 1.0) if mono <= 0.5 else map_range_clamp(mono, 0.5, 0.95, 1.0, 0.0)
    inp = lerp(inp, blender_hue_sat(inp, 0.5, preset['midtone_saturation'], 1.0), mix)
    
    # Clip and return
    return np.clip(inp, 0, 1)
