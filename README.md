# 🎞️ flim - Bean's Filmic Transform

## Introduction

flim is an experimental film emulation view transform that can be used for displaying digital open-domain (HDR) images, preferably in an [OpenColorIO](https://opencolorio.org/) environment.

## Eye Candy

- See comparisons between flim and other view transforms in the [releases](https://github.com/bean-mhm/flim/releases) section.

- You can find links to collections of OpenEXR image files for testing in [Useful Links](#useful-links).

- Below are some example images gone through flim v0.4.0.

![10 - SRIC_arri_alexa35 01017 - 2 flim](https://github.com/bean-mhm/flim/assets/98428255/030b2ca1-37aa-45e2-834f-dac077a4f353)

![13 - SRIC_arri_alexa35 01033 - 2 flim](https://github.com/bean-mhm/flim/assets/98428255/f3a5a326-4989-4ff6-af20-81a4aef80aa0)

![18 - SRIC_arri_alexa35 01038 - 2 flim](https://github.com/bean-mhm/flim/assets/98428255/5d543d1b-ef2e-4500-b9cd-af59a0028c9e)

![26 - SRIC_hdm-vmlab-hdr 01033 - 2 flim](https://github.com/bean-mhm/flim/assets/98428255/32c9faca-c14f-4b2d-b256-ad71e6ee50fd)

![33 - SRIC_red 01006 - 2 flim](https://github.com/bean-mhm/flim/assets/98428255/86fb5ec7-165e-4733-95c1-97a5f6cbe758)

![37 - courtyard_night_4k - 2 flim](https://github.com/bean-mhm/flim/assets/98428255/83bc352e-c8a7-4d97-83b0-1521dbe2e72e)

![41 - pretville_street_4k - 2 flim](https://github.com/bean-mhm/flim/assets/98428255/a1886812-4e0d-432d-9291-3e4fd9269c54)

![53 - lakeside_2k - 2 flim](https://github.com/bean-mhm/flim/assets/98428255/3e125013-a67a-44ee-867b-410a1fb0f7c6)

![55 - out_sweep - 2 flim](https://github.com/bean-mhm/flim/assets/98428255/cccbb62a-e2f2-4529-9f88-e012abe0ad97)



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

 - flim's 3D LUT is designed to be used in an [OpenColorIO](https://opencolorio.org/) environment, but depending on your software and environment, you might be able to manually replicate the transforms in your custom pipeline.
 
 - flim only supports the sRGB display format as of now.

If `main.py` runs successfully, you should see a file named `flim.spi3d` in the same directory. Alternatively, you can look up the latest LUT - no pun intended - in the [releases](https://github.com/bean-mhm/flim/releases) section, which may be outdated.

The LUT's expected input and output formats are mentioned in the LUT comments at end of the file, but they can also be seen in the code.

Here's an example of the LUT comments (note that this might not match the latest version):

```
# -------------------------------------------------
# 
# flim v0.4.0 - Bean's Filmic Transform
# 
# LUT input is expected to be in Linear BT.709 I-D65 and gone through an AllocationTransform like the following:
# !<AllocationTransform> {allocation: lg2, vars: [-11, 12, 0.00048828125]}
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
        - !<RangeTransform> {min_in_value: 0., min_out_value: 0.}
        - !<AllocationTransform> {allocation: lg2, vars: [-11, 12, 0.00048828125]}
        - !<FileTransform> {src: flim.spi3d, interpolation: linear}
```

1. Paying attention to the transforms, you will notice a `ColorSpaceTransform` from `Linear CIE-XYZ I-E` to `Linear BT.709 I-D65`. This is because the example OCIO config has its reference color space (the `reference` role) set to `Linear CIE-XYZ I-E`. If your config already uses `Linear BT.709 I-D65` (Linear Rec.709) as its reference this is not needed. If your config uses another color space as its reference, you should manually do a conversion to `Linear BT.709 I-D65`. You can get the conversion matrices using the [Colour](https://www.colour-science.org/) library.

2. Then, we have a `RangeTransform` which is there to eliminate negative values (out-of-gamut). This is not the best approach as it will cause weird transitions in images that have a lot of negative values, but it is what flim uses for now.

3. Next, we have an `AllocationTransform` which can be directly copied from the LUT comments. The `AllocationTransform` here takes the log2 of the tristimulus (RGB) values and maps them from a specified range (the first two values after `vars`) to the [0, 1] range. The third value in `vars` is the offset applied to the values before mapping. This is done to keep the blacks.

4. Finally, a `FileTransform` references the 3D LUT.

Here's an example of how you can add flim as a view transform to an OCIO config:

```yaml
displays:
  sRGB:
    - !<View> {name: flim, colorspace: flim}
    ...
```

> `...` refers to the other view transforms in the config. `...` is generally used as a placeholder for the other parts of the code. I can't believe I had to mention this, but a friend was actually confused by it.

## Useful Links

- [The Hitchhiker's Guide to Digital Colour - Troy Sobotka](https://hg2dc.com/)
- [CG Cinematography - Christophe Brejon](https://chrisbrejon.com/cg-cinematography/)
- [AgX Config Generator - Troy Sobotka](https://github.com/sobotka/SB2383-Configuration-Generation)
- [RealBloom, Physically Accurate Bloom Simulation - Me](https://github.com/bean-mhm/realbloom)
- [Test Image Collection 1 - Troy Sobotka](https://github.com/sobotka/Testing_Imagery)
- [Test Image Collection 2 - Troy Sobotka](https://github.com/sobotka/images)
- [PolyHaven, HDRIs](https://polyhaven.com/hdris)
