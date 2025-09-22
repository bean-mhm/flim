"""

flim - Filmic Color Transform

input color space: Linear BT.709 I-D65
output color space: sRGB

repo:
https://github.com/bean-mhm/flim

"""


import numpy as np
import colour
import joblib

from utils import *


# use parallel processing?
parallel = True

# print the current indices while processing? (slow)
print_indices = False


# transform a 3D LUT
def apply_transform(table: np.ndarray, preset: dict):
    if len(table.shape) != 4:
        raise Exception(
            'table must have 4 dimensions (3 for xyz, 1 for the color channels)'
        )

    if table.shape[3] != 3:
        raise Exception('the fourth axis must have a size of 3 (RGB)')

    # LUT decompression: map range
    table = colour.algebra.linear_conversion(
        table,
        np.array([0., 1.]),
        np.array([
            preset['lut_compress_log2_min'],
            preset['lut_compress_log2_max']
        ])
    )

    # LUT decompression: exponent
    colour.algebra.set_spow_enable(True)
    table = np.power(2., table)

    # LUT decompression: offset
    table -= 2.**preset['lut_compress_log2_min']

    # eliminate negative values
    table = np.maximum(table, 0.)

    # pre-exposure
    table *= 2**preset['pre_exposure']

    # gamut extension matrix
    extend_mat = gamut_extension_mat(
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

    # backlight in the extended gamut
    backlight_ext = np.matmul(extend_mat, preset['print_backlight'])

    # upper and lower limits in the print (in the extended gamut!)
    big = 10_000_000.
    white_cap = negative_and_print(
        np.array([big, big, big]),
        preset,
        backlight_ext
    )
    black_cap = negative_and_print(
        np.array([0, 0, 0]),
        preset,
        backlight_ext
    ) / white_cap

    # element-wise transform (calls transform_rgb)
    if parallel:
        print('starting parallel element-wise transform...')

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
                black_cap,
                backlight_ext
            )
            for i in range(num_points)
        )

        # arrange the results
        print('arranging the results...')
        for z in range(table.shape[2]):
            for y in range(table.shape[1]):
                for x in range(table.shape[0]):
                    index = x + (y * stride_y) + (z * stride_z)
                    table[x, y, z] = results[index]
    else:
        print('starting serial element-wise transform...')
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
                        black_cap,
                        backlight_ext
                    )

    # OETF: Linear BT.709 I-D65 -> sRGB
    table = colour.models.oetf_sRGB(table)

    return table


# calls transform_rgb
def run_parallel(
        table,
        indices,
        preset: dict,
        extend_mat,
        extend_mat_inv,
        white_cap,
        black_cap,
        backlight_ext
):
    result = transform_rgb(
        table[indices],
        preset,
        extend_mat,
        extend_mat_inv,
        white_cap,
        black_cap,
        backlight_ext
    )

    if print_indices:
        print(f'{indices} done')

    return result


def negative_and_print(inp, preset: dict, backlight_ext):
    log2_min = preset['sigmoid_log2_min']
    log2_max = preset['sigmoid_log2_max']
    sigmoid_points = np.array([
        preset['sigmoid_toe_x'],
        preset['sigmoid_toe_y'],
        preset['sigmoid_shoulder_x'],
        preset['sigmoid_shoulder_y']
    ])

    # develop negative
    inp = rgb_develop(
        inp,
        preset['negative_film_exposure'],
        log2_min,
        log2_max,
        sigmoid_points,
        preset['negative_film_density']
    )

    # backlight
    inp = inp * backlight_ext

    # develop print
    inp = rgb_develop(
        inp,
        preset['print_film_exposure'],
        log2_min,
        log2_max,
        sigmoid_points,
        preset['print_film_density']
    )

    return inp


# transform a single RGB triplet (you should never directly call this function)
def transform_rgb(
    inp,
    preset: dict,
    extend_mat,
    extend_mat_inv,
    white_cap,
    black_cap,
    backlight_ext
):
    luminance_weights = preset['luminance_weights']
    luminance_weights /= np.dot(luminance_weights, np.array([1., 1., 1.]))

    # pre-formation filter
    inp *= lerp(
        np.array([1.0, 1.0, 1.0]),
        preset['pre_formation_filter'],
        preset['pre_formation_filter_strength']
    )

    # convert to the extended gamut
    inp = np.matmul(extend_mat, inp)

    # develop negative and print
    inp = negative_and_print(inp, preset, backlight_ext)

    # white cap
    inp /= white_cap

    # black cap
    if preset['black_point'] in ['Auto', 'auto', '', None]:
        inp = rgb_uniform_offset(
            inp,
            np.dot(black_cap, luminance_weights),
            0.,
            luminance_weights
        )
    else:
        inp = rgb_uniform_offset(
            inp,
            preset['black_point'] / 1000.,
            0.,
            luminance_weights
        )

    # convert from the extended gamut and clip out-of-gamut triplets
    inp = np.matmul(extend_mat_inv, inp)
    inp = np.maximum(inp, 0.)

    # post-formation filter
    inp = lerp(inp, inp * preset['post_formation_filter'],
               preset['post_formation_filter_strength'])

    # clip
    inp = np.clip(inp, 0., 1.)

    # midtone saturation
    mono = np.dot(inp, luminance_weights)
    midtone_fac = max(1. - (abs(mono - .5) / .45), 0.)
    inp = lerp(
        inp,
        rgb_adjust_hsv(inp, .5, preset['midtone_saturation'], 1.),
        midtone_fac
    )

    # clip and return
    return np.clip(inp, 0., 1.)
