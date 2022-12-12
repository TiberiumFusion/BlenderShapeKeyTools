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
	"version": (2, 2, 1, 0),
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
from bpy.app.handlers import persistent

from . import common


# Container of our custom icons
UiIconsExtra = None

# Dictionary of registered operators, mapped by their Blender ID (e.g. "wm.shape_key_tools_split_active_pair")
RegisteredOps = {}

# Set by register() and unregister(), used by persistent application handlers to deactive as expected when the addon is unloaded
AddonEnabled = False



#
#====================================================================================================
#    Helpers
#====================================================================================================
#

### Gets one of this addon's operator classes as specified by its bl_id
def GetRegisteredOpClass(clsBlId):
	global RegisteredOps
	
	if (clsBlId in RegisteredOps):
		return RegisteredOps[clsBlId].OpClass # We have to manually track our registered operators because bpy.types.<our operator class> is always null for no good reason



#
#====================================================================================================
#    Background modal operators
#====================================================================================================
#

##
## Viewport-related background ops
##

def StartViewportVisualizationOp(contextOverride=None):
	opCls = GetRegisteredOpClass("view3d.shape_key_tools_viewport_visuals")
	if (opCls.IsRunning == False):
		if (contextOverride != None):
			bpy.ops.view3d.shape_key_tools_viewport_visuals(contextOverride)
		else:
			bpy.ops.view3d.shape_key_tools_viewport_visuals()

def StartSplitPairPreviewOp(contextOverride=None):
	opCls = GetRegisteredOpClass("view3d.shape_key_tools_splitpair_preview")
	if (opCls.InstanceInfo == None):
		if (contextOverride != None):
			bpy.ops.view3d.shape_key_tools_splitpair_preview(contextOverride)
		else:
			bpy.ops.view3d.shape_key_tools_splitpair_preview()


### Create a watcher for the blend file load event so we can start background ops if a blend file was saved with any enabled
@persistent
def BlendFileOpenedWatcher(dummy):
	try: # All of this is dangerous since we cannot assume anything about the user's actions or intent when this is raised
		if (AddonEnabled):
			scene = bpy.context.scene
			properties = scene.shape_key_tools_props
			
			runViewportVisualizer = properties.opt_shapepairs_splitmerge_viewportvisualize
			runSplitPairPreview = (properties.opt_shapepairs_splitmerge_preview_split_left or properties.opt_shapepairs_splitmerge_preview_split_right)
			
			overrideContext = None
			if (runViewportVisualizer or runSplitPairPreview):
				# Because there is no way to get the context of the viewport control, we have to make it ourselves... grrr
				# Reference: https://b3d.interplanety.org/en/context-override/
				areas = [area for area in bpy.context.screen.areas if area.type == "VIEW_3D"]
				if (len(areas) > 0):
					area = areas[0]
					overrideContext = bpy.context.copy()
					overrideContext["window"] = bpy.context.window
					overrideContext["screen"] = bpy.context.screen
					overrideContext["scene"] = bpy.context.scene
					overrideContext["area"] = area
					overrideContext["region"] = area.regions[-1]
					overrideContext["space_data"] = area.spaces.active
			
			if (runViewportVisualizer):
				try:
					StartViewportVisualizationOp(overrideContext)
				except:
					pass
			
			if (runSplitPairPreview):
				try:
					StartSplitPairPreviewOp(overrideContext)
				except:
					pass
	except:
		pass
bpy.app.handlers.load_post.append(BlendFileOpenedWatcher)



#
#====================================================================================================
#    Top level properties
#====================================================================================================
#

