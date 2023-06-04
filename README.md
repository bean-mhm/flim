# 🎞️ flim - Bean's Filmic Transform

## Introduction

flim is an experimental film emulation transform that can be used for:

1. Displaying Digital Open-Domain (HDR) Images
2. Color Grading
3. Post-Processing in Video Games and Shaders ("tone-mapping")

## Eye Candy

- See comparisons between native sRGB, AgX, and flim's presets in the [releases](https://github.com/bean-mhm/flim/releases) section.

- You can find links to collections of OpenEXR image files for testing in [Useful Links](#useful-links).

- Below are some example images gone through flim v0.5.0.

![10 - SRIC_arri_alexa35 01017 - 2 flim](https://github.com/bean-mhm/flim/assets/98428255/1baf7c23-d089-455a-9717-85fe3502d8ec)

![13 - SRIC_arri_alexa35 01033 - 2 flim](https://github.com/bean-mhm/flim/assets/98428255/abf1b5c3-bac6-4ab0-a6ae-e6ca36b83655)

![25 - SRIC_hdm-vmlab-hdr 01032 - 2 flim](https://github.com/bean-mhm/flim/assets/98428255/f5a32d32-2200-49fd-a9e4-bf8957c1e5d2)

![26 - SRIC_hdm-vmlab-hdr 01033 - 2 flim](https://github.com/bean-mhm/flim/assets/98428255/21073d84-43e6-479d-a35c-cef1d95daed4)

![34 - SRIC_red 01006 - 2 flim](https://github.com/bean-mhm/flim/assets/98428255/0d0ca4b9-84a7-4bd5-8545-84d7d1b730f5)

![38 - courtyard_night_4k - 2 flim](https://github.com/bean-mhm/flim/assets/98428255/af6e275b-9cde-4584-960c-34bf54f1ed9b)

![42 - pretville_street_4k - 2 flim](https://github.com/bean-mhm/flim/assets/98428255/a047503f-e3da-446b-b69e-f0422fee7587)

![56 - out_sweep - 2 flim](https://github.com/bean-mhm/flim/assets/98428255/a37dea51-514b-41c9-b273-fc8990ce3454)



## Scripts

The code is structured in the following way:

| Script | Role | Uses |
|---|---|---|
| main.py | Compiles 3D LUTs for flim | flim.py  |
| flim.py | Transforms a given linear 3D LUT table | utils.py |
| utils.py | Contains helper functions | - |

You can add new custom presets in `main.py`, or play with the film emulation chain in `flim.py`.

Here are the external libraries required to run the scripts:

 - [Colour](https://www.colour-science.org/)
 
 - [NumPy](https://numpy.org/)
 
 - [Joblib](https://joblib.readthedocs.io/en/latest)

## Using the LUTs

First, a few notes:

 - flim's 3D LUTs are designed to be used in an [OpenColorIO](https://opencolorio.org/) (OCIO) environment, but depending on your software and environment, you might be able to manually replicate the transforms in your custom pipeline ([See Non-OCIO Guide below](#non-ocio-guide)).
 
 - flim only supports the sRGB display format as of now.

If `main.py` runs successfully, you should see files named like `flim_X.spi3d` in the same directory. Alternatively, you can look up the latest LUTs in the [releases](https://github.com/bean-mhm/flim/releases) section, which may be outdated.

The LUT comments contain most of the information you need. The following is an example of the LUT comments (note that this might not match the latest version).

```
# -------------------------------------------------
# 
# flim v0.6.1 - Bean's Filmic Transform
# 
# Preset: default
# URL: None
# 
# LUT input is expected to be in Linear BT.709 I-D65 and gone through an AllocationTransform like the following:
# !<AllocationTransform> {allocation: lg2, vars: [-11, 12, 0.00048828125]}
# 
# Output will be in sRGB 2.2.
# 
# Here's how you can add this to an OpenColorIO config:
```
```yaml
colorspaces:
  - !<ColorSpace>
    name: flim (default)
    family: Image Formation
    equalitygroup: ""
    bitdepth: unknown
    description: flim v0.6.1 - https://github.com/bean-mhm/flim
    isdata: false
    allocation: uniform
    from_scene_reference: !<GroupTransform>
      children:
        - !<ColorSpaceTransform> {src: reference, dst: Linear BT.709 I-D65}
        - !<RangeTransform> {min_in_value: 0., min_out_value: 0.}
        - !<AllocationTransform> {allocation: lg2, vars: [-11, 12, 0.00048828125]}
        - !<FileTransform> {src: flim_default.spi3d, interpolation: linear}
```
```
# Explanation:
#   1. ColorSpaceTransform converts the input from the scene reference to Linear BT.709 I-D65. If this is named
#      differently in your config (for example Linear Rec.709), change the name manually.
#   2. RangeTransform clips negative values. You might want to use a gamut compression algorithm before this step.
#   3. AllocationTransform is for LUT compression, it takes the log2 of the RGB values and maps them from a
#      specified range (the first two values after 'vars') to [0, 1]. The third value is the offset applied to the
#      values before log2. This is done to keep the blacks.
#   4. Lastly, the FileTransform references the 3D LUT and defines a trilinear interpolation method.
# 
# Adding this as a view transform is pretty straightforward:
```
```yaml
displays:
  sRGB:
    - !<View> {name: flim (default), colorspace: flim (default)}
    ... (other view transforms here)
```
```
# 
# Repo:
# https://github.com/bean-mhm/flim
# 
# Read more:
# https://opencolorio.readthedocs.io/en/latest/guides/authoring/authoring.html#how-to-configure-colorspace-allocation
# 
# -------------------------------------------------
```

### Non-OCIO Guide

You can replicate the transforms farily easily in order to use flim's 3D LUTs in your own pipeline without using OCIO. The following pseudo-code demonstrates the general process to transform a single RGB triplet (note that this might not match the latest version).

```py
# Input RGB values (color space: Linear BT.709 I-D65)
col = np.array([4.2, 0.23, 0.05])

# RangeTransform
# Clip negative values, or use a custom gamut compression algorithm.
col = np.maximum(col, 0.0)

# AllocationTransform
col += 0.00048828125  # offset by 2 to the power of -11 (lower bound after log2)
col = np.log2(col)
col = map_range(col, from=[-11, 12], to=[0, 1], clamp=True)

# Sample from the 3D LUT (output color space: sRGB 2.2)
out = lut.sample(TRILINEAR, col)
```

![3D LUT Visualization](images/3d_lut_vis.png)

## Useful Links

- [The Hitchhiker's Guide to Digital Colour - Troy Sobotka](https://hg2dc.com/)
- [CG Cinematography - Christophe Brejon](https://chrisbrejon.com/cg-cinematography/)
- [RealBloom, Physically Accurate Bloom Simulation - Me](https://github.com/bean-mhm/realbloom)
- [AgX Config Generator - Troy Sobotka](https://github.com/sobotka/SB2383-Configuration-Generation)
- [Test Image Collection 1 - Troy Sobotka](https://github.com/sobotka/Testing_Imagery)
- [Test Image Collection 2 - Troy Sobotka](https://github.com/sobotka/images)
- [PolyHaven, HDRIs](https://polyhaven.com/hdris)
