"""
Fake 3.5" floppy disk drive -- Blender build script.

A Commodore 1541-style prop with a working mechanical eject mechanism and a
hidden NFC reader bay. Insert a disk and a lever pushes the front button out;
press the button and the disk is ejected. No springs and no electronics in
the mechanism: it is a first-class lever driven by the disk itself. It takes
both 3D-printed dummy disks and real 3.5" floppies.

Parts, hardware, print settings and assembly order are in README.md.

RUNNING IT
    Blender >= 3.0, Scripting tab, Run. It wipes the scene and rebuilds every
    part from scratch, so it is safe to re-run after editing any dimension.
    Everything downstream of a dimension is derived, not hard-coded, so a
    change propagates instead of leaving something behind.

CONVENTIONS
    Millimetres throughout. X across the drive, Y front-to-back (negative is
    the front), Z up from the underside.

    Two rules govern every boolean, and both exist because their failures are
    hard to see and easy to avoid:

      OVERSHOOT   every cutter overshoots the face it cuts. A cutter face
                  exactly coplanar with a part face can leave a zero-thickness
                  membrane instead of a hole.
      EMBED       every unioned feature buries itself in its parent. A feature
                  that merely touches can survive as a separate shell: it
                  looks attached and prints as two pieces.

    count_shells() is the check for the second one. It should return 1 for
    every part.

Copyright (c) 2026
Licensed under CC BY-SA 4.0 -- see LICENSE
"""

import bpy
import bmesh
import math
import mathutils

SHOW_DISK_INSERTED = False

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for blocks in (bpy.data.meshes, bpy.data.collections):
        for b in list(blocks):
            if b.users == 0:
                blocks.remove(b)

def bool_op(obj, cutter, operation='DIFFERENCE'):
    mod = obj.modifiers.new(name="Bool", type='BOOLEAN')
    mod.operation = operation
    mod.object = cutter
    mod.solver = 'EXACT'
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)

def box(name, size, center):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o

def box_range(name, x, y, z):
    """Box given by ranges. Ranges are sorted before subtracting.

    A reversed range yields a negative scale, which flips the mesh normals
    inward; the EXACT solver then reads the volume as negative and a UNION
    starts behaving like a DIFFERENCE. Nothing here reverses a range, but
    it is an expensive fault to diagnose and a cheap one to rule out.
    """
    x = (min(x), max(x)); y = (min(y), max(y)); z = (min(z), max(z))
    for rod, r in zip("XYZ", (x, y, z)):
        if r[1] - r[0] <= 0:
            raise ValueError(f"box_range({name!r}): thickness zero en {rod}")
    return box(name, (x[1]-x[0], y[1]-y[0], z[1]-z[0]),
                 ((x[0]+x[1])/2, (y[0]+y[1])/2, (z[0]+z[1])/2))

def prism_yz(name, x, profile):
    """Prism with a polygonal Y-Z section, extruded along X.

    Forces the profile counter-clockwise and the faces outward. Otherwise
    the normals come out inverted and the boolean leaves membranes instead
    of cutting."""
    area = 0.5 * sum(profile[i][0]*profile[(i+1) % len(profile)][1]
                     - profile[(i+1) % len(profile)][0]*profile[i][1]
                     for i in range(len(profile)))
    p = list(profile) if area > 0 else list(reversed(profile))
    n = len(p)
    verts = [(x[0], y, z) for y, z in p] + [(x[1], y, z) for y, z in p]
    faces = [list(range(n-1, -1, -1)), list(range(n, 2*n))]
    for i in range(n):
        j = (i+1) % n
        faces.append([i, j, j+n, i+n])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(o)
    return o

def cyl_y(radius, length, center, verts=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius,
                                        depth=length, location=center)
    o = bpy.context.object
    o.rotation_euler[0] = math.radians(90)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    return o
def cyl_z(radius, length, center, verts=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius,
                                        depth=length, location=center)
    return bpy.context.object

def bevel(obj, width, segments=3):
    m = obj.modifiers.new(name="Bevel", type='BEVEL')
    m.width = width
    m.segments = segments
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=m.name)

def duplicate(obj, name):
    n = obj.copy()
    n.data = obj.data.copy()
    n.name = name
    bpy.context.collection.objects.link(n)
    return n

def rotate_mesh(obj, angle, axis, pivot):
    """Rotate an object's MESH about a pivot given in WORLD space.

    obj.data is in LOCAL coordinates and these parts keep their
    obj.location (box() applies scale only, never position), so the
    pivot has to be converted by subtracting it. Passing a world-space
    pivot spins the part about a point offset by obj.location, which
    throws it across the scene instead of seating it."""
    p = mathutils.Vector(pivot) - obj.location
    M = (mathutils.Matrix.Translation(p)
         @ mathutils.Matrix.Rotation(angle, 4, axis)
         @ mathutils.Matrix.Translation(-p))
    obj.data.transform(M)

