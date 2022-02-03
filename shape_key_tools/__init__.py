# ////////////////////////////////////////////////////////////////////////////////////////////////////
# //
# //    Shape Key Tools for Blender 2.79
# //    - Split/merge shape keys pairs (e.g. MyShapeKeyL+MyShapeKeyR) into left and right halves
# //    - Merge any two arbitrary shape keys with various blending modes
# //    - Split filtered deltas off from one shape key to form a new shape key
# //    - Apply modifiers to meshes with shape keys
# //
# ////////////////////////////////////////////////////////////////////////////////////////////////////

bl_info = {
	"name": "Shape Key Tools",
	"author": "TiberiumFusion",  
	"version": (2, 1, 0, 0),
	"blender": (2, 78, 0), # This is a guess... I think it was 2.77 or 2.78 that added some of the operators/api we need. Definitely no earlier than 2.75, since that is when support for custom icons was added.
	"location": "Object > Tools > Shape Key Tools",
	"description": "Tools for working with shape keys beyond Blender's limited abilities.",
	"wiki_url": "https://github.com/TiberiumFusion/BlenderShapeKeyTools",
	"tracker_url": "https://github.com/TiberiumFusion/BlenderShapeKeyTools/issues",
	"warning": "",
	"category": "Tools",
}

import sys, os, imp, types
from types import SimpleNamespace

import bpy, bpy.utils.previews
from bpy.props import *


# Container of our custom icons
UiIconsExtra = None

# Dictionary of registered operators, mapped by their Blender ID (e.g. "wm.shape_key_tools_split_active_pair")
RegisteredOps = {}



#
#====================================================================================================
#    Top level properties
#====================================================================================================
#

