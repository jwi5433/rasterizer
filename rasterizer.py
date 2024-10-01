import numpy as np
from PIL import Image
import sys

class Rasterizer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.framebuffer = np.zeros((height, width, 4), dtype=np.float32)
        self.position_buffer = []
        self.color_buffer = []

    def set_pixel(self, x, y, color):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.width and 0 <= y < self.height:
            self.framebuffer[y, x] = color

    def viewport_transform(self, x, y, z, w):
        nx = (x / w + 1) * self.width / 2
        ny = (1 - y / w) * self.height / 2  # Changed this line
        return nx, ny

    def interpolate(self, i0, d0, i1, d1):
        if i0 == i1:
            return [d0]
        values = []
        a = (d1 - d0) / (i1 - i0)
        d = d0
        for i in range(int(round(i0)), int(round(i1)) + 1):
            values.append(d)
            d += a
        return values

    def draw_line(self, x0, y0, x1, y1, color0, color1):
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        steep = dy > dx
        
        if steep:
            x0, y0 = y0, x0
            x1, y1 = y1, x1
        
        if x0 > x1:
            x0, x1 = x1, x0
            y0, y1 = y1, y0
            color0, color1 = color1, color0
        
        dx = x1 - x0
        dy = abs(y1 - y0)
        error = dx / 2
        y = int(round(y0))
        y_step = 1 if y0 < y1 else -1
        
        for x in range(int(round(x0)), int(round(x1)) + 1):
            t = (x - x0) / dx if dx != 0 else 0
            color = [c0 * (1 - t) + c1 * t for c0, c1 in zip(color0, color1)]
            if steep:
                self.set_pixel(y, x, color + [1])
            else:
                self.set_pixel(x, y, color + [1])
            
            error -= dy
            if error < 0:
                y += y_step
                error += dx

    def draw_triangle(self, vertices, colors):
        def sort_vertices(verts, cols):
            return zip(*sorted(zip(verts, cols), key=lambda x: x[0][1]))

        vertices, colors = sort_vertices(vertices, colors)
        v0, v1, v2 = vertices
        c0, c1, c2 = colors

        if v1[1] == v2[1]:
            self.fill_bottom_flat_triangle(v0, v1, v2, c0, c1, c2)
        elif v0[1] == v1[1]:
            self.fill_top_flat_triangle(v0, v1, v2, c0, c1, c2)
        else:
            v3x = v0[0] + ((v1[1] - v0[1]) / (v2[1] - v0[1])) * (v2[0] - v0[0])
            v3 = (v3x, v1[1])
            t = (v1[1] - v0[1]) / (v2[1] - v0[1])
            c3 = tuple(c0[i] * (1 - t) + c2[i] * t for i in range(3))
            self.fill_bottom_flat_triangle(v0, v1, v3, c0, c1, c3)
            self.fill_top_flat_triangle(v1, v3, v2, c1, c3, c2)

    def fill_bottom_flat_triangle(self, v0, v1, v2, c0, c1, c2):
        slope1 = (v1[0] - v0[0]) / (v1[1] - v0[1]) if v1[1] != v0[1] else 0
        slope2 = (v2[0] - v0[0]) / (v2[1] - v0[1]) if v2[1] != v0[1] else 0
        
        y_start, y_end = int(round(v0[1])), int(round(v1[1]))
        for y in range(y_start, y_end + 1):
            t = (y - v0[1]) / (v1[1] - v0[1]) if v1[1] != v0[1] else 1
            x1 = v0[0] + slope1 * (y - v0[1])
            x2 = v0[0] + slope2 * (y - v0[1])
            color_left = tuple(c0[i] * (1 - t) + c1[i] * t for i in range(3))
            color_right = tuple(c0[i] * (1 - t) + c2[i] * t for i in range(3))
            self.draw_line(x1, y, x2, y, color_left, color_right)

    def fill_top_flat_triangle(self, v0, v1, v2, c0, c1, c2):
        slope1 = (v2[0] - v0[0]) / (v2[1] - v0[1]) if v2[1] != v0[1] else 0
        slope2 = (v2[0] - v1[0]) / (v2[1] - v1[1]) if v2[1] != v1[1] else 0
        
        y_start, y_end = int(round(v2[1])), int(round(v0[1]))
        for y in range(y_start, y_end - 1, -1):
            t = (v2[1] - y) / (v2[1] - v0[1]) if v2[1] != v0[1] else 1
            x1 = v2[0] - slope1 * (v2[1] - y)
            x2 = v2[0] - slope2 * (v2[1] - y)
            color_left = tuple(c2[i] * (1 - t) + c0[i] * t for i in range(3))
            color_right = tuple(c2[i] * (1 - t) + c1[i] * t for i in range(3))
            self.draw_line(x1, y, x2, y, color_left, color_right)

    def draw_arrays_triangles(self, first, count):
        for i in range(first, first + count, 3):
            vertices = [self.viewport_transform(*v) for v in self.position_buffer[i:i+3]]
            colors = self.color_buffer[i:i+3]
            self.draw_triangle(vertices, colors)

    def save_image(self, filename):
        img_array = (np.clip(self.framebuffer, 0, 1) * 255).astype(np.uint8)
        Image.fromarray(img_array, 'RGBA').save(filename)

def parse_input(filename):
    rasterizer = None
    output_file = ""

    with open(filename, 'r') as file:
        for line in file:
            tokens = line.strip().split()
            if not tokens:
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
    if len(sys.argv) != 2:
        print("Usage: python rasterizer.py <input_file>")
        return

    rasterizer, output_file = parse_input(sys.argv[1])
    if rasterizer and output_file:
        rasterizer.save_image(output_file)

if __name__ == "__main__":
    main()