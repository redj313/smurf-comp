# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
import bpy.path as bpath
import os.path as opath
from bpy.props import StringProperty, PointerProperty
from bpy.types import Panel, Operator, PropertyGroup

bl_info = {
    "name": "Smurfs Tools",
    "description": "Basic Proxy tool for Compositor"
    "Node Wrangler addon must be activated",
    "author": "Regis Gobbin, Vincent Gires",
    "version": (0, 1, 2),
    "blender": (4, 0, 2),
    "location": "Compositor > Properties Panel > Node",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Node",
}

# ------------------------------------------------------------
# Properties
# ------------------------------------------------------------


class SmurfProps(PropertyGroup):
    suf1: StringProperty(
        name="A",
        description=(
            "Suffix used in the filenames of your currently "
            "loaded images (i.e. your low def proxy)"),
        default="_lodef",
        maxlen=1024)
    suf2: StringProperty(
        name="B",
        description=(
            "Suffix used in the filenames of your alternate "
            "images (i.e. your high def image)"),
        default="_hidef",
        maxlen=1024)

# -------------------------------------------------------------
# Fonctions
# -------------------------------------------------------------


def switch_suffix(nodes_selec, a, b):
    switched_nodes = []
    for node in nodes_selec:
        if not node.image:
            continue
        node.image.filepath = node.image.filepath.replace(a, b)
        node.image.name = node.image.name.replace(a, b)
        switched_nodes.append(node)
    if switched_nodes:
        print("Switched " + str(len(switched_nodes)) + " images")
    return switched_nodes


def transfer_img_res(image, scene, self):
    # Thanks to Vincent Gires for the following hack!
    if image.type == 'MULTILAYER':
        # HACK to get the resolution of a multilayer EXR through movieclip
        movieclip = bpy.data.movieclips.load(image.filepath)
        x, y = movieclip.size
        bpy.data.movieclips.remove(movieclip)
    else:
        x, y = image.size

    if scene.render.resolution_x == x and scene.render.resolution_y == y:
        self.report({'INFO'}, "Resolution already matching")
        print(f"Image and Render have same dimensions: {x} by {y}")

    else:
        # Passes the image's resolution to render resolution
        scene.render.resolution_x = x
        scene.render.resolution_y = y
        self.report({'INFO'}, "Render size changed")
        print(f"Render size set to {x} by {y}")


def get_image_nodes_to_switch(scene, a, b):
    if not scene.use_nodes:
        return
    nodes = [n for n in scene.node_tree.nodes if n.type == 'IMAGE']
    available_nodes = []
    for node in nodes:
        if a in bpath.basename(node.image.filepath):
            nodepath = bpath.abspath(node.image.filepath).replace(a, b)
            if opath.isfile(nodepath):
                available_nodes.append(node)
    return available_nodes


# -------------------------------------------------------------
# OPERATORS
# -------------------------------------------------------------

class SM_OT_SmurfSwitch1(Operator):
    bl_label = "Switch A --> B"
    bl_idname = "sm.smurfab"
    bl_description = "Replaces string A with string B in the image "
    "filename (to load an alternate version)"

    @classmethod
    def poll(cls, context):
        """Checks if the string to be replaced (A) is contained
        in any of the images' filepath, and if the potential outcome
        of switching it to B would point to an existing file.
        """
        scene = context.scene
        smurf = scene.smurf
        return get_image_nodes_to_switch(scene, smurf.suf1, smurf.suf2)

    def execute(self, context):
        scene = context.scene
        suf1 = scene.smurf.suf1
        suf2 = scene.smurf.suf2
        nodes_selec = get_image_nodes_to_switch(scene, suf1, suf2)
        #get_image_nodes_to_switch(scene, smurf.suf1, smurf.suf2)
        switched_nodes = switch_suffix(nodes_selec, suf1, suf2)
        #switch_suffix(context, nodes_selec, smurf.suf1, smurf.suf2)
        self.report({'INFO'}, f"Switched {(len(switched_nodes))} images")
        return {'FINISHED'}


class SM_OT_SmurfSwitch2(Operator):
    bl_label = "Switch B --> A"
    bl_idname = "sm.smurfba"
    bl_description = "Replaces string B with string A in the image filename"

    @classmethod
    def poll(cls, context):
        """Checks if the string to be replaced (B) is contained in any of the
        image's filepath, and if the potential outcome of switching it to A
        would point to an existing file.
        """
        scene = context.scene
        smurf = scene.smurf
        return get_image_nodes_to_switch(scene, smurf.suf2, smurf.suf1)

    def execute(self, context):
        scene = context.scene
        suf1 = scene.smurf.suf1
        suf2 = scene.smurf.suf2
        nodes_selec = get_image_nodes_to_switch(scene, suf2, suf1)
        switched_nodes = switch_suffix(nodes_selec, suf2, suf1)
        self.report({'INFO'}, f"Switched {(len(switched_nodes))} images")
        return {'FINISHED'}