class ShapeKeyTools_Properties(bpy.types.PropertyGroup):
	
	##
	## UI glue
	##
	
	### Subpanel expanders
	opt_gui_subpanel_expander_globalopts = BoolProperty(name="Global Options", default=False, description="These options are shared by all operations, but some operations may not use them. Read each operation's tooltip for more info!")
	opt_gui_subpanel_expander_shapepairs = BoolProperty(name="Split/Merge Pairs", default=True, description="Operations for splitting and merging shape key pairs (i.e. symmetrical shape keys, like facial expressions)")
	opt_gui_subpanel_expander_shapepairsopts = BoolProperty(name="Split/Merge Pairs Options", default=True, description="These options ONLY affect the 4 operations below")
	opt_gui_subpanel_expander_arbitrary = BoolProperty(name="Arbitrary Split/Merge Operations", default=True, description="General purpose split & merge operations")
	opt_gui_subpanel_expander_modifiers = BoolProperty(name="Modifer Operations", default=True, description="Operations involving shape keys and modifiers")
	opt_gui_subpanel_expander_info = BoolProperty(name="Info", default=True, description="Miscellaneous information on the active object's shape keys")
	
	### Helpers for enabling/disabling controls based on other controls
	opt_gui_enabler_shapepairs_split_smoothdist = BoolProperty(name="", default=False, description="For internal addon use only.")
	
	
	##
	## Global options for all ops
	##
	
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
	
	
	##
	## Local options for shape key pairs split & merge
	##
	
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
	
	def inputShapePairsSplitModeChanged(self, context):
		if (self.opt_shapepairs_split_mode == "smooth"):
			self.opt_gui_enabler_shapepairs_split_smoothdist = True
		else:
			self.opt_gui_enabler_shapepairs_split_smoothdist = False
	opt_shapepairs_split_mode = EnumProperty(
		name = "",
		description = "Method for determing the per-side deltas when splitting shape keys into 'left' and 'right' halves.",
		items = [
			("sharp", "Sharp", "Sharp divide. No smoothing between the split left and right halves. Useful for shape keys that have distinct halves and do not connect in the center, like eye shapes."),
			("smooth", "Smooth", "Smoothed divide. The left and right halves are crossfaded within the specified Smoothing Distance. Useful for shape keys that connect in the center, like mouth shapes."),
		],
		update = inputShapePairsSplitModeChanged,
	)
	
	opt_shapepairs_split_smoothdist = FloatProperty(
		name = "Smoothing Distance",
		description = "Only used by Smooth Split Mode. Radius (in worldspace) from the center of split axis that defines the region in which the left and right halves of the shape key are smoothed when split. Smoothing uses simple bezier interpolation",
		min = 0.0,
		soft_min = 0.0,
		soft_max = 100.0,
		default = 1.0,
		precision = 2,
		step = 0.1,
		subtype = 'DISTANCE',
		unit = 'LENGTH',
	)
	
	opt_shapepairs_merge_mode = EnumProperty(
		name = "",
		description = "Method for combining left and right shape keys together.",
		items = [
			("additive", "Additive", "All deltas from both shape keys will be added together. This mode is suitable if you previously split the shape key with either the 'Smooth' or 'Sharp' mode."),
			("overwrite", "Overwrite", "Only the deltas from the left side of the left shape key and the right side of the right shape key will be used. This mode is only suitable if you previously split the shape key with 'Sharp' mode."),
		],
	)
	
	def inputShapePairsVisualizeSplitMergeAxisChanged(self, context):
		StartViewportVisualizationOp()
	opt_shapepairs_splitmerge_viewportvisualize = BoolProperty(
		name = "Visualize Split/Merge Regions",
		description = "Draws an overlay in the viewport that represents the current split/merge parameters",
		default = False,
		update = inputShapePairsVisualizeSplitMergeAxisChanged,
	)
	opt_shapepairs_splitmerge_viewportvisualize_show_splitplane = BoolProperty(
		name = "Show Split Plane",
		description = "Show the world plane that will bisect the shape keys",
		default = True,
	)
	opt_shapepairs_splitmerge_viewportvisualize_show_splithalves = BoolProperty(
		name = "Show Halves",
		description = "Shows the left and right sides of the split plane",
		default = True,
	)
	opt_shapepairs_splitmerge_viewportvisualize_show_smoothregion = BoolProperty(
		name = "Show Smoothing Region",
		description = "Shows the region where the split shape keys will be cross-blended when Split Mode is set to Smooth",
		default = True,
	)
	
	def inputSplitPairPreviewLeftChanged(self, context):
		if (self.opt_shapepairs_splitmerge_preview_split_left):
			self.opt_shapepairs_splitmerge_preview_split_right = False
			StartSplitPairPreviewOp()
	opt_shapepairs_splitmerge_preview_split_left = BoolProperty(
		name = "L",
		description = "Live preview the result of the Split Active Shape Key operator. Change the split options with realtime feedback in the viewport",
		default = False,
		update = inputSplitPairPreviewLeftChanged,
	)
	
	def inputSplitPairPreviewRightChanged(self, context):
		if (self.opt_shapepairs_splitmerge_preview_split_right):
			self.opt_shapepairs_splitmerge_preview_split_left = False
			StartSplitPairPreviewOp()
	opt_shapepairs_splitmerge_preview_split_right = BoolProperty(
		name = "R",
		description = "Live preview the result of the Split Active Shape Key operator. Change the split options with realtime feedback in the viewport",
		default = False,
		update = inputSplitPairPreviewRightChanged,
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
				# Split axis
				g1sg1BodyRow1 = g1sg1Body.row()
				g1sg1BodyRow1.label("Split Axis:")
				g1sg1BodyRow1.prop(properties, "opt_shapepairs_split_axis", text="")
				# Split mode
				g1sg1BodyRow2 = g1sg1Body.row()
				g1sg1BodyRow2.label("Split Mode:")
				g1sg1BodyRow2.prop(properties, "opt_shapepairs_split_mode", text="")
				# Smoothing factor
				g1sg1BodyRow3 = g1sg1Body.row()
				g1sg1BodyRow3.prop(properties, "opt_shapepairs_split_smoothdist")
				g1sg1BodyRow3.enabled = properties.opt_gui_enabler_shapepairs_split_smoothdist
				# Merge mode
				g1sg1BodyRow4 = g1sg1Body.row()
				g1sg1BodyRow4.label("Merge Mode:")
				g1sg1BodyRow4.prop(properties, "opt_shapepairs_merge_mode", text="")
				### Split/merge visualization
				# Master show/hide
				g1sg1BodyRow5 = g1sg1Body.row()
				g1sg1BodyRow5.prop(properties, "opt_shapepairs_splitmerge_viewportvisualize")
				if (properties.opt_shapepairs_splitmerge_viewportvisualize):
					# Show split plane
					g1sg1BodyRow6 = g1sg1Body.row()
					g1sg1BodyRow6.separator()
					g1sg1BodyRow6.prop(properties, "opt_shapepairs_splitmerge_viewportvisualize_show_splitplane")
					g1sg1BodyRow6.enabled = properties.opt_shapepairs_splitmerge_viewportvisualize
					# Show split halves
					g1sg1BodyRow7 = g1sg1Body.row()
					g1sg1BodyRow7.separator()
					g1sg1BodyRow7.prop(properties, "opt_shapepairs_splitmerge_viewportvisualize_show_splithalves")
					g1sg1BodyRow7.enabled = properties.opt_shapepairs_splitmerge_viewportvisualize
					# Show smoothing region
					g1sg1BodyRow8 = g1sg1Body.row()
					g1sg1BodyRow8.separator()
					g1sg1BodyRow8.enabled = properties.opt_shapepairs_splitmerge_viewportvisualize
					g1sg1BodyRow8a = g1sg1BodyRow8.row()
					g1sg1BodyRow8a.prop(properties, "opt_shapepairs_splitmerge_viewportvisualize_show_smoothregion")
					g1sg1BodyRow8a.enabled = properties.opt_gui_enabler_shapepairs_split_smoothdist
				# Split mesh preview
				g1sg1BodyRow9 = g1sg1Body.row()
				g1sg1BodyRow9.alignment = 'LEFT'
				g1sg1BodyRow9.label("Preview Split:")
				g1sg1BodyRow9.prop(properties, "opt_shapepairs_splitmerge_preview_split_left")
				g1sg1BodyRow9.prop(properties, "opt_shapepairs_splitmerge_preview_split_right")
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
		
		### Info
		g4 = layout.box()
		g4Col = g4.column()
		g4Header = g4Col.row()
		g4HeaderL = g4Header.row()
		g4HeaderR = g4Header.row()
		g4HeaderL.alignment = 'LEFT'
		g4HeaderR.alignment = 'RIGHT'
		infoHeaderText = "Info"
		if (obj):
			infoHeaderText = obj.name
		g4HeaderL.prop(properties, "opt_gui_subpanel_expander_info", icon=("TRIA_DOWN" if properties.opt_gui_subpanel_expander_info else "TRIA_RIGHT"), text=infoHeaderText, emboss=False, expand=False)
		g4HeaderR.label(text="", icon="QUESTION")
		if (properties.opt_gui_subpanel_expander_info):
			g4Body = g4Col.column()
			try:
				if (hasattr(obj.data.shape_keys, "key_blocks")):
					# Active shape key
					active = g4Body.box().column()
					activeRow = active.row()
					activeL = activeRow.row()
					activeR = activeRow.row()
					activeL.alignment = "LEFT"
					activeR.alignment = "RIGHT"
					activeL.label("Active")
					activeR.label(obj.data.shape_keys.key_blocks[obj.active_shape_key_index].name)
					if (obj.active_shape_key_index == 0):
						active.label("Incompatible with some ops", icon="ERROR")
					# Total shape keys
					total = g4Body.box().column()
					totalRow = total.row()
					totalL = totalRow.row()
					totalR = totalRow.row()
					totalL.alignment = "LEFT"
					totalR.alignment = "RIGHT"
					totalL.label("Total shape keys")
					totalR.label(str(len(obj.data.shape_keys.key_blocks)))
					# Merged L+R pair keys
					pairKeys = g4Body.box().column()
					pairKeysRow = pairKeys.row()
					pairKeysL = pairKeysRow.row()
					pairKeysR = pairKeysRow.row()
					pairKeysL.alignment = "LEFT"
					pairKeysR.alignment = "RIGHT"
					pairKeysL.label("L+R Pairs")
					pairCount = 0
					seen = {}
					for keyBlock in obj.data.shape_keys.key_blocks:
						if (not keyBlock.name in seen):
							seen[keyBlock.name] = True
							(splitLName, splitRName, usesPlusConvention) = common.FindShapeKeyPairSplitNames(keyBlock.name)
							if (usesPlusConvention):
								pairCount += 1
					pairKeysR.label(str(pairCount))
					# Unmerged L+R pair keys
					unmergedPairKeys = g4Body.box().column()
					unmergedPairKeysRow = unmergedPairKeys.row()
					unmergedPairKeysL = unmergedPairKeysRow.row()
					unmergedPairKeysR = unmergedPairKeysRow.row()
					unmergedPairKeysL.alignment = "LEFT"
					unmergedPairKeysR.alignment = "RIGHT"
					unmergedPairKeysL.label("Unmerged L+R Pairs")
					unmergedPairCount = 0
					seen = {}
					for keyBlock in obj.data.shape_keys.key_blocks:
						if (not keyBlock.name in seen):
							seen[keyBlock.name] = True
							(firstName, expectedCompName, mergedName) = common.FindShapeKeyMergeNames(keyBlock.name)
							if (not expectedCompName in seen and expectedCompName in obj.data.shape_keys.key_blocks.keys()):
								seen[expectedCompName] = True
								unmergedPairCount += 1
					unmergedPairKeysR.label(str(unmergedPairCount))
				else:
					g4Body.label("Object has no shape keys.")
			except Exception as e:
				g4Body.label(str(e), icon="CANCEL")
				raise
		


def register():
	global UiIconsExtra
	global RegisteredOps
	global AddonEnabled
	
	AddonEnabled = True
	
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
	global RegisteredOps
	global AddonEnabled
	
	AddonEnabled = False
	
	bpy.utils.previews.remove(UiIconsExtra)
	
	del bpy.types.Scene.shape_key_tools_props
	bpy.utils.unregister_module(__name__)
	
	for blenderID in RegisteredOps:
		info = RegisteredOps[blenderID]
		info.Script.unregister()
	RegisteredOps = {}

if __name__ == "__main__":
	register()
