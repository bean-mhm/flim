"""

helper functions for flim

repo:
https://github.com/bean-mhm/flim

"""


import numpy as np
import colour

from super_sigmoid import super_sigmoid


# constants
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
    if (b == 0.):
        return 0.
    return a / b


def safe_pow(a, b):
    return np.sign(a) * (np.abs(a)**b)


def pivot_pow(a, b, pivot):
    return pivot * ((a / pivot)**b)


def smootherstep(x, edge0, edge1):
    x = np.clip(safe_divide((x - edge0), (edge1 - edge0)), 0., 1.)
    return x * x * x * (x * (x * 6. - 15.) + 10.)


def remap(inp, inp_start, inp_end, out_start, out_end):
    return out_start + (
        ((out_end - out_start) / (inp_end - inp_start))
        * (inp - inp_start)
    )


def remap_clamp(inp, inp_start, inp_end, out_start, out_end):
    v = out_start + (
        ((out_end - out_start) / (inp_end - inp_start))
        * (inp - inp_start)
    )

    return np.clip(v, out_start, out_end)


def remap01(inp, inp_start, inp_end):
    return np.clip((inp - inp_start) / (inp_end - inp_start), 0., 1.)


def remap_smootherstep(inp, inp_start, inp_end, out_start, out_end):
    if (inp_start == inp_end):
        return 0.

    fac = \
        (1. - smootherstep(inp, inp_end, inp_start))  \
        if inp_start > inp_end  \
        else smootherstep(inp, inp_start, inp_end)

    return out_start + fac * (out_end - out_start)


def rgb_to_hsv(inp):
    h = 0.
    s = 0.
    v = 0.

    cmax = max(inp[0], max(inp[1], inp[2]))
    cmin = min(inp[0], min(inp[1], inp[2]))
    cdelta = cmax - cmin

    v = cmax

    if cmax != 0.:
        s = cdelta / cmax

    if s != 0.:
        c = (-inp + cmax) / cdelta

        if inp[0] == cmax:
            h = c[2] - c[1]
        elif inp[1] == cmax:
            h = 2. + c[0] - c[2]
        else:
            h = 4. + c[1] - c[0]

        h /= 6.

        if h < 0.:
            h += 1.

    return np.array([h, s, v])


def hsv_to_rgb(inp):
    h = inp[0]
    s = inp[1]
    v = inp[2]

    if s == 0.:
        return np.array([v, v, v])
    else:
        if h == 1.:
            h = 0.

        h *= 6.
        i = np.floor(h)
        f = h - i
        p = v * (1. - s)
        q = v * (1. - (s * f))
        t = v * (1. - (s * (1. - f)))

        if i == 0.:
            return np.array([v, t, p])
        elif i == 1.:
            return np.array([q, v, p])
        elif i == 2.:
            return np.array([p, v, t])
        elif i == 3.:
            return np.array([p, q, v])
        elif i == 4.:
            return np.array([t, p, v])
        else:
            return np.array([v, p, q])


def rgb_adjust_hsv(inp, hue, sat, value):
    hsv = rgb_to_hsv(inp)

    hsv[0] = np.modf(hsv[0] + hue + .5)[0]
    hsv[1] = np.clip(hsv[1] * sat, 0, 1)
    hsv[2] = hsv[2] * value

    return hsv_to_rgb(hsv)


def rgb_sum(inp):
    return inp[0] + inp[1] + inp[2]


def rgb_max(inp):
    return max(max(inp[0], inp[1]), inp[2])


def rgb_min(inp):
    return min(min(inp[0], inp[1]), inp[2])


def rgb_uniform_offset(inp, black_point, white_point, luminance_weights):
    mono = np.dot(inp, luminance_weights)

    # avoid division by zero
    if abs(mono) < .0001:
        return inp

    return inp * remap01(
        mono,
        min(black_point, .999),
        1. - min(white_point, .999)
    ) / mono


def dye_mix_factor(
    mono,
    log2_min,
    log2_max,
    sigmoid_points,
    max_density
):

    # log2 and map range
    offset = 2.**log2_min
    fac = remap01(np.log2(mono + offset), log2_min, log2_max)

    # calculate amount of exposure from 0 to 1
    fac = super_sigmoid(
        fac,
        toe_x=sigmoid_points[0],
        toe_y=sigmoid_points[1],
        shoulder_x=sigmoid_points[2],
        shoulder_y=sigmoid_points[3]
    )

    # calculate dye density
    fac *= max_density

    # mix factor
    fac = 2. ** (-fac)

    # clip and return
    return np.clip(fac, 0., 1.)


def rgb_color_layer(
    inp,
    sensitivity_tone,
    dye_tone,
    log2_min,
    log2_max,
    sigmoid_points,
    max_density
):
    # normalize
    sensitivity_tone_norm = sensitivity_tone / rgb_sum(sensitivity_tone)
    dye_tone_norm = dye_tone / rgb_max(dye_tone)

    # dye mix factor
    mono = np.dot(inp, sensitivity_tone_norm)
    mix = dye_mix_factor(
        mono,
        log2_min,
        log2_max,
        sigmoid_points,
        max_density
    )

    # dye mixing
    return lerp(dye_tone_norm, white, mix)


def rgb_develop(
    inp,
    exposure,
    log2_min,
    log2_max,
    sigmoid_points,
    max_density
):
    # exposure
    inp *= 2.**exposure

    # blue-sensitive layer
    out = rgb_color_layer(
        inp,
        blue,
        yellow,
        log2_min,
        log2_max,
        sigmoid_points,
        max_density
    )

    # green-sensitive layer
    out *= rgb_color_layer(
        inp,
        green,
        magenta,
        log2_min,
        log2_max,
        sigmoid_points,
        max_density
    )

    # red-sensitive layer
    out *= rgb_color_layer(
        inp,
        red,
        cyan,
        log2_min,
        log2_max,
        sigmoid_points,
        max_density
    )

    return out


def gamut_extension_mat_row(primary_hue, scale, rotate, mul):
    out = hsv_to_rgb(np.array([
        wrap(primary_hue + (rotate / 360.), 0., 1.),
        1. / scale,
        1.
    ]))

    out /= rgb_sum(out)
    out *= mul
    return out


def gamut_extension_mat(
    red_scale,
    green_scale,
    blue_scale,
    red_rot,
    green_rot,
    blue_rot,
    red_mul,
    green_mul,
    blue_mul
):
    return np.array([
        gamut_extension_mat_row(0.0, red_scale, red_rot, red_mul),
        gamut_extension_mat_row(
            1.0 / 3.0, green_scale, green_rot, green_mul),
        gamut_extension_mat_row(2.0 / 3.0, blue_scale, blue_rot, blue_mul)
    ])