def count_shells(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    seen, n = set(), 0
    for v in bm.verts:
        if v in seen:
            continue
        n += 1
        stack = [v]
        while stack:
            w = stack.pop()
            if w in seen:
                continue
            seen.add(w)
            for e in w.link_edges:
                stack.append(e.other_vert(w))
    bm.free()
    return n

# ============================================================
# CONVENTIONS FOR BOOLEAN WORK
# ============================================================
# EMBED  how deep a unioned feature buries itself in its parent. A feature
#        that merely touches its parent can survive as a separate shell:
#        it looks attached and prints as two pieces.
# OVERSHOOT   how far a cutter overshoots the face it cuts. A cutter face exactly
#        coplanar with a part face can leave a zero-thickness membrane
#        instead of a hole.
EMBED = 1.0   # how deep unions bury themselves
OVERSHOOT = 4.0   # how far cutters overshoot the face


# ============================================================
# DIMENSIONS
# ============================================================
# Outer shell. X is not symmetric about zero: the drive is wider to the
# right of the disk centreline, as on the original.
BODY_XL, BODY_XR, BODY_Y, BODY_Z = -49.0, 61.0, 108.0, 39.0
BODY_W = BODY_XR - BODY_XL
front_y, back_y = -BODY_Y/2, BODY_Y/2

BEZEL_T, BEZEL_INSET = 2.5, 2.0   # bezel thickness, inset
bezel_front = front_y - BEZEL_T


# --- the disk ---
# Measured from the printed dummy (HD_Floppy_Disk_V03.stl). A real 3.5"
# floppy is ~3.3 mm, 0.3 thinner; the whole retention design has to work
# with both, which is what drives SLOT_CLR_H and RET_BUMP_H below.
DISK_W, DISK_D, DISK_T = 90.0, 93.9, 3.6
SLOT_CLR_W, SLOT_CLR_H = 1.2, 0.5   # channel clearance: across, vertical

SLOT_CX = 6.0   # disk centreline
SLOT_W = DISK_W + SLOT_CLR_W
SLOT_H = DISK_T + SLOT_CLR_H
slot_z0 = 17.5   # channel floor
slot_z1 = slot_z0 + SLOT_H
DISK_ZMID = slot_z0 + DISK_T/2

# How deep the disk goes. Not a chosen number: the rule is that its rear
# edge ends up flush with the back of the front finger recess, so there is
# nothing left to grip and the only way out is the button.
DISK_TIP_Y = (front_y - BEZEL_T) + 8.0 + DISK_D

# The shutter. It is 1.4 mm proud of the shell, so a pusher in the middle
# of the leading edge would only ever touch the shutter -- fine on a printed
# dummy, but on a real disk that is sheet metal being shoved 11 mm at a
# time. The bar pushes on the two shell bands instead, either side of it.
DISK_SHUTTER_PROUD = 1.4
DISK_SHELL_Y = DISK_TIP_Y - DISK_SHUTTER_PROUD
DISK_REAR_Y = DISK_TIP_Y - DISK_D

SLOT_BACK_CLR = 1.5   # shutter never reaches the back of the channel
SLOT_BACK = DISK_TIP_Y + SLOT_BACK_CLR


# The parting line sits at the ROOF of the disk channel, not its floor, so
# that Mech_Plate lands between the two shells like the meat in a
# sandwich and the existing screws and dowels clamp all three. SLOT_FLOOR
# is the channel floor, which used to be the same plane and no longer is.
SLOT_FLOOR = slot_z0
Z_SPLIT = slot_z1

RECESS_C_X, RECESS_C_D, RECESS_C_TOP = (-12.0, 24.0), 8.0, 14.0   # front finger recess
RECESS_L_X, RECESS_R_X = (-38.0, -12.0), (24.0, 50.0)
RECESS_LAT_D, RECESS_LAT_TOP = 3.5, 13.0

RECESS_TOP_C_D = RECESS_C_D   # the recess above the mouth matches the one below
RECESS_TOP_C_H = 5.0
RECESS_TOP_LAT_D, RECESS_TOP_LAT_H = 2.0, 7.0


# --- NFC bay ---
# Sized for a 65 x 65 x 12 mm reader. The whole assembly is centred on the
# body axis, not on X=0: the bay, its rebate, the four screws, the cable
# gland and the cover all follow NFC_CX/NFC_CY.
NFC_W, NFC_D, NFC_H = 68.0, 68.0, 12.7
NFC_CY = (front_y + back_y) / 2
nfc_y0 = NFC_CY - NFC_D/2
nfc_cy = nfc_y0 + NFC_D/2
NFC_CX = SLOT_CX
NFC_SCREW_OFF = 39.0
NFC_COVER_T, NFC_COVER_CLR = 1.8, 0.3   # NFC cover thickness, fit
NFC_COVER_W, NFC_COVER_D = NFC_W + 20.0, NFC_D + 20.0
NFC_COVER_SUNK = 1.0   # cover sits 1 mm proud of nothing -- recessed
NFC_REBATE = NFC_COVER_T + NFC_COVER_SUNK

# Perimeter groove at the bottom of the cover rebate. The printer leaves
# stringing in the inside corner; with the groove it falls into it instead
# of sitting under the cover.
NFC_GROOVE_W, NFC_GROOVE_H = 1.2, 1.0
CABLE_W, CABLE_H = 20.0, 13.0   # cable opening

GLAND_D, GLAND_CLR, GLAND_BORE_R = 8.0, 0.10, 3.0   # gland: depth, fit, bore

CABLE_Z0 = NFC_REBATE - 1.0
CABLE_Z1 = CABLE_Z0 + CABLE_H
CABLE_ZMID = (CABLE_Z0 + CABLE_Z1) / 2


# ============================================================
# FASTENERS
# ============================================================
# --- alignment dowels ---
# Separate rods, not moulded into the base. Standing up out of the base they
# printed with the layers across the load and snapped. Press fit in the top
# shell and sliding in the other two, which matches the assembly order: they
# go into the top first, then the plate and the base drop over them.
DOWEL_R = 2.0
DOWEL_DEPTH_TOP = 4.0   # blind depth in the top shell
DOWEL_DEPTH_BASE = 4.0   # blind depth in the base
DOWEL_FIT_PRESS = 0.10
DOWEL_FIT_SLIDE = 0.25
DOWELS = ((-42.0, 49.0), (54.0, 49.0))
M3_CLR, M3_PILOT = 1.7, 1.05   # clearance and pilot radii


# Countersink cut to the real head: 5.5 mm across and the standard 90 deg.
# An oversized or shallower-angled cone lets the head sit on its outer rim
# only, and sink deeper than intended.
M3_HEAD_D = 5.5
M3_HEAD_R = M3_HEAD_D/2 + 0.2
M3_HEAD_H = M3_HEAD_R - M3_CLR

def countersink(obj, xy, z_face, upward=True):
    """Avellanat de 90 graus a la cara z_face. El con sobresurt OVERSHOOT mm
    per fora de la peça per no deixar cap cara coplanar."""
    r_out = M3_HEAD_R + OVERSHOOT
    if upward:
        z0, z1 = z_face - OVERSHOOT, z_face + M3_HEAD_H
        r1, r2 = r_out, M3_CLR
    else:
        z0, z1 = z_face - M3_HEAD_H, z_face + OVERSHOOT
        r1, r2 = M3_CLR, r_out
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=r1, radius2=r2,
                                    depth=z1 - z0, location=(xy[0], xy[1], (z0 + z1)/2))
    bool_op(obj, bpy.context.object)
SCREWS = ((-44.0, -30.0), (-44.0, 30.0), (56.0, -30.0), (56.0, 30.0))


# ============================================================
# EJECT MECHANISM
# ============================================================
# --- the bar the disk pushes ---
# BAR_TRAVEL is the primary figure and everything else follows from it.
# The bar stops against the disk shell, never the shutter.
BAR_X = 0.0
BAR_TRAVEL = 11.0   # bar travel -- the primary figure
BAR_Y_IN = DISK_SHELL_Y
BAR_Y_OUT = BAR_Y_IN - BAR_TRAVEL

