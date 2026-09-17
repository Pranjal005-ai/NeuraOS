"""
=========================================================
File: glow.py
Author: Pranjal

Purpose:
Glow-rendering helpers for Ved's face.

WHY PREMULTIPLIED COLOUR
------------------------
pygame's BLEND_RGB_ADD / BLEND_RGBA_ADD add raw channel
values to the destination. They do NOT scale by the
source alpha. So drawing (18, 82, 200, 5) and blitting
additively adds a FULL (18, 82, 200) -- the alpha is
ignored and every "faint" layer arrives at full strength.
That is what turned the eye halo into a solid disc.

The fix: bake the falloff into RGB itself (premultiply),
keep alpha at 255, and blit with BLEND_RGB_ADD. Untouched
pixels stay (0,0,0,0) and therefore add nothing.
=========================================================
"""

import math

import pygame

try:
    from pygame import gfxdraw
    _HAS_GFX = True
except ImportError:
    _HAS_GFX = False


_RADIAL_CACHE = {}


####################################################
# Smooth variable-width strokes
#
# pygame.draw.arc gives a hard-edged, constant-width,
# aliased stroke. Building the stroke as a polygon that
# follows a centreline lets the width vary along its
# length (fat in the middle, tapering to points) and
# lets gfxdraw antialias the edges.
####################################################

def _fill_poly(surf, points, colour):

    pts = [(int(round(p[0])), int(round(p[1]))) for p in points]

    if len(pts) < 3:
        return

    if _HAS_GFX:
        gfxdraw.filled_polygon(surf, pts, colour)
        gfxdraw.aapolygon(surf, pts, colour)
    else:
        pygame.draw.polygon(surf, colour, pts)


def stroke_outline(points, thickness):
    """
    Expand a centreline into a closed polygon outline.

    thickness may be a scalar or a per-point list.
    """

    n = len(points)

    if not isinstance(thickness, (list, tuple)):
        thickness = [thickness] * n

    left = []
    right = []

    for i, (x, y) in enumerate(points):

        if i == 0:
            tx = points[1][0] - x
            ty = points[1][1] - y
        elif i == n - 1:
            tx = x - points[n - 2][0]
            ty = y - points[n - 2][1]
        else:
            tx = points[i + 1][0] - points[i - 1][0]
            ty = points[i + 1][1] - points[i - 1][1]

        length = math.hypot(tx, ty) or 1.0

        nx = -ty / length
        ny = tx / length

        h = thickness[i] / 2.0

        left.append((x + nx * h, y + ny * h))
        right.append((x - nx * h, y - ny * h))

    return left + list(reversed(right))


def glow_stroke(
    screen,
    color,
    points,
    thickness,
    layers=4,
    bloom=0.15
):
    """
    Draw a smooth tapering stroke with a soft bloom.
    points is a centreline; thickness scalar or per-point.
    """

    if len(points) < 2:
        return

    n = len(points)

    if not isinstance(thickness, (list, tuple)):
        thickness = [thickness] * n

    spread = layers * 4 + max(thickness)
    pad = int(spread) + 4

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    left = int(min(xs)) - pad
    top = int(min(ys)) - pad

    surf = pygame.Surface(
        (
            int(max(xs) - min(xs)) + pad * 2,
            int(max(ys) - min(ys)) + pad * 2
        ),
        pygame.SRCALPHA
    )

    local = [(x - left, y - top) for (x, y) in points]

    # Bloom passes: same centreline, progressively fatter.
    for i in range(layers, 0, -1):

        grow = i * 3.0
        factor = bloom * (1.0 - (i - 1) / float(layers)) ** 1.6

        _fill_poly(
            surf,
            stroke_outline(local, [t + grow for t in thickness]),
            _scale(color, factor)
        )

    # Core
    _fill_poly(
        surf,
        stroke_outline(local, list(thickness)),
        _scale(color, 1.0)
    )

    screen.blit(
        surf,
        (left, top),
        special_flags=pygame.BLEND_RGB_ADD
    )


def glow_polygon_outline(
    screen,
    color,
    points,
    thickness,
    layers=4,
    bloom=0.15
):
    """
    Same as glow_stroke but for a closed shape --
    repeats the first point so the outline joins up.
    """

    closed = list(points) + [points[0]]

    glow_stroke(
        screen,
        color,
        closed,
        thickness,
        layers=layers,
        bloom=bloom
    )


def fill_shape(screen, color, points):
    """Antialiased solid fill, drawn straight to screen."""

    _fill_poly(screen, points, color)



def _scale(color, factor):
    """Premultiply a colour by a 0..1 intensity."""

    factor = max(0.0, min(1.0, factor))

    return (
        int(color[0] * factor),
        int(color[1] * factor),
        int(color[2] * factor),
        255
    )