class ShapeKeyTools_Properties(bpy.types.PropertyGroup):
	
	### Gui glue
	opt_gui_subpanel_expander_globalopts = BoolProperty(name="Global Options", default=False, description="These options are shared by all operations, but some operations may not use them. Read each operation's tooltip for more info!")
	opt_gui_subpanel_expander_shapepairs = BoolProperty(name="Split/Merge Pairs", default=True, description="Operations for splitting and merging shape key pairs (i.e. symmetrical shape keys, like facial expressions)")
	opt_gui_subpanel_expander_shapepairsopts = BoolProperty(name="Split/Merge Pairs Options", default=True, description="These options ONLY affect the 4 operations below")
	opt_gui_subpanel_expander_arbitrary = BoolProperty(name="Arbitrary Split/Merge Operations", default=True, description="General purpose split & merge operations")
	opt_gui_subpanel_expander_modifiers = BoolProperty(name="Modifer Operations", default=True, description="Operations involving shape keys and modifiers")
	
	### Global options for all ops
	opt_global_enable_filterverts = BoolProperty(
		name = "Vertex Filter",
		description = "Filter shape key vertices by comparing them with the conditions below. Vertices that pass ALL conditions are considered RED. All other vertices are considered BLACK. Each operation may treat RED and BLACK vertices DIFFERENTLY, so read every tooltip!",
		default = False,
	)
	
	opt_global_filterverts_distance_min_enable = BoolProperty(
		name = "Enable Minimum Delta",
		description = "Enables the 'Minimum Delta' filter condition",
		default = False,
	)
	opt_global_filterverts_distance_min = FloatProperty(
		name = "Minimum Delta",
		description = "Vertex delta (difference in position from basis shape key) must be at least this distance (in local object space). By setting this to a low value, such as 0.1, you can filter out vertices with imperceptible deltas",
		min = 0.0,
		soft_min = 0.0,
		soft_max = 100.0,
		default = 0.1,
		precision = 6,
		step = 1,
		subtype = 'DISTANCE',
		unit = 'LENGTH',
	)
	
	opt_global_filterverts_distance_max_enable = BoolProperty(
		name = "Enable Maximum Delta",
		description = "Enables the 'Maximum Delta' filter condition",
		default = False,
	)
	opt_global_filterverts_distance_max = FloatProperty(
		name = "Maximum Delta",
		description = "Vertex delta (difference in position from basis shape key) must be no greater than this distance (in local object space). By setting this to a high value, such as 50, you can filter out vertices with extreme deltas",
		min = 0.0,
		soft_min = 0.0,
		soft_max = 10000.0,
		default = 10000.0,
		precision = 6,
		step = 1,
		subtype = 'DISTANCE',
		unit = 'LENGTH',
	)
	
	opt_global_filterverts_vertexgroup_latestitems = None
	def getActiveObjectVertexGroups(self, context):
		vertexGroupsOrdered = []
		for vg in context.object.vertex_groups:
			vertexGroupsOrdered.append((vg.index, vg.name))
		def s(v):
			return v[0]
		vertexGroupsOrdered.sort(key=s)
		opt_global_filterverts_vertexgroup_latestitems = [(str(tuple[0]), tuple[1], tuple[1], "GROUP_VERTEX", tuple[0]) for tuple in vertexGroupsOrdered]
		return opt_global_filterverts_vertexgroup_latestitems
	opt_global_filterverts_vertexgroup_enable = BoolProperty(
		name = "Enable Vertex Group",
		description = "Enables the 'Vertex Group' filter condition",
		default = False,
	)
	opt_global_filterverts_vertexgroup = EnumProperty(
		name = "Vertex Group",
		description = "Vertex must belong to the specified vertex group",
		items = getActiveObjectVertexGroups,
	)
	
	# Creates a dictionary with the values of only the ENABLED vertex filter params
	def getEnabledVertexFilterParams(self):
		params = {}
		if (self.opt_global_filterverts_distance_min_enable):
			params["DeltaDistanceMin"] = self.opt_global_filterverts_distance_min
		if (self.opt_global_filterverts_distance_max_enable):
			params["DeltaDistanceMax"] = self.opt_global_filterverts_distance_max
		if (self.opt_global_filterverts_vertexgroup_enable):
			params["VertexGroupIndex"] = self.opt_global_filterverts_vertexgroup
		return params
	
	### Local options for shape key pairs split & merge
	opt_shapepairs_split_axis = EnumProperty(
		name = "",
		description = "World axis for splitting/merging shape keys into 'left' and 'right' halves.",
		items = [
			("+X", "+X", "Split/merge shape keys into a +X half ('left') and a -X half ('right'), using the YZ world plane. Pick this if your character faces -Y.", "AXIS_SIDE", 1),
			("+Y", "+Y", "Split/merge shape keys into a +Y half ('left') and a -Y half ('right'), using the XZ world plane. Pick this if your character faces +X.", "AXIS_FRONT", 2),
			("+Z", "+Z", "Split/merge shape keys into a +Z half ('left') and a -Z half ('right'), using the XY world plane.", "AXIS_TOP", 3),
			("-X", "-X", "Split/merge shape keys into a -X half ('left') and a +X half ('right'), using the YZ world plane. Pick this if your character faces +Y.", "AXIS_SIDE", 4),
			("-Y", "-Y", "Split/merge shape keys into a -Y half ('left') and a +Y half ('right'), using the XZ world plane. Pick this if your character faces -X.", "AXIS_FRONT", 5),
			("-Z", "-Z", "Split/merge shape keys into a -Z half ('left') and a +Z half ('right'), using the XY world plane.", "AXIS_TOP", 6),
		]
	)



#
#====================================================================================================
#    Ops panel
#====================================================================================================
#

