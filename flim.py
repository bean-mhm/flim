"""

flim - Filmic Color Transform

Input Color Space:   Linear BT.709 I-D65
Output Color Space:  sRGB 2.2

Repo:
https://github.com/bean-mhm/flim

"""


import numpy as np
import colour
import joblib

from utils import *


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
    
    # Upper and lower limits in the print
    big = 10_000_000.0
    white_cap = negative_and_print(np.array([big, big, big]), preset)
    black_cap = negative_and_print(np.array([0, 0, 0]), preset)
    black_cap /= white_cap
    
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
                extend_mat_inv,
                white_cap,
                black_cap)
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
                    table[x, y, z] = transform_rgb(
                        table[x, y, z],
                        preset,
                        extend_mat,
                        extend_mat_inv,
                        white_cap,
                        black_cap
                    )
    
    # OETF (Gamma 2.2)
    table = colour.algebra.spow(table, 1.0 / 2.2)
    
    return table


# Calls transform_rgb
def run_parallel(table, indices, preset: dict, extend_mat, extend_mat_inv, white_cap, black_cap):
    result = transform_rgb(table[indices], preset, extend_mat, extend_mat_inv, white_cap, black_cap)
    
    if print_indices:
        print(f'{indices} done')
    
    return result


def negative_and_print(inp, preset: dict):
    log2_min = preset['sigmoid_log2_min']
    log2_max = preset['sigmoid_log2_max']
    sigmoid_points = np.array([
        preset['sigmoid_toe_x'],
        preset['sigmoid_toe_y'],
        preset['sigmoid_shoulder_x'],
        preset['sigmoid_shoulder_y']
    ])
    
    # Develop Negative
    inp = flim_rgb_develop(
        inp,
        preset['negative_film_exposure'],
        log2_min,
        log2_max,
        sigmoid_points,
        preset['negative_film_density']
    )
    
    # Backlight
    inp = inp * preset['print_backlight']
    
    # Develop Print
    inp = flim_rgb_develop(
        inp,
        preset['print_film_exposure'],
        log2_min,
        log2_max,
        sigmoid_points,
        preset['print_film_density']
    )

    return inp


# Transform a single RGB triplet
# You should never directly call this function.
def transform_rgb(inp, preset: dict, extend_mat, extend_mat_inv, white_cap, black_cap):
    # Pre-Formation Filter
    inp = lerp(inp, inp * preset['pre_formation_filter'], preset['pre_formation_filter_strength'])
    
    # Convert to extended gamut
    inp = np.matmul(extend_mat, inp)
    
    # Negative & Print
    inp = negative_and_print(inp, preset)
    
    # Convert from extended gamut
    inp = np.matmul(extend_mat_inv, inp)
    
    # Eliminate negative values
    inp = np.maximum(inp, 0.0)
    
    # White cap
    inp /= white_cap
    
    # Black cap
    if preset['black_point'].lower() == 'auto' or preset['black_point'] in ['', None]:
        inp = rgb_uniform_offset(inp, rgb_avg(black_cap) * 1000.0, 0.0)
    else:
        inp = rgb_uniform_offset(inp, preset['black_point'], 0.0)
    
    # Post-Formation Filter
    inp = lerp(inp, inp * preset['post_formation_filter'], preset['post_formation_filter_strength'])
    
    # Clip
    inp = np.clip(inp, 0, 1)
    
    # Midtone Saturation
    mono = rgb_avg(inp)
    mix = map_range_clamp(mono, 0.05, 0.5, 0.0, 1.0) if mono <= 0.5 else map_range_clamp(mono, 0.5, 0.95, 1.0, 0.0)
    inp = lerp(inp, blender_hue_sat(inp, 0.5, preset['midtone_saturation'], 1.0), mix)
    
    # Clip and return
    return np.clip(inp, 0, 1)
