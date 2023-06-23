"""

Helper functions for flim

Repo:
https://github.com/bean-mhm/flim

"""


import numpy as np
import colour

from super_sigmoid import super_sigmoid


# Constants

white = np.array([1.0, 1.0, 1.0])
red = np.array([1.0, 0.0, 0.0])
yellow = np.array([1.0, 1.0, 0.0])
green = np.array([0.0, 1.0, 0.0])
cyan = np.array([0.0, 1.0, 1.0])
blue = np.array([0.0, 0.0, 1.0])
magenta = np.array([1.0, 0.0, 1.0])


def wrap(x, a, b):
    return a + np.mod(x - a, b - a)


def lerp(a, b, t):
    return a + t * (b - a)


def safe_divide(a, b):
    if (b == 0.0):
        return 0.0
    return a / b


def safe_pow(a, b):
    return np.sign(a) * (np.abs(a)**b)


def pivot_pow(a, b, pivot):
    return pivot * ((a / pivot)**b)


def smootherstep(x, edge0, edge1):
    x = np.clip(safe_divide((x - edge0), (edge1 - edge0)), 0.0, 1.0)
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


def map_range(inp, inp_start, inp_end, out_start, out_end):
    return out_start + ((out_end - out_start) / (inp_end - inp_start)) * (inp - inp_start)


def map_range_clamp(inp, inp_start, inp_end, out_start, out_end):
    v = out_start + ((out_end - out_start) / (inp_end - inp_start)) * (inp - inp_start)
    
    if v < out_start:
        return out_start
    
    if v > out_end:
        return out_end
    
    return v


def map_range_smootherstep(inp, inp_start, inp_end, out_start, out_end):
    if (inp_start == inp_end):
        return 0.0
    
    fac = \
        (1.0 - smootherstep(inp, inp_end, inp_start)) \
        if inp_start > inp_end \
        else smootherstep(inp, inp_start, inp_end)
    
    return out_start + fac * (out_end - out_start)


def blender_rgb_to_hsv(inp):
    h = 0.0
    s = 0.0
    v = 0.0

    cmax = max(inp[0], max(inp[1], inp[2]))
    cmin = min(inp[0], min(inp[1], inp[2]))
    cdelta = cmax - cmin

    v = cmax
    
    if cmax != 0.0:
        s = cdelta / cmax
    
    if s != 0.0:
        c = (-inp + cmax) / cdelta

        if inp[0] == cmax:
            h = c[2] - c[1]
        elif inp[1] == cmax:
            h = 2.0 + c[0] - c[2]
        else:
            h = 4.0 + c[1] - c[0]

        h /= 6.0

        if h < 0.0:
            h += 1.0

    return np.array([h, s, v])


def blender_hsv_to_rgb(inp):
    h = inp[0]
    s = inp[1]
    v = inp[2]

    if s == 0.0:
        return np.array([v, v, v])
    else:
        if h == 1.0:
            h = 0.0

        h *= 6.0
        i = np.floor(h)
        f = h - i
        p = v * (1.0 - s)
        q = v * (1.0 - (s * f))
        t = v * (1.0 - (s * (1.0 - f)))

        if i == 0.0:
            return np.array([v, t, p])
        elif i == 1.0:
            return np.array([q, v, p])
        elif i == 2.0:
            return np.array([p, v, t])
        elif i == 3.0:
            return np.array([p, q, v])
        elif i == 4.0:
            return np.array([t, p, v])
        else:
            return np.array([v, p, q])


def blender_hue_sat(inp, hue, sat, value):
    hsv = blender_rgb_to_hsv(inp)
    
    hsv[0] = np.modf(hsv[0] + hue + 0.5)[0]
    hsv[1] = np.clip(hsv[1] * sat, 0, 1)
    hsv[2] = hsv[2] * value
    
    return blender_hsv_to_rgb(hsv)


def BT_709_to_XYZ(inp):
    mat = np.array([
        [ 0.4123908 ,  0.35758434,  0.18048079],
        [ 0.21263901,  0.71516868,  0.07219232],
        [ 0.01933082,  0.11919478,  0.95053215]
    ])
    return np.matmul(mat, inp)


def XYZ_to_BT_709(inp):
    mat = np.array([
        [ 3.24096994, -1.53738318, -0.49861076],
        [-0.96924364,  1.8759675 ,  0.04155506],
        [ 0.05563008, -0.20397696,  1.05697151]
    ])
    return np.matmul(mat, inp)


luminance_BT_709_I_D65 = np.array([0.299, 0.587, 0.114])
def rgb_lum(inp):
    return np.dot(inp, luminance_BT_709_I_D65)


def rgb_avg(inp):
    return (inp[0] + inp[1] + inp[2]) / 3.0


def rgb_sum(inp):
    return inp[0] + inp[1] + inp[2]


def rgb_max(inp):
    return max(max(inp[0], inp[1]), inp[2])