class OBJECT_PT_ShapeKeyTools_Panel(bpy.types.Panel):
	bl_label = "Shape Key Tools"
	bl_idname = "OBJECT_PT_shape_key_tools_panel"
	bl_space_type = "VIEW_3D" 
	bl_region_type = "TOOLS"
	bl_category = "Tools"
	bl_context = "objectmode"
	bl_options = {"DEFAULT_CLOSED"}
	
	@classmethod
	def poll(cls, context):
		if (context.object == None):
			return False
		if (context.object.type != "MESH"):
			return False
		return True
	
	def draw(self, context):
		global UiIconsExtra
		
		scene = context.scene
		properties = scene.shape_key_tools_props
		
		layout = self.layout
		
		obj = context.object
		
		if (obj == None or obj.type != "MESH"):# or not hasattr(obj.data.shape_keys, "key_blocks") or len(obj.data.shape_keys.key_blocks.keys()) <= 1):
			layout.label("Active object is invalid.")
			return
		
		### Global options
		g0 = layout.box()
		g0Col = g0.column()
		g0Header = g0Col.row()
		g0Header.alignment = 'LEFT'
		g0Header.prop(properties, "opt_gui_subpanel_expander_globalopts", text="Common Options", icon=("TRIA_DOWN" if properties.opt_gui_subpanel_expander_globalopts else "TRIA_RIGHT"), emboss=False, expand=False)
		if (properties.opt_gui_subpanel_expander_globalopts):
			g0Body = g0Col.column()
			# Filter verts
			filterVerts = g0Body.box().column()
			filterVertsHeader = filterVerts.row()
			filterVertsHeader.alignment = 'EXPAND'
			filterVertsHeader.prop(properties, "opt_global_enable_filterverts")
			filterVertsHeader.label("", icon="FILTER")
			if (properties.opt_global_enable_filterverts):
				filterVertsBody = filterVerts.column()
				# Vertex group
				vg = filterVertsBody.box()
				vgCol = vg.column()
				vgCol.prop(properties, "opt_global_filterverts_vertexgroup_enable", text="Vertex Group:")
				vgValueCon = vgCol.row()
				vgValueCon.prop(properties, "opt_global_filterverts_vertexgroup", text="")
				vgValueCon.enabled = properties.opt_global_filterverts_vertexgroup_enable
				# Delta distance
				deltaDist = filterVertsBody.box()
				deltaDist.label("Delta Distance:")
				deltaDistCols = deltaDist.column_flow(columns=2, align=False)
				deltaDistMin = deltaDistCols.column()
				deltaDistMax = deltaDistCols.column()
				deltaDistMin.prop(properties, "opt_global_filterverts_distance_min_enable", text="Minimum:")
				deltaDistMinValueCon = deltaDistMin.row()
				deltaDistMinValueCon.prop(properties, "opt_global_filterverts_distance_min", text="")
				deltaDistMinValueCon.enabled = properties.opt_global_filterverts_distance_min_enable
				deltaDistMax.prop(properties, "opt_global_filterverts_distance_max_enable", text="Maximum:")
				deltaDistMaxValueCon = deltaDistMax.row()
				deltaDistMaxValueCon.prop(properties, "opt_global_filterverts_distance_max", text="")
				deltaDistMaxValueCon.enabled = properties.opt_global_filterverts_distance_max_enable
		
		### Split/merge pairs
		g1 = layout.box()
		g1Col = g1.column()
		g1Header = g1Col.row()
		g1Header.alignment = 'LEFT'
		g1Header.prop(properties, "opt_gui_subpanel_expander_shapepairs", text="Split/Merge L+R Pairs", icon=("TRIA_DOWN" if properties.opt_gui_subpanel_expander_shapepairs else "TRIA_RIGHT"), emboss=False, expand=False)
		if (properties.opt_gui_subpanel_expander_shapepairs):
			g1Body = g1Col.column()
			# Options
			g1sg1 = g1Body.box()
			g1sg1Col = g1sg1.column()
			g1sg1Header = g1sg1Col.row()
			g1sg1Header.alignment = 'LEFT'
			g1sg1Header.prop(properties, "opt_gui_subpanel_expander_shapepairsopts", text="Options", icon=("TRIA_DOWN" if properties.opt_gui_subpanel_expander_shapepairsopts else "TRIA_RIGHT"), emboss=False, expand=False)
			if (properties.opt_gui_subpanel_expander_shapepairsopts):
				g1sg1Body = g1sg1Col.column()
				g1sg1BodyRow1 = g1sg1Body.row()
				g1sg1BodyRow1.label("Split Axis:")
				g1sg1BodyRow1.prop(properties, "opt_shapepairs_split_axis", text="")
			# Operators
			g1Body.operator("wm.shape_key_tools_split_active_pair", icon_value=UiIconsExtra["arrow_divide"].icon_id)
			g1Body.operator("wm.shape_key_tools_split_all_pairs", icon_value=UiIconsExtra["arrow_divide"].icon_id)
			g1Body.operator("wm.shape_key_tools_smartmerge_active", icon_value=UiIconsExtra["arrow_join"].icon_id)
			g1Body.operator("wm.shape_key_tools_smartmerge_all_pairs", icon_value=UiIconsExtra["arrow_join"].icon_id)
		
		### Arbitary split/merge
		g2 = layout.box()
		g2Col = g2.column()
		g2Header = g2Col.row()
		g2Header.alignment = 'LEFT'
		g2Header.prop(properties, "opt_gui_subpanel_expander_arbitrary", icon=("TRIA_DOWN" if properties.opt_gui_subpanel_expander_arbitrary else "TRIA_RIGHT"), text="Arbitrary Split/Merge", emboss=False, expand=False)
		if (properties.opt_gui_subpanel_expander_arbitrary):
			g2Body = g2Col.column()
			# Operators
			splitByFilterCon = g2Body.row()
			splitByFilterCon.operator("wm.shape_key_tools_split_by_filter", icon_value=UiIconsExtra["arrow_branch"].icon_id)
			splitByFilterCon.enabled = properties.opt_global_enable_filterverts
			g2Body.operator("wm.shape_key_tools_combine_two", icon_value=UiIconsExtra["arrow_merge"].icon_id)
		
		### Modifiers
		g3 = layout.box()
		g3Col = g3.column()
		g3Header = g3Col.row()
		g3Header.alignment = 'LEFT'
		g3Header.prop(properties, "opt_gui_subpanel_expander_modifiers", icon=("TRIA_DOWN" if properties.opt_gui_subpanel_expander_modifiers else "TRIA_RIGHT"), text="Shape Key Modifiers", emboss=False, expand=False)
		if (properties.opt_gui_subpanel_expander_modifiers):
			g3Body = g3Col.column()
			# Operators
			g3Body.operator("wm.shape_key_tools_apply_modifiers_to_shape_keys", icon="MODIFIER")
		