####################################################
# Radial glow (soft halo)
####################################################

def radial_glow(color, radius, layers=30, intensity=0.38):
    """
    Cached circular falloff, premultiplied.
    intensity = brightness at the very centre (0..1).
    """

    key = (tuple(color), radius, layers, round(intensity, 3))

    if key in _RADIAL_CACHE:
        return _RADIAL_CACHE[key]

    size = radius * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)

    # Largest & faintest first, smallest & brightest last.
    for i in range(layers, 0, -1):

        r = max(1, int(radius * i / layers))

        # 1.0 at the centre, 0.0 at the edge.
        t = 1.0 - (i / float(layers))

        pygame.draw.circle(
            surf,
            _scale(color, intensity * (t ** 2.4)),
            (radius, radius),
            r
        )

    _RADIAL_CACHE[key] = surf
    return surf


def draw_radial_glow(screen, color, center, radius, intensity=0.38):

    surf = radial_glow(color, radius, intensity=intensity)

    screen.blit(
        surf,
        (int(center[0]) - radius, int(center[1]) - radius),
        special_flags=pygame.BLEND_RGB_ADD
    )


####################################################
# Glowing arc
####################################################

def glow_arc(
    screen,
    color,
    rect,
    start_angle,
    end_angle,
    width=5,
    layers=5,
    bloom=0.16
):

    x, y, w, h = rect
    pad = layers * 4 + width

    surf = pygame.Surface(
        (w + pad * 2, h + pad * 2),
        pygame.SRCALPHA
    )

    for i in range(layers, 0, -1):

        grow = i * 3

        # Outer layers dimmer than inner ones.
        factor = bloom * (1.0 - (i - 1) / float(layers)) ** 1.6

        pygame.draw.arc(
            surf,
            _scale(color, factor),
            (pad - grow, pad - grow, w + grow * 2, h + grow * 2),
            start_angle,
            end_angle,
            width + i * 2
        )

    pygame.draw.arc(
        surf,
        _scale(color, 1.0),
        (pad, pad, w, h),
        start_angle,
        end_angle,
        width
    )

    screen.blit(
        surf,
        (x - pad, y - pad),
        special_flags=pygame.BLEND_RGB_ADD
    )


####################################################
# Glowing straight line
####################################################

def glow_line(
    screen,
    color,
    start_pos,
    end_pos,
    width=5,
    layers=5,
    bloom=0.16
):

    x1, y1 = start_pos
    x2, y2 = end_pos

    pad = layers * 4 + width

    left = int(min(x1, x2)) - pad
    top = int(min(y1, y2)) - pad

    surf_w = int(abs(x2 - x1)) + pad * 2
    surf_h = int(abs(y2 - y1)) + pad * 2

    surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)

    p1 = (x1 - left, y1 - top)
    p2 = (x2 - left, y2 - top)

    for i in range(layers, 0, -1):

        factor = bloom * (1.0 - (i - 1) / float(layers)) ** 1.6

        pygame.draw.line(
            surf,
            _scale(color, factor),
            p1,
            p2,
            width + i * 3
        )

    pygame.draw.line(surf, _scale(color, 1.0), p1, p2, width)

    screen.blit(
        surf,
        (left, top),
        special_flags=pygame.BLEND_RGB_ADD
    )


####################################################
# Glowing ellipse outline
####################################################

def glow_ellipse(
    screen,
    color,
    rect,
    width=5,
    layers=5,
    bloom=0.16
):

    x, y, w, h = rect
    pad = layers * 4 + width

    surf = pygame.Surface(
        (w + pad * 2, h + pad * 2),
        pygame.SRCALPHA
    )

    for i in range(layers, 0, -1):

        grow = i * 3
        factor = bloom * (1.0 - (i - 1) / float(layers)) ** 1.6

        pygame.draw.ellipse(
            surf,
            _scale(color, factor),
            (pad - grow, pad - grow, w + grow * 2, h + grow * 2),
            max(1, width + i)
        )

    pygame.draw.ellipse(
        surf,
        _scale(color, 1.0),
        (pad, pad, w, h),
        width
    )

    screen.blit(
        surf,
        (x - pad, y - pad),
        special_flags=pygame.BLEND_RGB_ADD
    )


####################################################
# Glowing circle outline
####################################################

def glow_circle(
    screen,
    color,
    center,
    radius,
    width=5,
    layers=5,
    bloom=0.16
):

    glow_ellipse(
        screen,
        color,
        (
            int(center[0]) - radius,
            int(center[1]) - radius,
            radius * 2,
            radius * 2
        ),
        width=width,
        layers=layers,
        bloom=bloom
    )