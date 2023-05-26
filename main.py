"""

3D LUT Generator for flim

Repo:
https://github.com/bean-mhm/flim

"""


import numpy as np
import colour
import os
import time

from flim import apply_transform, vt_version


# Parameters

compress_lg2_min = -11
compress_lg2_max = 11

parallel_processing = True

lut_dims = 80
lut_filename = 'flim'
lut_comments = [
    '-------------------------------------------------',
    '',
    f'flim v{vt_version} - Bean\'s Filmic Transform',
    '',
    'LUT input is expected to be in Linear BT.709 I-D65 and gone through an AllocationTransform like the following:',
    f'!<AllocationTransform> {{allocation: lg2, vars: [{compress_lg2_min}, {compress_lg2_max}, {2**compress_lg2_min}]}}',
    '',
    'Output will be in sRGB 2.2.',
    '',
    'Repo:',
    'https://github.com/bean-mhm/flim',
    '',
    'Read more:',
    'https://opencolorio.readthedocs.io/en/latest/guides/authoring/authoring.html#how-to-configure-colorspace-allocation',
    '',
    '-------------------------------------------------'
]


# Print the parameters
print(f'{vt_version = }')
print(f'{compress_lg2_min = }')
print(f'{compress_lg2_max = }')
print(f'{parallel_processing = }')
print(f'{lut_dims = }')
print(f'{lut_filename = }')
print(f'{lut_comments = }')
print('')

t_start = time.time()

# Make a linear 3D LUT
print('Making a linear 3D LUT...')
lut = colour.LUT3D(
    table = colour.LUT3D.linear_table(lut_dims),
    name = 'flim',
    domain = np.array([[0, 0, 0], [1, 1, 1]]),
    size = lut_dims,
    comments = lut_comments
)

# Apply transform on the LUT
print('Applying the transform...')
lut.table = apply_transform(lut.table, compress_lg2_min, compress_lg2_max, parallel_processing)

# Write the LUT
print('Writing the LUT...')
script_dir = os.path.realpath(os.path.dirname(__file__))
colour.write_LUT(
    LUT = lut,
    path = f"{script_dir}/{lut_filename}.spi3d",
    decimals = 6,
    method = 'Sony SPI3D'
)

t_end = time.time()

print(f'Done ({t_end - t_start:.1f} s)')