BAR_T = 4.0   # arm thickness (Z)
BAR_W = 10.0   # arm width (X)


# --- middle plate ---
# It is the floor of the mechanism and the roof of the disk channel at the
# same time. Before it existed the bays ran all the way down and the moving
# parts had nothing underneath, so they sagged into the disk channel; a
# floor was impossible because everything is fitted from below. Being a
# separate plate is what resolves that.
PLATE_T = 2.0   # middle plate thickness
PLATE_Z0 = slot_z1
PLATE_Z1 = slot_z1 + PLATE_T

PLATE_X = (BODY_XL, BODY_XR)
PLATE_Y0 = front_y + 0.5

DOWEL_LEN = DOWEL_DEPTH_TOP + PLATE_T + DOWEL_DEPTH_BASE

BAR_Z0 = PLATE_Z1
BAR_Z1 = BAR_Z0 + BAR_T
SHOE_Z0 = 17.8   # shoes stop 0.3 above the channel floor


# Two shoes rather than one central foot: they land on solid shell either
# side of the shutter, and the resultant push stays near the disk center so
# it cannot skew and jam in the 0.6 mm of side clearance.
SHOE_W = 6.0
SHOE_CX = (-35.0, 40.0)
SHOE_X = tuple((cx - SHOE_W/2, cx + SHOE_W/2)
                     for cx in SHOE_CX)

XBAR_X = (SHOE_X[0][0], SHOE_X[1][1])
XBAR_D = 5.0   # crossbar depth (Y)
XBAR_SHUTTER_CLR = 0.5   # crossbar clears the proud shutter
XBAR_Y0 = BAR_Y_OUT + DISK_SHUTTER_PROUD + XBAR_SHUTTER_CLR
XBAR_Y1 = XBAR_Y0 + XBAR_D

RUN_CLR = 0.4   # running clearance in the bays
MECH_Z_TOP = 33.0 + PLATE_T   # roof of the whole mechanism bay
BTN_X = (RECESS_L_X[0] + RECESS_L_X[1]) / 2
BTN_W = 10.0   # button cap size
BTN_CLR = 0.3   # button running fit

BTN_CAP_Z0 = 33.0
BTN_CAP_Z1 = 37.0

LEVER_ARM_BAR, LEVER_ARM_BTN = 18.0, 7.0


# --- scotch yoke, both ends ---
# Each end of the lever is a round boss and the driven part grips it with a
# two-walled fork. It began as a pin in a slot; the pin was a 2.4 mm stub
# loaded in bending with the layers across it and it broke on the second
# press. A fork wall carries the same load with fourteen times the section
# and prints flat. The boss must be wider than the lever body or the lever's
# own corners would foul the fork walls as it swings.
BOSS_R = 6.0
FORK_FIT = 0.3   # total boss-to-fork clearance
FORK_GAP = 2 * BOSS_R + FORK_FIT
FORK_WALL = 4.0   # fork wall thickness -- this is what takes the load
FORK_REACH = BAR_TRAVEL / 2 + FORK_GAP / 2 + FORK_WALL
LEVER_X = BTN_X + LEVER_ARM_BTN

BAR_BAY_MARGIN = 4.5
RECESS_C_BACK_Y = bezel_front + RECESS_TOP_C_D
FRONT_WALL_MIN = 2.5

# The pivot sits as far forward as it can without its bay breaking through
# into the front finger recess -- that would show the mechanism from
# outside. FRONT_WALL_MIN is the wall that has to survive.
LEVER_Y_MIN = (RECESS_C_BACK_Y + FRONT_WALL_MIN + BAR_BAY_MARGIN
             + FORK_REACH)
LEVER_Y = max(bezel_front + 20.0, LEVER_Y_MIN)
LEVER_T = 4.0   # lever thickness (Z)
PIVOT_R, PIVOT_FIT = 2.5, 0.2   # pivot rod radius, hole fit

LEVER_FLOAT = 0.3   # lever end float, so it turns freely
LEVER_GAP_BELOW = 1.2   # lever clears the bar below it
LEVER_Z0 = BAR_Z1 + LEVER_GAP_BELOW
LEVER_Z = LEVER_Z0 + LEVER_T/2


import math as _math


# The swing is centred on the mid-stroke, not run from one end. Same travel
# either way, but half the angle: the sweep shrinks and so does the slack
# everywhere else. With a yoke at both ends the reduction is exact --
# button travel = bar travel x b/a.
LEVER_THETA = _math.asin((BAR_TRAVEL / 2.0) / LEVER_ARM_BAR)
FORK_X_FREE = 5.0
FORK_X_PIVOT = 1.5
BTN_TRAVEL = BAR_TRAVEL * LEVER_ARM_BTN / LEVER_ARM_BAR

FORK_BAR_X_PIVOT = 2.0
FORK_BAR_X_FREE = 5.0

LEVER_W_MARGIN = 2.5
LEVER_W = 2 * (PIVOT_R + PIVOT_FIT) + 2 * LEVER_W_MARGIN

def _swept_bounds(x0, x1, half_w, t_min, t_max, steps=180):
    xs, ys = [], []
    for cx in (x0, x1):
        for cy in (-half_w, half_w):
            rho = _math.hypot(cx, cy)
            phi = _math.atan2(cy, cx)
            for i in range(steps + 1):
                t = t_min + (t_max - t_min) * i / steps
                xs.append(rho * _math.cos(phi + t))
                ys.append(rho * _math.sin(phi + t))
    return min(xs), max(xs), min(ys), max(ys)

LEVER_BODY_X0 = -(LEVER_ARM_BTN + BOSS_R)
LEVER_BODY_X1 = LEVER_ARM_BAR + BOSS_R
_ex0, _ex1, _ey0, _ey1 = _swept_bounds(LEVER_BODY_X0, LEVER_BODY_X1, max(LEVER_W / 2, BOSS_R),
                                         -LEVER_THETA, LEVER_THETA)
LEVER_SWEEP_CLR = 1.0
LEVER_SWEEP_X = (LEVER_X + _ex0 - LEVER_SWEEP_CLR, LEVER_X + _ex1 + LEVER_SWEEP_CLR)
LEVER_SWEEP_Y = (LEVER_Y + _ey0 - LEVER_SWEEP_CLR, LEVER_Y + _ey1 + LEVER_SWEEP_CLR)