def register():
	global UiIconsExtra
	
	# Custom icons
	UiIconsExtra = bpy.utils.previews.new()
	iconDir = os.path.join(os.path.dirname(__file__), "icons")
	for filename in os.listdir(iconDir):
		if (filename[-4:] == ".png"):
			UiIconsExtra.load(filename[:-4], os.path.join(iconDir, filename), "IMAGE")
			
	# Top level structure
	bpy.utils.register_module(__name__)
	bpy.types.Scene.shape_key_tools_props = PointerProperty(type=ShapeKeyTools_Properties)
	
	# Operators
	opsDir = os.path.join(os.path.dirname(__file__), "ops")
	for filename in os.listdir(opsDir):
		fullpath = os.path.join(opsDir, filename)
		if (os.path.isfile(fullpath)): # dont import the pycache folder
			script = imp.load_source("ops." + filename[:-3], fullpath)
			operatorClass = script.register()
			info = SimpleNamespace()
			info.Script = script
			info.OpClass = operatorClass
			RegisteredOps[operatorClass.bl_idname] = info

def unregister():
	global UiIconsExtra
	
	bpy.utils.previews.remove(UiIconsExtra)
	
	del bpy.types.Scene.shape_key_tools_props
	bpy.utils.unregister_module(__name__)
	
	for blenderID in RegisteredOps:
		info = RegisteredOps[blenderID]
		info.Script.unregister()
	RegisteredOps = {}

if __name__ == "__main__":
	register()
