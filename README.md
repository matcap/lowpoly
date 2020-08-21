# lowpoly

 A simple and inefficient low-polygon image generator 

## Usage
```
Lowpolyfy an image.

positional arguments:
  input_img             input image (at least 2x2)
  output_img            output image name

optional arguments:
  -h, --help            show this help message and exit
  -dx density, --densityx density
                        number of grid points along X axis
  -dy density, --densityy density
                        number of grid points along Y axis
  -a aascale, --antialias aascale
                        antialias scale
  -w wiggle, --wiggle wiggle
                        random grid wiggle magnitude (pixel)
  -cd--colordev colordev
                        random color brightness deviation (percentage)
```