BTN_EXIT_MARGIN = BTN_TRAVEL + 1.0

BOSS_BTN_X = LEVER_X - LEVER_ARM_BTN * _math.cos(LEVER_THETA)
BOSS_BTN_Y = LEVER_Y + LEVER_ARM_BTN * _math.sin(LEVER_THETA)
FORK_Z1 = LEVER_Z0 + LEVER_T + 0.6

FORK_BTN_Y0 = BOSS_BTN_Y - FORK_GAP/2 - FORK_WALL
FORK_BTN_Y1 = BOSS_BTN_Y + FORK_GAP/2 + FORK_WALL
BOSS_BAR_X   = LEVER_X + LEVER_ARM_BAR
BOSS_BAR_Y = LEVER_Y - BAR_TRAVEL / 2
FORK_BAR_Y0 = BOSS_BAR_Y - FORK_GAP/2 - FORK_WALL
FORK_BAR_Y1 = BOSS_BAR_Y + FORK_GAP/2 + FORK_WALL
FORK_BAR_X0 = BOSS_BAR_X - FORK_BAR_X_PIVOT
FORK_BAR_X1 = BOSS_BAR_X + FORK_BAR_X_FREE

BAR_ARM_Y0 = FORK_BAR_Y0

BTN_CLR_Y = 1.0
BTN_WEB_Y0 = front_y + BTN_TRAVEL + BTN_CLR_Y + 1.5

BTN_WEB_D = 6.0
BTN_WEB_Y1 = BTN_WEB_Y0 + BTN_WEB_D

BTN_WEB_BAY_Y = (BTN_WEB_Y0 - BTN_TRAVEL - BTN_CLR_Y,
                     BTN_WEB_Y1 + BTN_CLR_Y)
BTN_PROUD = 5.0
BTN_TIP_Y = bezel_front - BTN_PROUD

clear_scene()


# ============================================================
# 1) OUTER SHELL
# ============================================================
shell = box_range("Shell", (BODY_XL, BODY_XR), (-BODY_Y/2, BODY_Y/2), (0, BODY_Z))
bevel(shell, 0.5)

panel = box_range("panel",
                    (BODY_XL + BEZEL_INSET, BODY_XR - BEZEL_INSET),
                    (bezel_front, front_y + EMBED),
                    (BEZEL_INSET, BODY_Z - BEZEL_INSET))
bevel(panel, 1.2)
bool_op(shell, panel, 'UNION')

_POCKET_X_STL = ((3.0, 6.5), (81.5, 86.5))
_POCKET_Y_STL = (73.5, 77.0)
_disk_x0 = SLOT_CX - DISK_W/2
RET_POCKET_X = tuple((a + _disk_x0, b + _disk_x0) for a, b in _POCKET_X_STL)
RET_POCKET_Y = (DISK_TIP_Y - (DISK_D - _POCKET_Y_STL[0]),
             DISK_TIP_Y - (DISK_D - _POCKET_Y_STL[1]))

RET_CX = tuple((a + b) / 2 for a, b in RET_POCKET_X)
RET_CY = (RET_POCKET_Y[0] + RET_POCKET_Y[1]) / 2

RET_W = 6.6
RET_T = 0.8   # 2 perimeters exactly at 0.4 mm nozzle
RET_LEN = 20.0
RET_TIP_MARGIN = 4.0        # bump sits this far short of the free tip
RET_ARM = RET_LEN - RET_TIP_MARGIN   # the real bending length
RET_GAP = 0.8   # gap around the tongue on three sides
RET_RELIEF_Z0 = 14.0

RET_BUMP_H = 1.2   # must exceed the thinner disk's clearance
RET_BUMP_R0 = 1.5
RET_BUMP_R1 = 0.3
RET_BUMP_EMBED = 0.45

RET_Y0 = RET_CY - RET_ARM            # root
RET_Y1 = RET_CY + RET_TIP_MARGIN     # free tip

def _tongue_x(i):
    return (RET_CX[i] - RET_W/2, RET_CX[i] + RET_W/2)


# ============================================================
# 2) SPLITTING INTO BASE / PLATE / TOP
# ============================================================
# The top shell starts above the middle plate everywhere except at the
# front, where it reaches down to the parting line so the plate hides
# behind the bezel. That leaves a single visible seam on the front face,
# and it falls on the upper lip of the disk mouth.
BIG = 500.0
case_top = duplicate(shell, "Drive_Top")
case_base = shell
case_base.name = "Drive_Base"

bool_op(case_base, box("split_upper", (BODY_W+BIG, BODY_Y+BIG, BIG),
                        (0, 0, Z_SPLIT + BIG/2)))
bool_op(case_top, box_range("split_lower",
                            (-BIG, BIG), (PLATE_Y0, BIG),
                            (-BIG, PLATE_Z1)))
bool_op(case_top, box_range("split_lower_front",
                            (-BIG, BIG), (-BIG, PLATE_Y0),
                            (-BIG, Z_SPLIT)))


# The disk channel is cut FIRST: the retention bumps rise above its floor,
# so cutting it afterwards would shave them off.
bool_op(case_base, box_range("cut_slot",
                            (SLOT_CX - SLOT_W/2, SLOT_CX + SLOT_W/2),
                            (bezel_front - 2.0, SLOT_BACK),
                            (SLOT_FLOOR, slot_z1 + OVERSHOOT)))


# The shoes travel past the back of the disk channel, so the channel is
# extended for them -- but only in their two narrow bands, which leaves the
# back wall intact everywhere else.
for _sx in SHOE_X:
    bool_op(case_base, box_range("shoe_run",
                                 (_sx[0] - RUN_CLR, _sx[1] + RUN_CLR),
                                 (SLOT_BACK - 1.0,
                                  XBAR_Y1 + BAR_TRAVEL + RUN_CLR),
                                 (SLOT_FLOOR, slot_z1 + OVERSHOOT)))