def rgb_min(inp):
    return min(min(inp[0], inp[1]), inp[2])


def rgb_mag(inp):
    return np.linalg.norm(inp)


def rgb_mag_over_sqrt3(inp):
    return np.linalg.norm(inp) / 1.7320508075688772935274463415059


def rgb_hue(inp):
    x1 = (inp[1] - inp[2]) * np.sqrt(3)
    x2 = inp[0]*2 - inp[1] - inp[2]
    
    hue = np.rad2deg(np.arctan2(x1, x2))
    
    if hue < 0.0:
        hue += 360.0
    
    if hue > 360.0:
        hue -= 360.0
    
    return hue


def rgb_sat(inp):
    inp_norm = inp / rgb_max(inp)
    return np.clip(rgb_max(inp_norm) - rgb_min(inp_norm), 0, 1)


def rgb_monotone(inp, col, amount):
    inp_mag = rgb_mag(inp)
    
    inp_norm = inp / inp_mag
    col_norm = col / rgb_mag(col)
    
    dot = np.dot(inp_norm, col_norm)
    
    out = col_norm * (inp_mag * dot)
    
    return inp + amount * (out - inp)


def rgb_uniform_offset(inp, black_point, white_point):
    mono = rgb_avg(inp)
    return inp * map_range_clamp(mono, black_point / 1000, 1 - (white_point / 1000), 0, 1) / mono


def enhance_curve(inp, toe, shoulder, transition):
    a = inp**toe
    b = 1.0 - (1.0 - inp)**shoulder
    mix = inp**transition
    
    return lerp(a, b, mix)


def enhance_curve_reverse_mix(inp, toe, shoulder, transition):
    a = inp**toe
    b = 1.0 - (1.0 - inp)**shoulder
    mix = 1.0 - (1.0 - inp)**transition
    
    return lerp(a, b, mix)


def flim_sigmoid_old(inp):
    return 1.0 - enhance_curve(1.0 - inp, toe=4.0, shoulder=2.0, transition=2.0)


def flim_dye_mix_factor(
    mono,
    log2_min,
    log2_max,
    sigmoid_points,
    max_density):
    
    # log2 and map range
    offset = 2.0**log2_min
    fac = map_range_clamp(np.log2(mono + offset), log2_min, log2_max, 0.0, 1.0)
    
    # Calculate amount of exposure from 0 to 1
    fac = super_sigmoid(
        fac,
        toe_x=sigmoid_points[0],
        toe_y=sigmoid_points[1],
        shoulder_x=sigmoid_points[2],
        shoulder_y=sigmoid_points[3]
    )
    
    # Calculate dye density
    fac *= max_density
    
    # Mix factor
    fac = 2.0 ** (-fac)
    
    # Clip and return
    return np.clip(fac, 0, 1)


def flim_rgb_color_layer(
    inp,
    sensitivity_tone,
    dye_tone,
    log2_min,
    log2_max,
    sigmoid_points,
    max_density):
    
    # Normalize
    sensitivity_tone_norm = sensitivity_tone / rgb_sum(sensitivity_tone)
    dye_tone_norm = dye_tone / rgb_max(dye_tone)
    
    # Dye mix factor
    mono = np.dot(inp, sensitivity_tone_norm)
    mix = flim_dye_mix_factor(mono, log2_min, log2_max, sigmoid_points, max_density)
    
    # Dye mixing
    out = lerp(dye_tone_norm, white, mix)
    
    return out


def flim_rgb_develop(
    inp,
    exposure,
    log2_min,
    log2_max,
    sigmoid_points,
    max_density):
    
    # Exposure
    inp = inp * 2**exposure
    
    # Blue-sensitive layer
    out = flim_rgb_color_layer(inp, blue, yellow, log2_min, log2_max, sigmoid_points, max_density)
    
    # Green-sensitive layer
    out *= flim_rgb_color_layer(inp, green, magenta, log2_min, log2_max, sigmoid_points, max_density)
    
    # Red-sensitive layer
    out *= flim_rgb_color_layer(inp, red, cyan, log2_min, log2_max, sigmoid_points, max_density)
    
    return out


def flim_gamut_extension_mat_row(primary_hue, scale, rotate, mul):
    out = blender_hsv_to_rgb(np.array([
        wrap(primary_hue + (rotate / 360.0), 0.0, 1.0),
        1.0 / scale,
        1.0]))
    
    out /= rgb_sum(out)
    out *= mul
    return out


def flim_gamut_extension_mat(red_scale, green_scale, blue_scale, red_rot, green_rot, blue_rot, red_mul, green_mul, blue_mul):
    return np.array([
        flim_gamut_extension_mat_row(0.0, red_scale, red_rot, red_mul),
        flim_gamut_extension_mat_row(1.0 / 3.0, green_scale, green_rot, green_mul),
        flim_gamut_extension_mat_row(2.0 / 3.0, blue_scale, blue_rot, blue_mul)
    ])
