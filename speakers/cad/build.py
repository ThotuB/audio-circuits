import build123d as bld
import yacv_server as server

width, depth, height = 146, 232, 280  # mm, outer dimensions
wall_front = 18  # mm, front wall thickness (holds the drivers)
wall_side = 14  # mm, top/bottom/left/right/back wall thickness
fillet_radius = 6  # mm, vertical corner rounding

top_hole_radius = 40  # mm
top_recess_radius = 52  # mm
top_edge_gap = 25  # mm, from top edge to edge of hole
top_hole_z = height / 2 - (top_edge_gap + top_hole_radius)

bottom_hole_radius = 57  # mm
bottom_recess_radius = 66  # mm
bottom_edge_gap = 36  # mm, from bottom edge to edge of hole
bottom_hole_z = -(height / 2 - (bottom_edge_gap + bottom_hole_radius))

front_y = -depth / 2


def rounded_box(w: float, d: float, h: float, radius: float) -> bld.Part:
    box = bld.Box(w, d, h)
    if radius <= 0:
        return box
    return bld.fillet(box.edges().filter_by(bld.Axis.Z), radius=radius)


outer = rounded_box(width, depth, height, fillet_radius)

# front wall is thicker than the rest, so the cavity is offset toward the back
# the cavity itself stays square - only the outer shell is rounded
inner_depth = depth - wall_front - wall_side
inner_center_y = (wall_front - wall_side) / 2
inner = bld.Box(width - 2 * wall_side, inner_depth, height - 2 * wall_side)
inner = bld.Pos(0, inner_center_y, 0) * inner

hollow = outer - inner  # empty inside, 18mm front wall, 14mm elsewhere


def cyl_along_y(radius: float, length: float, y_center: float, z: float) -> bld.Part:
    cylinder = bld.Cylinder(radius=radius, height=length)
    cylinder = bld.Rotation(X=90) * cylinder
    return bld.Pos(0, y_center, z) * cylinder


def driver_hole(z: float, hole_radius: float, recess_radius: float) -> bld.Part:
    # full through-hole plus a recess cut halfway into the front wall thickness
    through = cyl_along_y(hole_radius, wall_front + 40, front_y, z)
    recess = cyl_along_y(recess_radius, wall_front / 2, front_y + wall_front / 4, z)
    return through + recess


top_hole = driver_hole(top_hole_z, top_hole_radius, top_recess_radius)
bottom_hole = driver_hole(bottom_hole_z, bottom_hole_radius, bottom_recess_radius)

port_width = 118  # mm, overall width, including the rounded ends
port_height = 10  # mm, also the diameter of the rounded ends (radius 5)
port_bottom_gap = 14  # mm, from bottom edge to bottom of the port
port_z = -height / 2 + port_bottom_gap + port_height / 2


def slot_along_y(w: float, h: float, length: float, y_center: float, z: float) -> bld.Part:
    plane = bld.Plane.XZ.offset(-y_center)
    slot = plane * bld.SlotOverall(w, h)
    port = bld.extrude(slot, amount=length / 2, both=True)
    return bld.Pos(0, 0, z) * port


port_hole = slot_along_y(port_width, port_height, wall_front + 40, front_y, port_z)

speaker = hollow - top_hole - bottom_hole - port_hole

# round over the port's outer rim (where it meets the front face)
port_round_radius = 2.5  # mm
port_rim_edges = [
    e
    for e in speaker.edges()
    if abs(e.bounding_box().min.Y - front_y) < 1e-3
    and abs(e.bounding_box().max.Y - front_y) < 1e-3
    and abs(e.bounding_box().center().Z - port_z) < port_height
]
speaker = bld.fillet(port_rim_edges, radius=port_round_radius)

# internal brace, between the port and the bottom driver hole
port_top_z = port_z + port_height / 2
bottom_hole_bottom_z = bottom_hole_z - bottom_hole_radius
brace_height = bottom_hole_bottom_z - port_top_z
brace_center_z = (port_top_z + bottom_hole_bottom_z) / 2

inner_front_y = inner_center_y - inner_depth / 2
brace_depth = inner_depth * 2 / 3
brace_center_y = inner_front_y + brace_depth / 2

brace_width = width - 2 * wall_side  # full inner cavity width
brace = bld.Box(brace_width, brace_depth, brace_height)
brace = bld.Pos(0, brace_center_y, brace_center_z) * brace

# middle support, between the two drivers - hollow frame, 18mm wall all around
support_height = 12  # mm
support_wall = 18  # mm
top_hole_bottom_z = top_hole_z - top_hole_radius
support_top_z = top_hole_bottom_z
support_bottom_z = support_top_z - support_height
support_center_z = (support_top_z + support_bottom_z) / 2

support_outer = bld.Box(brace_width, inner_depth, support_height)
support_inner = bld.Box(
    brace_width - 2 * support_wall, inner_depth - 2 * support_wall, support_height
)
support = support_outer - support_inner
support = bld.Pos(0, inner_center_y, support_center_z) * support

cavity = inner - brace - support

# tunnel: same footprint as the brace, but extended down to the bottom of the speaker
tunnel_top_z = brace_center_z + brace_height / 2
tunnel_bottom_z = -height / 2
tunnel_height = tunnel_top_z - tunnel_bottom_z
tunnel_center_z = (tunnel_top_z + tunnel_bottom_z) / 2
tunnel = bld.Box(brace_width, brace_depth, tunnel_height)
tunnel = bld.Pos(0, brace_center_y, tunnel_center_z) * tunnel

cavity_sealed = cavity - tunnel

cavity = bld.Pos(width + 50, 0, 0) * cavity  # shifted aside, just for viewing next to the speaker
cavity_sealed = bld.Pos(2 * (width + 50), 0, 0) * cavity_sealed  # shifted further aside

print(f"Outer volume: {outer.volume / 1000:.1f} cm^3 ({outer.volume / 1_000_000:.3f} L)")
print(f"Cavity volume: {cavity.volume / 1000:.1f} cm^3 ({cavity.volume / 1_000_000:.3f} L)")
print(f"Cavity volume (sealed): {cavity_sealed.volume / 1000:.1f} cm^3 ({cavity_sealed.volume / 1_000_000:.3f} L)")

print("Starting server on... http://localhost:32323")
server.show(speaker, brace, support, cavity, cavity_sealed)
