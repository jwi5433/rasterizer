import numpy as np
from PIL import Image
import sys

class Rasterizer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.framebuffer = np.zeros((height, width, 4), dtype=np.uint8)
        self.position_buffer = []
        self.color_buffer = []

    def set_pixel(self, x, y, color):
        x, y = int(x), int(y)
        if 0 <= x < self.width and 0 <= y < self.height:
            self.framebuffer[y, x] = [int(max(0, min(255, c * 255))) for c in color] + [255]

    def viewport_transform(self, x, y, z, w):
        return int((x / w + 1) * self.width / 2), int((y / w + 1) * self.height / 2)

    def draw_triangle(self, vertices, colors):
        def edge_function(a, b, c):
            return (c[0] - a[0]) * (b[1] - a[1]) - (c[1] - a[1]) * (b[0] - a[0])

        min_x = max(0, min(v[0] for v in vertices))
        max_x = min(self.width - 1, max(v[0] for v in vertices))
        min_y = max(0, min(v[1] for v in vertices))
        max_y = min(self.height - 1, max(v[1] for v in vertices))

        area = edge_function(vertices[0], vertices[1], vertices[2])

        for y in range(int(min_y), int(max_y) + 1):
            for x in range(int(min_x), int(max_x) + 1):
                w0 = edge_function(vertices[1], vertices[2], (x, y))
                w1 = edge_function(vertices[2], vertices[0], (x, y))
                w2 = edge_function(vertices[0], vertices[1], (x, y))

                if w0 >= 0 and w1 >= 0 and w2 >= 0:
                    w0 /= area
                    w1 /= area
                    w2 /= area
                    color = tuple(w0 * c0 + w1 * c1 + w2 * c2 for c0, c1, c2 in zip(*colors))
                    self.set_pixel(x, y, color)

    def draw_arrays_triangles(self, first, count):
        for i in range(first, first + count, 3):
            vertices = [self.viewport_transform(*v) for v in self.position_buffer[i:i+3]]
            colors = self.color_buffer[i:i+3]
            self.draw_triangle(vertices, colors)

    def save_image(self, filename):
        Image.fromarray(self.framebuffer, 'RGBA').save(filename)

def parse_input(filename):
    rasterizer = None
    output_file = ""

    with open(filename, 'r') as file:
        for line in file:
            tokens = line.strip().split()
            if not tokens or tokens[0].startswith('#'):
                continue

            if tokens[0] == 'png':
                width, height = int(tokens[1]), int(tokens[2])
                output_file = tokens[3]
                rasterizer = Rasterizer(width, height)
            elif tokens[0] == 'position':
                size = int(tokens[1])
                values = [float(x) for x in tokens[2:]]
                rasterizer.position_buffer = [values[i:i+4] for i in range(0, len(values), size)]
            elif tokens[0] == 'color':
                size = int(tokens[1])
                values = [float(x) for x in tokens[2:]]
                rasterizer.color_buffer = [values[i:i+3] for i in range(0, len(values), size)]
            elif tokens[0] == 'drawArraysTriangles':
                first, count = int(tokens[1]), int(tokens[2])
                rasterizer.draw_arrays_triangles(first, count)

    return rasterizer, output_file

def main():
    if len(sys.argv) == 2:
        rasterizer, output_file = parse_input(sys.argv[1])
        if rasterizer and output_file:
            rasterizer.save_image(output_file)

if __name__ == "__main__":
    main()