"""

3D LUT Generator for flim

Repo:
https://github.com/bean-mhm/flim

"""


import numpy as np
import colour
import os
import time

from flim import apply_transform, vt_name, vt_version


# Presets

preset_default = {
    'name': 'default',
    'info_url': None,
    
    'lut_compress_log2_min': -11,
    'lut_compress_log2_max': +12,
    'lut_quantize': 80,
    
    'pre_exposure': 0.95,
    
    'extended_gamut_red_scale': 1.05,
    'extended_gamut_green_scale': 1.12,
    'extended_gamut_blue_scale': 1.045,
    'extended_gamut_red_rot': 0.5,
    'extended_gamut_green_rot': 2.0,
    'extended_gamut_blue_rot': 0.0,
    'extended_gamut_red_mul': 1.0,
    'extended_gamut_green_mul': 1.0,
    'extended_gamut_blue_mul': 1.0,
    
    'negative_film_exposure': 5.3,
    'negative_film_density': 10.0,
    
    'print_backlight': np.array([1.0, 1.0, 1.0]),
    'print_film_exposure': 5.3,
    'print_film_density': 13.3,
    
    'highlight_cap': np.array([0.91, 0.91, 0.91]),
    'black_point': 1.47,
    'white_point': 0.0,
    'midtone_saturation': 1.02
}

preset_gold = {
    'name': 'gold',
    'info_url': None,
    
    'lut_compress_log2_min': -10,
    'lut_compress_log2_max': +10,
    'lut_quantize': 80,
    
    'pre_exposure': 3.3,
    
    'extended_gamut_red_scale': 1.05,
    'extended_gamut_green_scale': 1.12,
    'extended_gamut_blue_scale': 1.045,
    'extended_gamut_red_rot': 0.5,
    'extended_gamut_green_rot': 1.0,
    'extended_gamut_blue_rot': 0.0,
    'extended_gamut_red_mul': 1.0,
    'extended_gamut_green_mul': 1.0,
    'extended_gamut_blue_mul': 1.2,
    
    'negative_film_exposure': 2.3,
    'negative_film_density': 8.2,
    
    'print_backlight': np.array([1.1, 0.99, 1.04828]),
    'print_film_exposure': 2.3,
    'print_film_density': 26.0,
    
    'highlight_cap': np.array([0.97, 0.97, 0.97]),
    'black_point': 0.0,
    'white_point': 0.0,
    'midtone_saturation': 1.0
}

presets_to_compile = [preset_default, preset_gold]


# Compile the presets to 3D LUT files
for preset in presets_to_compile:
    preset['name'] = preset['name'].strip().replace(' ', '_')
    lut_name = f'flim_{preset["name"]}'
    
    ocio_view_name = f"flim ({preset['name']})"
    ocio_allocation_vars = f'vars: [{preset["lut_compress_log2_min"]}, {preset["lut_compress_log2_max"]}, {2**preset["lut_compress_log2_min"]}]'
    ocio_guide_comments = \
        f"Here's how you can add this to an OpenColorIO config:\n" \
        f"```yaml\n" \
        f"colorspaces:\n" \
        f"  - !<ColorSpace>\n" \
        f"    name: {ocio_view_name}\n" \
        f"    family: Image Formation\n" \
        f"    equalitygroup: ""\n" \
        f"    bitdepth: unknown\n" \
        f"    description: {vt_name} v{vt_version} - https://github.com/bean-mhm/flim\n" \
        f"    isdata: false\n" \
        f"    allocation: uniform\n" \
        f"    from_scene_reference: !<GroupTransform>\n" \
        f"      children:\n" \
        f"        - !<ColorSpaceTransform> {{src: reference, dst: Linear BT.709 I-D65}}\n" \
        f"        - !<RangeTransform> {{min_in_value: 0., min_out_value: 0.}}\n" \
        f"        - !<AllocationTransform> {{allocation: lg2, {ocio_allocation_vars}}}\n" \
        f"        - !<FileTransform> {{src: {lut_name}.spi3d, interpolation: linear}}\n" \
        f"```\n" \
        f"Explanation:\n" \
        f"  1. ColorSpaceTransform converts the input from scene reference to Linear BT.709 I-D65 (Rec.709).\n" \
        f"  2. RangeTransform clips negative values. You might want to use a gamut compression algorithm before this step.\n" \
        f"  3. AllocationTransform is for LUT compression, it takes the log2 of the RGB values, then maps them from a\n" \
        f"     specified range (the first two values after 'vars') to [0,1]. The third value is the offset applied to the\n" \
        f"     values before log2. This is done to keep the blacks.\n" \
        f"  4. Lastly, the FileTransform references the 3D LUT and defines a trilinear interpolation method.\n" \
        f"\n" \
        f"Adding this as a view transform is pretty straightforward:\n" \
        f"```yaml\n" \
        f"displays:\n" \
        f"  sRGB:\n" \
        f"    - !<View> {{name: {ocio_view_name}, colorspace: {ocio_view_name}}}\n" \
        f"    ... (other view transforms here)\n" \
        f"```"

    lut_comments = [
        '-------------------------------------------------',
        '',
        f'{vt_name} v{vt_version} - Bean\'s Filmic Transform',
        '',
        f'Preset: {preset["name"]}',
        f'URL: {preset["info_url"]}',
        '',
        'LUT input is expected to be in Linear BT.709 I-D65 and gone through an AllocationTransform like the following:',
        f'!<AllocationTransform> {{allocation: lg2, {ocio_allocation_vars}}}',
        '',
        'Output will be in sRGB 2.2.',
        ''] + \
        ocio_guide_comments.splitlines() + [\
        '',
        'Repo:',
        'https://github.com/bean-mhm/flim',
        '',
        'Read more:',
        'https://opencolorio.readthedocs.io/en/latest/guides/authoring/authoring.html#how-to-configure-colorspace-allocation',
        '',
        '-------------------------------------------------'
    ]
    
    print(f'Compiling preset "{preset["name"]}"')
    
    t_start = time.time()
    
    # Make a linear 3D LUT
    print('Making a linear 3D LUT...')
    lut = colour.LUT3D(
        table=colour.LUT3D.linear_table(preset['lut_quantize']),
        name=vt_name,
        domain=np.array([[0, 0, 0], [1, 1, 1]]),
        size=preset['lut_quantize'],
        comments=lut_comments
    )
    
    # Apply transform on the LUT table
    print('Applying transform on the LUT table...')
    lut.table = apply_transform(lut.table, preset)

    # Write the LUT
    print('Writing the LUT...')
    script_dir = os.path.realpath(os.path.dirname(__file__))
    colour.write_LUT(
        LUT=lut,
        path=f"{script_dir}/{lut_name}.spi3d",
        decimals=5,
        method='Sony SPI3D'
    )

    t_end = time.time()
    
    print(f'Preset "{preset["name"]}" compiled in {t_end - t_start:.1f} s.\n')