# ------------------------------------------------------------
# DISK RETENTION
# ------------------------------------------------------------
# Two compliant tongues in the channel floor, each with a truncated cone
# that drops into one of the recesses on the back of the disk.
#
# The subtlety: the bump does not push the tongue down, it lifts the DISK.
# The disk rises until it meets the roof, and only the remainder bends the
# tongue -- so retention is governed by (bump height - vertical clearance),
# not by tongue stiffness alone. That is why the channel is kept tight and
# the bump made tall: a real disk is 0.3 mm thinner and with a generous
# channel it simply floats over the bump and is not retained at all.
#
# 45 deg all round, so it cams out with the same force it went in with.
# RET_ARM, not RET_LEN, is the bending length: the bump sits 4 mm short
# of the tip. Width is the one linear term here -- thickness and length are
# both cubed -- so it is the knob for small adjustments.
for _i in range(2):
    _rx = _tongue_x(_i)
    bool_op(case_base, box_range("ret_relief",
                                 (_rx[0] - RET_GAP, _rx[1] + RET_GAP),
                                 (RET_Y0, RET_Y1 + RET_GAP),
                                 (RET_RELIEF_Z0, SLOT_FLOOR - RET_T)))
    for _gx in ((_rx[0] - RET_GAP, _rx[0]), (_rx[1], _rx[1] + RET_GAP)):
        bool_op(case_base, box_range("ret_slit", _gx,
                                     (RET_Y0, RET_Y1 + RET_GAP),
                                     (SLOT_FLOOR - RET_T, slot_z1 + OVERSHOOT)))
    bool_op(case_base, box_range("ret_slit_end",
                                 (_rx[0] - RET_GAP, _rx[1] + RET_GAP),
                                 (RET_Y1, RET_Y1 + RET_GAP),
                                 (SLOT_FLOOR - RET_T, slot_z1 + OVERSHOOT)))
    _slope = (RET_BUMP_R0 - RET_BUMP_R1) / RET_BUMP_H
    bpy.ops.mesh.primitive_cone_add(
        vertices=32,
        radius1=RET_BUMP_R0 + RET_BUMP_EMBED * _slope,
        radius2=RET_BUMP_R1,
        depth=RET_BUMP_H + RET_BUMP_EMBED,
        location=(RET_CX[_i], RET_CY,
                  SLOT_FLOOR + (RET_BUMP_H - RET_BUMP_EMBED)/2))
    _bump = bpy.context.object
    _bump.name = "ret_bump"
    bool_op(case_base, _bump, 'UNION')


lip = box("lip", (SLOT_W, 3.0, 3.0), (SLOT_CX, bezel_front, slot_z1))
lip.rotation_euler[0] = math.radians(45)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
bool_op(case_top, lip)

def recess_above(name, x, depth, height):
    """Recess above the mouth, mirroring the one below: flat floor level
    with the mouth and a 45 deg ramp upward. It starts half a millimetre
    below the channel roof, i.e. inside an already empty volume."""
    y0, y1 = bezel_front - 1.0, bezel_front + depth
    z0 = slot_z1 - 0.5
    z_flat = z0 + height
    return prism_yz(name, x, [(y0, z0),
                              (y0, z_flat + depth + 1.0),
                              (y1, z_flat),
                              (y1, z0)])

bool_op(case_top, recess_above("cut_top_c", RECESS_C_X, RECESS_TOP_C_D, RECESS_TOP_C_H))
bool_op(case_top, recess_above("cut_top_l", RECESS_L_X, RECESS_TOP_LAT_D, RECESS_TOP_LAT_H))
bool_op(case_top, recess_above("cut_top_r", RECESS_R_X, RECESS_TOP_LAT_D, RECESS_TOP_LAT_H))
for _n, _bx, _f, _a in (("l", RECESS_L_X, RECESS_TOP_LAT_D, RECESS_TOP_LAT_H),
                        ("c", RECESS_C_X, RECESS_TOP_C_D, RECESS_TOP_C_H),
                        ("r", RECESS_R_X, RECESS_TOP_LAT_D, RECESS_TOP_LAT_H)):
    bool_op(case_base, recess_above(f"base_top_{_n}", _bx, _f, _a))


# ============================================================
# 3) TOP SHELL -- cutting the mechanism bays
# ============================================================
bool_op(case_top, box_range("bay_crossbar",
                            (XBAR_X[0] - RUN_CLR, XBAR_X[1] + RUN_CLR),
                            (BAR_Y_OUT - RUN_CLR,
                             XBAR_Y1 + BAR_TRAVEL + RUN_CLR),
                            (PLATE_Z1 - OVERSHOOT, BAR_Z1 + RUN_CLR)))

BAR_BAY_X = (min(BAR_X - BAR_W/2, FORK_BAR_X0) - RUN_CLR,
               max(BAR_X + BAR_W/2, FORK_BAR_X1) + RUN_CLR)
bool_op(case_top, box_range("bay_bar", BAR_BAY_X,
                            (BAR_ARM_Y0 - BAR_BAY_MARGIN,
                             XBAR_Y1 + BAR_TRAVEL + RUN_CLR),
                            (PLATE_Z1 - OVERSHOOT, MECH_Z_TOP)))
bool_op(case_top, box_range("bay_lever",
                            LEVER_SWEEP_X,
                            LEVER_SWEEP_Y,
                            (PLATE_Z1 - OVERSHOOT, MECH_Z_TOP)))

bool_op(case_top, box_range("bezel_button_slot",
                            (BTN_X - BTN_W/2 - BTN_CLR, BTN_X + BTN_W/2 + BTN_CLR),
                            (BTN_TIP_Y - BTN_EXIT_MARGIN, BTN_WEB_Y0 + 0.5),
                            (BTN_CAP_Z0 - RUN_CLR, BTN_CAP_Z1 + RUN_CLR)))
bool_op(case_top, box_range("bay_button_web",
                            (BTN_X - BTN_W/2 - BTN_CLR, BTN_X + BTN_W/2 + BTN_CLR),
                            BTN_WEB_BAY_Y,
                            (PLATE_Z1 - OVERSHOOT, BTN_CAP_Z1 + RUN_CLR)))
bool_op(case_top, box_range("bay_button_tram",
                            (BTN_X - BTN_W/2 - BTN_CLR, BTN_X + BTN_W/2 + BTN_CLR),
                            (BTN_WEB_Y1, FORK_BTN_Y1 + 2.0),
                            (PLATE_Z1 - OVERSHOOT, MECH_Z_TOP)))


# Blind sockets for the dowels and pilot holes for the screws.
for px, py in DOWELS:
    _z0, _z1 = PLATE_Z1 - OVERSHOOT, PLATE_Z1 + DOWEL_DEPTH_TOP
    bool_op(case_top, cyl_z(DOWEL_R + DOWEL_FIT_PRESS, _z1 - _z0,
                           (px, py, (_z0 + _z1)/2)))
