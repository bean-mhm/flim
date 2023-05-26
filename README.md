# flim - Bean's Filmic Transform

## Introduction

flim is an experimental film emulation view transform that can be used for displaying digital open-domain (HDR) images.

## Eye Candy

See comparisons between flim and other view transforms in the [releases](https://github.com/bean-mhm/flim/releases) section.

## Scripts

The code is structured in the following way:

| Script | Role | Uses |
|---|---|---|
| main.py | Generates a 3D LUT for flim | flim.py  |
| flim.py | Transforms a given linear 3D LUT table | utils.py |
| utils.py | Contains helper functions | - |

Here are the external libraries required to run the scripts:

 - [Colour](https://www.colour-science.org/)
 
 - [NumPy](https://numpy.org/)
 
 - [Joblib](https://joblib.readthedocs.io/en/latest)

## Using the LUT

First, a few notes:

 - flim's 3D LUT is designed to be used in an [OpenColorIO](https://opencolorio.org/) environment.
 
 - flim only supports the sRGB display format as of now.

If `main.py` runs successfully, you should see a file named `flim.spi3d` in the same directory. Alternatively, you can look up the latest LUT - no pun intended - in the [releases](https://github.com/bean-mhm/flim/releases) section, which may be outdated.

The LUT's expected input and output formats are mentioned in the LUT comments at end of the file, but they can also be seen in the code.

Here's an example of the LUT comments (note that this might not match the latest version):

```
# -------------------------------------------------
# 
# flim v0.2.0 - Bean's Filmic Transform
# 
# LUT input is expected to be in Linear BT.709 I-D65 and gone through an AllocationTransform like the following:
# !<AllocationTransform> {allocation: lg2, vars: [-11, 11, 0.00048828125]}
# 
# Output will be in sRGB 2.2.
# 
# Repo:
# https://github.com/bean-mhm/flim
# 
# Read more:
# https://opencolorio.readthedocs.io/en/latest/guides/authoring/authoring.html#how-to-configure-colorspace-allocation
# 
# -------------------------------------------------
```

Here's an example of how you can add flim to an OCIO config:

```yaml
colorspaces:
  - !<ColorSpace>
    name: flim
    family: Image Formation
    equalitygroup: ""
    bitdepth: unknown
    description: flim - Bean's Filmic Transform
    isdata: false
    allocation: uniform
    from_scene_reference: !<GroupTransform>
      children:
        - !<ColorSpaceTransform> {src: Linear CIE-XYZ I-E, dst: Linear BT.709 I-D65}
        - !<AllocationTransform> {allocation: lg2, vars: [-11, 11, 0.00048828125]}
        - !<FileTransform> {src: flim.spi3d, interpolation: linear}
  ...
```

Paying attention to the transforms, you will notice a `ColorSpaceTransform` from CIE-XYZ I-E to Linear BT.709 I-D65. This is because the example OCIO config has its reference color space (the `reference` role) set to CIE-XYZ I-E. If your config already uses Linear BT.709 I-D65 as its reference this is not needed. If your config uses another color space as its reference, you should manually do a conversion to Linear BT.709 I-D65. You can get the conversion matrices using the [Colour](https://www.colour-science.org/) library.

Next, we have an `AllocationTransform`, which can be directly copied from the LUT comments. The `AllocationTransform` here literally just takes the log2 of the tristimulus (RGB) values and maps them from a specified range (the first two values after `vars`) to the [0, 1] range. The third value in `vars` is the offset applied to the values before mapping. This is done to keep the blacks.

Finally, a `FileTransform` references the 3D LUT.

Here's an example of how you can add flim as a view transform in an OCIO config:

```yaml
displays:
  sRGB:
    - !<View> {name: flim, colorspace: flim}
    ...
```

> `...` refers to the other view transforms in the config. `...` is generally used as a placeholder for the other parts of the code. I can't believe I had to mention this, but a friend was actually confused by it.