class SM_OT_TransferImageRes(Operator):
    bl_label = "Set Resolution From Active"
    bl_idname = "sm.smurfimgres"
    bl_description = (
        "Automatically sets the render resolution from the active image node")

    @classmethod
    def poll(cls, context):
        if not context.scene.use_nodes:
            return
        tree = context.scene.node_tree
        # This operator will only be active if the active node is an image node
        # with an image loaded.
        if tree.nodes.active:
            if tree.nodes.active.type == 'IMAGE':
                return tree.nodes.active.image

    def execute(self, context):
        scene = context.scene
        tree = scene.node_tree
        transfer_img_res(tree.nodes.active.image, scene, self)
        return {'FINISHED'}

class SM_OT_SmurfSet2K(Operator):
    bl_label = "Set to 2K"
    bl_idname = "sm.smurf2k"
    bl_description = "Sets render resolution to 2K square"

    def execute(self, context):
        bpy.context.scene.render.resolution_x = 2048
        bpy.context.scene.render.resolution_y = 2048
        print(f"Render size set to 2048 square")
        return {'FINISHED'}
    
class SM_OT_SmurfSet8K(Operator):
    bl_label = "Set to 8K"
    bl_idname = "sm.smurf8k"
    bl_description = "Sets render resolution to 8K square"

    def execute(self, context):
        bpy.context.scene.render.resolution_x = 8192
        bpy.context.scene.render.resolution_y = 8192
        print(f"Render size set to 8192 square")
        return {'FINISHED'}


# --------------------------------------------------------------
# INTERFACE
# --------------------------------------------------------------


class SmurfPanel(bpy.types.Panel):
    bl_label = "Smurfs Tools"
    bl_idname = "NODE_PT_smurfs"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = "UI"
    bl_category = "Node"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        smurf = scene.smurf
        rd = scene.render

        layout.label(text="Proxy Image Switch")

        layout.prop(smurf, "suf1")
        layout.prop(smurf, "suf2")

        row = layout.row(align=True)

        row.operator(SM_OT_SmurfSwitch1.bl_idname, icon='LOOP_FORWARDS')
        row.operator(SM_OT_SmurfSwitch2.bl_idname, icon='LOOP_BACK')

        col = layout.column(align=True)

        col.separator()
        # The following operator is from the Node Wrangler addon.
        # It has to be activated obviously.
        col.operator(
            bpy.types.NODE_OT_nw_reload_images.bl_idname, icon='FILE_REFRESH')

        col.separator()
        layout.label(text="Image Resolution")
        col.separator()
        
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align=True)
        col.prop(rd, "resolution_x", text="X")
        col.prop(rd, "resolution_y", text="Y")
        col.prop(rd, "resolution_percentage", text="%")

        row = layout.row(align=True)
        
        row.operator(SM_OT_SmurfSet2K.bl_idname, icon='RENDER_RESULT')
        row.operator(SM_OT_SmurfSet8K.bl_idname, icon='RENDER_RESULT')
        
        col = layout.column(align=True)

        col.operator(SM_OT_TransferImageRes.bl_idname, icon='NODE_SEL')


class ColorManagement(bpy.types.Panel):
    """Duplicate of the same panel from render properties
    handy to access it from here."""
    bl_label = "Color Management"
    bl_idname = "NODE_PT_color_management"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = "UI"
    bl_category = "Node"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        scene = context.scene
        view = scene.view_settings

        flow = layout.grid_flow(
            row_major=True, columns=0,
            even_columns=False, even_rows=False, align=True)

        col = flow.column()
        col.prop(scene.display_settings, "display_device")

        col.separator()

        col.prop(view, "view_transform")
        col.prop(view, "look")

        col = flow.column()
        col.prop(view, "exposure")
        col.prop(view, "gamma")

        col.separator()

# --------------------------------------------------------------
# REGISTER
# --------------------------------------------------------------


classes = (
    SM_OT_SmurfSwitch1,
    SM_OT_SmurfSwitch2,
    SM_OT_TransferImageRes,
    SM_OT_SmurfSet2K,
    SM_OT_SmurfSet8K,
    SmurfProps,
    SmurfPanel,
    ColorManagement,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.smurf = PointerProperty(type=SmurfProps)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.smurf


if __name__ == "__main__":
    register()