for sx, sy in SCREWS:
    bool_op(case_top, cyl_z(M3_PILOT, OVERSHOOT + 10.0,
                           (sx, sy, Z_SPLIT - OVERSHOOT/2 + 5.0)))

ROD_R = 2.5
ROD_FIT = 0.15
ROD_DEPTH = 3.0   # blind depth in the top shell
_socket_z0 = MECH_Z_TOP - OVERSHOOT
_socket_z1 = MECH_Z_TOP + ROD_DEPTH
bool_op(case_top, cyl_z(ROD_R + ROD_FIT, _socket_z1 - _socket_z0,
                       (LEVER_X, LEVER_Y, (_socket_z0 + _socket_z1)/2)))

z_above = Z_SPLIT + OVERSHOOT

def recess_below(name, x, depth, top_z):
    """Recess below the mouth with a 45 deg sloped floor, taken from the
    original front panel. It runs above the part so its roof never
    coincides with the channel floor."""
    y0, y1 = bezel_front - 1.0, bezel_front + depth
    return prism_yz(name, x, [(y0, top_z - depth - 1.0),
                              (y0, z_above),
                              (y1, z_above),
                              (y1, top_z)])

bool_op(case_base, recess_below("cut_recess_c", RECESS_C_X, RECESS_C_D, RECESS_C_TOP))
bool_op(case_base, recess_below("cut_recess_l", RECESS_L_X, RECESS_LAT_D, RECESS_LAT_TOP))
bool_op(case_base, recess_below("cut_recess_r", RECESS_R_X, RECESS_LAT_D, RECESS_LAT_TOP))


# ============================================================
# 4) BASE -- NFC bay, cable gland, fasteners
# ============================================================
bool_op(case_base, box_range("cut_rebate",
                             (NFC_CX - NFC_COVER_W/2 - NFC_COVER_CLR, NFC_CX + NFC_COVER_W/2 + NFC_COVER_CLR),
                             (nfc_cy - NFC_COVER_D/2 - NFC_COVER_CLR, nfc_cy + NFC_COVER_D/2 + NFC_COVER_CLR),
                             (-OVERSHOOT, NFC_REBATE)))

_sx0, _sx1 = NFC_CX - NFC_COVER_W/2 - NFC_COVER_CLR, NFC_CX + NFC_COVER_W/2 + NFC_COVER_CLR
_sy0, _sy1 = nfc_cy - NFC_COVER_D/2 - NFC_COVER_CLR, nfc_cy + NFC_COVER_D/2 + NFC_COVER_CLR
for _gx, _gy in (((_sx0, _sx0 + NFC_GROOVE_W), (_sy0, _sy1)),
                 ((_sx1 - NFC_GROOVE_W, _sx1), (_sy0, _sy1)),
                 ((_sx0, _sx1), (_sy0, _sy0 + NFC_GROOVE_W)),
                 ((_sx0, _sx1), (_sy1 - NFC_GROOVE_W, _sy1))):
    bool_op(case_base, box_range("cut_groove", _gx, _gy,
                                 (NFC_REBATE, NFC_REBATE + NFC_GROOVE_H)))

for sx in (-NFC_SCREW_OFF, NFC_SCREW_OFF):
    for sy in (-NFC_SCREW_OFF, NFC_SCREW_OFF):
        bool_op(case_base, cyl_z(M3_PILOT, 8.0, (NFC_CX + sx, nfc_cy + sy, NFC_REBATE + 3.5)))

bool_op(case_base, box_range("cut_nfc", (NFC_CX - NFC_W/2, NFC_CX + NFC_W/2),
                             (nfc_cy - NFC_D/2, nfc_cy + NFC_D/2),
                             (-OVERSHOOT, NFC_REBATE + NFC_H)))

bool_op(case_base, box_range("cut_cable", (NFC_CX - CABLE_W/2, NFC_CX + CABLE_W/2),
                             (nfc_y0 + NFC_D - 5.0, back_y + OVERSHOOT),
                             (CABLE_Z0, CABLE_Z1)))

for sx, sy in SCREWS:
    bool_op(case_base, cyl_z(M3_CLR, Z_SPLIT + 2*OVERSHOOT, (sx, sy, Z_SPLIT/2)))
    countersink(case_base, (sx, sy), 0.0, upward=True)

for px, py in DOWELS:
    _z0, _z1 = Z_SPLIT - DOWEL_DEPTH_BASE, Z_SPLIT + OVERSHOOT

disk_cy = (DISK_REAR_Y + DISK_D/2 if SHOW_DISK_INSERTED
           else bezel_front - 14.0 - DISK_D/2)

# ============================================================
# 5) REFERENCE DISK -- clearance check only, not a part
# ============================================================
disk = box("Reference_Disk", (DISK_W, DISK_D, DISK_T),
                (SLOT_CX, disk_cy, DISK_ZMID))
chamf = box("x", (DISK_W + 2, 3.4, 3.4),
            (SLOT_CX, disk_cy - DISK_D/2, DISK_ZMID + DISK_T/2))
chamf.rotation_euler[0] = math.radians(45)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
bool_op(disk, chamf)


# ============================================================
# 6) Push_Bar -- the bar the disk pushes
# ============================================================
# A T: a long arm to the lever, a crossbar at the back, and two shoes
# hanging through the plate into the disk channel. It rests flat on the
# middle plate, so it cannot sag.
bar = box_range("Bar_arm",
                   (BAR_X - BAR_W/2, BAR_X + BAR_W/2),
                   (BAR_ARM_Y0, XBAR_Y1),
                   (BAR_Z0, BAR_Z1))

bool_op(bar, box_range("Bar_crossbar",
                          XBAR_X,
                          (XBAR_Y0, XBAR_Y1),
                          (BAR_Z0, BAR_Z1)), 'UNION')

for _sx in SHOE_X:
    bool_op(bar, box_range("Bar_shoe", _sx,
                              (BAR_Y_OUT, XBAR_Y1),
                              (SHOE_Z0, BAR_Z1)), 'UNION')

for _fy in ((FORK_BAR_Y0, FORK_BAR_Y0 + FORK_WALL),
            (FORK_BAR_Y1 - FORK_WALL, FORK_BAR_Y1)):
    bool_op(bar, box_range("Bar_fork",
                              (FORK_BAR_X0, FORK_BAR_X1),
                              _fy, (BAR_Z0, FORK_Z1)), 'UNION')
