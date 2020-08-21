#!/usr/bin/python3

from PIL import Image
from scipy import misc, ndimage
import numpy as np
import numpy as np
import sys
import threading
import argparse
import colorsys

#
#   UTILITY FUNCTIONS
#

def as_pixel_pos(v: [float]):
    return [round(i, 0) for i in v]

def wiggle_vert(v: [float], intensity: float):
    return [(i + np.random.uniform(-1, 1) * intensity) for i in v]

def clip_to_image(v: [float], imgdim: [float]):
    for i in range(0, len(imgdim)):
        v[i] = max(0, min(imgdim[i] - 1, v[i]))
    return v

def tri2d_area(v0, v1, v2):
    return abs((v0[0]*(v1[1]-v2[1]) + v1[0]*(v2[1]-v0[1]) + v2[0]*(v0[1]-v1[1]))/2)

def tri2d_point_inside(v0, v1, v2, p):
    A = tri2d_area(v0, v1, v2)
    A0 = tri2d_area(p, v1, v2)
    A1 = tri2d_area(v0, p, v2)
    A2 = tri2d_area(v0, v1, p)
    return (A == (A0 + A1 + A2))

def average_region(imgv, v1, v2, v3, cdev=0):
    region = []
    avgcol = np.zeros(3)
    # Find bounding box for region to speed up processing
    # top, left, bottom, right
    bb = [  int(min(v1[1], v2[1], v3[1])),
            int(min(v1[0], v2[0], v3[0])),
            int(max(v1[1], v2[1], v3[1])),
            int(max(v1[0], v2[0], v3[0]))]

    # Calculate average color in the region
    for y in range(bb[0], bb[2] + 1):
        for x in range(bb[1], bb[3] + 1):
            if tri2d_point_inside(v1, v2, v3, [x,y]):
                region.append([x, y])
                avgcol[0] += imgv[y, x, 0]
                avgcol[1] += imgv[y, x, 1]
                avgcol[2] += imgv[y, x, 2]
    
    avgcol /= len(region)

    # Pass from RGB to HLS
    avgcol = list(colorsys.rgb_to_hls(avgcol[0], avgcol[1], avgcol[2]))
    # Calculate color brightness change
    avgcol[1] *= 1.0 + (np.random.uniform(-1, 1) * (cdev/100))
    # Return from HLS to RGB
    avgcol = list(colorsys.hls_to_rgb(avgcol[0], avgcol[1], avgcol[2]))
    # Make sure all components are positive
    avgcol[0] = max(0, min(255, abs(avgcol[0])))
    avgcol[1] = max(0, min(255, abs(avgcol[1])))
    avgcol[2] = max(0, min(255, abs(avgcol[2])))

    # Set all pixels in that region to its average color
    for pix in region:
        imgv[pix[1], pix[0], 0] = avgcol[0]
        imgv[pix[1], pix[0], 1] = avgcol[1]
        imgv[pix[1], pix[0], 2] = avgcol[2]

def display_progress(total, current):
    print(f"Progress: {round((current/total)*100, 1)}%   ", end='\r')

#
#   MAIN
#

parser = argparse.ArgumentParser(prog='lowpoly',description='Lowpolyfy an image.')
parser.add_argument('input_img', type=str, help='input image (at least 2x2)')
parser.add_argument('output_img', type=str, help='output image name')
parser.add_argument('-dx', '--densityx', type=float, default=10.0, help='number of grid points along X axis', metavar='density')
parser.add_argument('-dy', '--densityy', type=float, default=10.0, help='number of grid points along Y axis', metavar='density')
parser.add_argument('-a', '--antialias', type=int, default=2, help='antialias scale factor', metavar='aascale')
parser.add_argument('-w', '--wiggle', type=int, default=0, help='random grid wiggle magnitude (pixel)', metavar='wiggle')
parser.add_argument('-cd', '--colordev', type=float, default=0.0, help='random color brightness deviation (percentage)', metavar='colordev')
parser.add_argument('-s', '--scale', type=float, default=1.0, help='output image scale factor', metavar='scale')


args = parser.parse_args()

# Adjusting input arguments
args.wiggle *= args.antialias * args.scale

# Load original image
img = Image.open(args.input_img)

if img.width < 2 or img.height < 2:
    print("error: image width and height must be greater than 2 pixels",file=sys.stderr)
    exit(1)

print(f"Input image: {args.input_img} w:{img.width} h:{img.height}")

img = img.resize((int(img.width * args.antialias * args.scale), 
                int(img.height * args.antialias * args.scale)),
                Image.BICUBIC)
imgv = np.asarray(img)
imgv = imgv.copy()

if args.antialias > 1 or args.scale > 1:
    print(f"Upscaling to: w:{img.width} h:{img.height}")

# Generate a map of evenly spaced vertices,
# applying a wiggle and clipping them to image size
vertmap = []
for y in np.linspace(0, img.height - 1, num=args.densityy):
    row = []
    for x in np.linspace(0, img.width - 1, num=args.densityx):
        vert = [x,y]
        if (x > 0 and x < img.width - 1) and (y > 0 and y < img.height - 1):
            vert = wiggle_vert(vert, args.wiggle)
        vert = as_pixel_pos(vert)
        vert = clip_to_image(vert, [img.width, img.height])
        row.append(vert)
    vertmap.append(row)

total_triangles = 2 * (len(vertmap) - 1) * (len(vertmap[0]) - 1)
print(f"Generated grid of {total_triangles} triangles")



# Loop through all the regions and average them
processed_triangles = 0

# Upper left triangles first...
for r in range(0, len(vertmap) - 1):
    for c in range(0, len(vertmap[0]) - 1):
        v1 = vertmap[r      ][c     ]
        v2 = vertmap[r      ][c + 1 ]
        v3 = vertmap[r + 1  ][c     ]
        average_region(imgv, v1, v2, v3, args.colordev)
        processed_triangles += 1
        display_progress(total_triangles, processed_triangles)

# ...bottom right triangles then
for r in range(1, len(vertmap)):
    for c in range(1, len(vertmap[0])):
        v1 = vertmap[r      ][c - 1 ]
        v2 = vertmap[r      ][c     ]
        v3 = vertmap[r - 1  ][c     ]
        average_region(imgv, v1, v2, v3, args.colordev)
        processed_triangles += 1
        display_progress(total_triangles, processed_triangles)


# Save image back

imgout = Image.fromarray(imgv)
imgout = imgout.resize((int(imgout.width / args.antialias), int(imgout.height / args.antialias)), Image.LANCZOS)
print(f"Output image: {args.output_img} w:{imgout.width} h:{imgout.height}")

imgout.save(args.output_img)
print("Done")