bevel(bar, 0.6, 2)

bar.name = "Push_Bar"


# ============================================================
# 7) Eject_Lever -- the lever
# ============================================================
# A rectangle from one boss center to the other, with a round boss at each
# end. Beyond the boss centres there are no square corners, only the boss
# profile, which is what lets the forks reach in without fouling.
#
# The pivot hole is cut LAST. The button-side boss is only 7 mm from the
# pivot and would otherwise fill part of the hole, and the lever would not
# go onto its rod at all.
lever = box_range("Eject_Lever",
                     (LEVER_X - LEVER_ARM_BTN, LEVER_X + LEVER_ARM_BAR),
                     (LEVER_Y - LEVER_W/2, LEVER_Y + LEVER_W/2),
                     (LEVER_Z0, LEVER_Z0 + LEVER_T))
bevel(lever, 0.5, 2)
_cut_h = LEVER_T + 4.0
bool_op(lever, cyl_z(BOSS_R, LEVER_T,
                       (LEVER_X + LEVER_ARM_BAR, LEVER_Y, LEVER_Z)), 'UNION')
bool_op(lever, cyl_z(BOSS_R, LEVER_T, (LEVER_X - LEVER_ARM_BTN, LEVER_Y, LEVER_Z)), 'UNION')

bool_op(lever, cyl_z(PIVOT_R + PIVOT_FIT, _cut_h, (LEVER_X, LEVER_Y, LEVER_Z)))
lever.name = "Eject_Lever"

rotate_mesh(lever, -LEVER_THETA, 'Z', (LEVER_X, LEVER_Y, LEVER_Z))


# ============================================================
# 8) Front_Button -- the button
# ============================================================
# Cap, a web up to the mechanism level, a tram back to the fork. The two
# concave corners are chamfered because there is no straight path that
# gets the part into its bay -- it has to go in turning, and turning, the
# outer corners are what foul.
button = box_range("Button_cap",
                  (BTN_X - BTN_W/2, BTN_X + BTN_W/2),
                  (BTN_TIP_Y, BTN_WEB_Y0 + 0.5),
                  (BTN_CAP_Z0, BTN_CAP_Z1))
web = box_range("Button_web",
                   (BTN_X - BTN_W/2, BTN_X + BTN_W/2),
                   (BTN_WEB_Y0, BTN_WEB_Y1),
                   (BAR_Z0, BTN_CAP_Z1))
bool_op(button, web, 'UNION')
BTN_TRAM_X = (BTN_X - BTN_W/2, BTN_X + BTN_W/2 - 2.5)
tram = box_range("Button_tram", BTN_TRAM_X,
                    (BTN_WEB_Y1, FORK_BTN_Y1),
                    (BAR_Z0, BAR_Z1))
bool_op(button, tram, 'UNION')

for _fy in ((FORK_BTN_Y0, FORK_BTN_Y0 + FORK_WALL),
            (FORK_BTN_Y1 - FORK_WALL, FORK_BTN_Y1)):
    bool_op(button, box_range("Button_fork",
                             (BOSS_BTN_X - FORK_X_FREE, BOSS_BTN_X + FORK_X_PIVOT),
                             _fy, (BAR_Z0, FORK_Z1)), 'UNION')

BTN_CHAMF = 1.5
BTN_CHAMF_TOP = 4.0
BTN_END_Y = FORK_BTN_Y1
bool_op(button, prism_yz("Button_chamf", (BTN_TRAM_X[0] - 1.0, BTN_TRAM_X[1] + 1.0),
                        [(BTN_END_Y + 1.0, BAR_Z0 - 1.0),
                         (BTN_END_Y + 1.0, BAR_Z0 + BTN_CHAMF),
                         (BTN_END_Y - BTN_CHAMF, BAR_Z0 - 1.0)]))
CHAMF_M = 1.0
bool_op(button, prism_yz("Button_chamf_top", (BTN_X - BTN_W/2 - OVERSHOOT, BTN_X + BTN_W/2 + OVERSHOOT),
                        [(BTN_WEB_Y1 - BTN_CHAMF_TOP - OVERSHOOT, BTN_CAP_Z1 + OVERSHOOT),
                         (BTN_WEB_Y1 + CHAMF_M,             BTN_CAP_Z1 + OVERSHOOT),
                         (BTN_WEB_Y1 + CHAMF_M,             BTN_CAP_Z1 - BTN_CHAMF_TOP - CHAMF_M)]))
button.name = "Front_Button"


# ============================================================
# 9) Mech_Plate -- the middle plate
# ============================================================
# Slots for the shoes, clearance for the screws and dowels, and a tower
# that both houses the lower end of the pivot rod and gives the lever
# something to rest on. The front edge takes the same recess cuts as the
# shells, so it follows the bezel exactly instead of showing through it.
plate = box_range("Mech_Plate",
                      (PLATE_X[0], PLATE_X[1]),
                      (PLATE_Y0, back_y),
                      (PLATE_Z0, PLATE_Z1))

for _sx in SHOE_X:
    bool_op(plate, box_range("plate_shoe_slot",
                                 (_sx[0] - RUN_CLR, _sx[1] + RUN_CLR),
                                 (BAR_Y_OUT - RUN_CLR,
                                  XBAR_Y1 + BAR_TRAVEL + RUN_CLR),
                                 (PLATE_Z0 - OVERSHOOT, PLATE_Z1 + OVERSHOOT)))

for _sx, _sy in SCREWS:
    bool_op(plate, cyl_z(M3_CLR, PLATE_T + 2*OVERSHOOT, (_sx, _sy, PLATE_Z0)))
for _px, _py in DOWELS:
    bool_op(plate, cyl_z(DOWEL_R + DOWEL_FIT_SLIDE, PLATE_T + 2*OVERSHOOT,
                            (_px, _py, PLATE_Z0)))

PIVOT_TOWER_R = 5.0
PIVOT_TOWER_Z1 = LEVER_Z0 - LEVER_FLOAT
PLATE_FLOOR_T = 0.6
_rod_hole_z0 = PLATE_Z0 + PLATE_FLOOR_T
bool_op(plate, cyl_z(PIVOT_TOWER_R, PIVOT_TOWER_Z1 - PLATE_Z0,
                        (LEVER_X, LEVER_Y, (PLATE_Z0 + PIVOT_TOWER_Z1)/2)), 'UNION')
bool_op(plate, cyl_z(ROD_R + ROD_FIT, (PIVOT_TOWER_Z1 + OVERSHOOT) - _rod_hole_z0,
                        (LEVER_X, LEVER_Y, (_rod_hole_z0 + PIVOT_TOWER_Z1 + OVERSHOOT)/2)))

for _tag, _bx, _depth, _height in (("l", RECESS_L_X, RECESS_TOP_LAT_D, RECESS_TOP_LAT_H),
                               ("c", RECESS_C_X, RECESS_TOP_C_D, RECESS_TOP_C_H),
                               ("r", RECESS_R_X, RECESS_TOP_LAT_D, RECESS_TOP_LAT_H)):
    bool_op(plate, recess_above(f"plate_notch_{_tag}", _bx, _depth, _height))
bevel(plate, 0.4, 2)
plate.name = "Mech_Plate"

ROD_Z0 = _rod_hole_z0
ROD_Z1 = MECH_Z_TOP + ROD_DEPTH

# ============================================================
# 10) Lever_Rod -- the pivot rod
# ============================================================
# Held blind in the top shell and captured by the plate's tower, so it is
# supported at both ends instead of cantilevered. As a separate part it
# prints lying down, with the layers along the axis rather than across the
# bending load -- roughly 45 MPa instead of 25. It moulded into the shell
# before, and it broke. A length of 5 mm steel rod works just as well.
rod = cyl_z(ROD_R, ROD_Z1 - ROD_Z0, (BODY_XR + 30.0, 0.0, (ROD_Z0 + ROD_Z1)/2))
rod.name = "Lever_Rod"

nfc_cover_px = BODY_XR + NFC_COVER_W/2 + 20.0

# ============================================================
# 11) NFC_Cover -- reader bay cover
# ============================================================
nfc_cover = box("NFC_Cover", (NFC_COVER_W, NFC_COVER_D, NFC_COVER_T), (nfc_cover_px, nfc_cy, NFC_COVER_T/2))
for sx in (-NFC_SCREW_OFF, NFC_SCREW_OFF):
    for sy in (-NFC_SCREW_OFF, NFC_SCREW_OFF):
        bool_op(nfc_cover, cyl_z(M3_CLR, NFC_COVER_T + 2.0,
                            (nfc_cover_px + sx, nfc_cy + sy, NFC_COVER_T/2)))
        countersink(nfc_cover, (nfc_cover_px + sx, nfc_cy + sy), 0.0, upward=True)

GLAND_Y1 = back_y
GLAND_Y0 = back_y - GLAND_D

def gland_half(name, z0, z1):
    part = box_range(name, (NFC_CX - CABLE_W/2 + GLAND_CLR,
                            NFC_CX + CABLE_W/2 - GLAND_CLR),
                      (GLAND_Y0, GLAND_Y1), (z0, z1))
    bool_op(part, cyl_y(GLAND_BORE_R, (GLAND_Y1 - GLAND_Y0) + 4.0,
                        (NFC_CX, (GLAND_Y0 + GLAND_Y1)/2, CABLE_ZMID)))
    return part

gland_lower = gland_half("Gland_Lower", CABLE_Z0, CABLE_ZMID)
gland_upper = gland_half("Gland_Upper", CABLE_ZMID, CABLE_Z1)

COUPON_DX = BODY_XR + 40.0
COUPON_X = (-43.0, -26.0)
COUPON_Y = (0.0, 42.0)
COUPON_Z = (RET_RELIEF_Z0 - 1.0, PLATE_Z0 + 3.0)


# ============================================================
# 13) Retention_Coupon -- test coupon, not part of the drive
# ============================================================
# A slice of the disk channel with one tongue, at the real dimensions and
# with the channel roof at the real height -- which is the part that
# matters, since retention depends on how much vertical clearance the disk
# has. About 7 g. Slide a disk in from the low-Y end until it clicks.
coupon = box_range("Retention_Coupon",
                      (COUPON_X[0] + COUPON_DX, COUPON_X[1] + COUPON_DX),
                      COUPON_Y, COUPON_Z)
bool_op(coupon, box_range("coupon_slot",
                             (SLOT_CX - SLOT_W/2 + COUPON_DX, COUPON_X[1] + COUPON_DX + OVERSHOOT),
                             (COUPON_Y[0] - OVERSHOOT, COUPON_Y[1] + OVERSHOOT),
                             (SLOT_FLOOR, slot_z1)))
_rx = (RET_CX[0] - RET_W/2 + COUPON_DX, RET_CX[0] + RET_W/2 + COUPON_DX)
bool_op(coupon, box_range("coupon_relief",
                             (_rx[0] - RET_GAP, _rx[1] + RET_GAP),
                             (RET_Y0, RET_Y1 + RET_GAP),
                             (RET_RELIEF_Z0, SLOT_FLOOR - RET_T)))
for _gx in ((_rx[0] - RET_GAP, _rx[0]), (_rx[1], _rx[1] + RET_GAP)):
    bool_op(coupon, box_range("coupon_slit", _gx,
                                 (RET_Y0, RET_Y1 + RET_GAP),
                                 (SLOT_FLOOR - RET_T, slot_z1 + OVERSHOOT)))
bool_op(coupon, box_range("coupon_slit_end",
                             (_rx[0] - RET_GAP, _rx[1] + RET_GAP),
                             (RET_Y1, RET_Y1 + RET_GAP),
                             (SLOT_FLOOR - RET_T, slot_z1 + OVERSHOOT)))
_slope = (RET_BUMP_R0 - RET_BUMP_R1) / RET_BUMP_H
bpy.ops.mesh.primitive_cone_add(
    vertices=32, radius1=RET_BUMP_R0 + RET_BUMP_EMBED * _slope,
    radius2=RET_BUMP_R1, depth=RET_BUMP_H + RET_BUMP_EMBED,
    location=(RET_CX[0] + COUPON_DX, RET_CY,
              SLOT_FLOOR + (RET_BUMP_H - RET_BUMP_EMBED)/2))
bool_op(coupon, bpy.context.object, 'UNION')
coupon.name = "Retention_Coupon"


# ============================================================
# 14) Guide_Dowel -- alignment dowel (x2)
# ============================================================
# Print lying down. Two lengths of 4 mm steel rod will also do.
dowel = cyl_z(DOWEL_R, DOWEL_LEN, (BODY_XR + 60.0, 0.0, DOWEL_LEN/2))
dowel.name = "Guide_Dowel"