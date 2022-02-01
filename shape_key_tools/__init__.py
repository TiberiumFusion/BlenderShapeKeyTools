# ////////////////////////////////////////////////////////////////////////////////////////////////////
# //
# //    Shape Key Tools for Blender 2.79
# //    - Split/merge shape keys pairs (e.g. MyShapeKeyL+MyShapeKeyR) into left and right halves
# //    - Merge any two arbitrary shape keys with various blending modes
# //    - Split certain deltas off from one shape key to form a new shape key
# //
# ////////////////////////////////////////////////////////////////////////////////////////////////////

bl_info = {
	"name": "Shape Key Tools",
	"author": "TiberiumFusion",  
	"version": (2, 0, 0, 0),
	"blender": (2, 78, 0), # This is a guess... I think it was 2.77 or 2.78 that added some of the operators/api we need. Definitely no earlier than 2.75, since that is when support for custom icons was added.
	"location": "Object > Tools > Shape Key Tools",
	"description": "Tools for working with shape keys beyond Blender's limited abilities.",
	"wiki_url": "https://github.com/TiberiumFusion/BlenderShapeKeyTools",
	"tracker_url": "https://github.com/TiberiumFusion/BlenderShapeKeyTools/issues",
	"warning": "",
	"category": "Tools",
}

import os, textwrap, bpy, bpy.utils.previews
from bpy.props import *
from . import main


UiIconsExtra = None



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
	opt_gui_subpanel_expander_arbitrary = BoolProperty(name="Other Operations", default=True, description="General purpose operations")
	
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
#    Shake Key Pairs Split/Merge
#====================================================================================================
#

class WM_OT_ShapeKeyTools_OpSplitActivePair(bpy.types.Operator):
	bl_idname = "wm.shape_key_tools_split_active_pair"
	bl_label = "Split Active Shape Key"
	bl_description = "Splits the active shape key on the active mesh into two separate shape keys. The left and right halves are determined by your chosen split axis. This operation does NOT use the Vertex Filter!"
	bl_options = {"UNDO"}
	
	def validate(self, context):
		obj = context.object
		
		# Object must be a mesh
		if (obj.type != "MESH"):
			self.report({'ERROR'}, "The active object ('" + obj.name + "', type: " + obj.type + ") is not a mesh!")
			return False
		
		# Object must have enough shape keys
		if (not hasattr(obj.data.shape_keys, "key_blocks") or len(obj.data.shape_keys.key_blocks.keys()) <= 1):
			self.report({'ERROR'}, "The active object must have at least 1 shape key (excluding the basis shape key).")
			return False
		
		# Active shape key cannot be the basis shape key		
		activeShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(obj.active_shape_key.name)
		if (activeShapeKeyIndex == 0):
			self.report({'ERROR'}, "You cannot split the basis shape key.")
			return False
		
		return True
	
	def execute(self, context):
		scene = context.scene
		properties = scene.shape_key_tools_props
		
		if context.object:
			obj = context.object
			if (self.validate(context) == False):
				return {'FINISHED'}
			
			activeShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(obj.active_shape_key.name)
			newNameData = main.FindShapeKeySplitNames(obj.active_shape_key.name)
			main.SplitPairActiveShapeKey(obj, properties.opt_shapepairs_split_axis, newNameData[0], newNameData[1])
			obj.active_shape_key_index = activeShapeKeyIndex # reselect the shape key at the original's index (will be the left split shape key)
		
		return {'FINISHED'}
	
class WM_OT_ShapeKeyTools_OpSplitAllPairs(bpy.types.Operator):
	bl_idname = "wm.shape_key_tools_split_all_pairs"
	bl_label = "Split All Paired Shape Keys"
	bl_description = "Splits ALL paired shape keys (i.e. shape keys with names like 'MyShapeKeyL+MyShapeKeyR') on the active mesh into two separate shape keys. The left and right halves are determined by your chosen split axis. This operation does NOT use the Vertex Filter!"
	bl_options = {"UNDO"}
	
	_asyncProgressStage = 0
	_timer = None
	
	_scene = None
	_properties = None

	_asyncWorkData = None

	def asyncWork(self, context):
		# The actual operation
		self._asyncWorkData["_OpMethod"](self._asyncWorkData)
		
		if self._asyncWorkData["_Finished"]:
			self._asyncProgressStage = 2
	
	def modal(self, context, event):
		if event.type == "TIMER" and self._asyncProgressStage == 1:
			self.asyncWork(context)
			
		if self._asyncProgressStage >= 2:
			self.cancel(context)
			return {"CANCELLED"}
		
		return {"PASS_THROUGH"}
	
	def validate(self, context):
		obj = context.object
		
		# Object must be a mesh
		if (obj.type != "MESH"):
			self.report({'ERROR'}, "The active object ('" + obj.name + "', type: " + obj.type + ") is not a mesh!")
			return False
		
		# Object must have enough shape keys
		if (not hasattr(obj.data.shape_keys, "key_blocks") or len(obj.data.shape_keys.key_blocks.keys()) <= 1):
			self.report({'ERROR'}, "The active object must have at least 1 shape key (excluding the basis shape key).")
			return False
		
		return True
	
	def execute(self, context):				
		self._scene = context.scene
		self._properties = self._scene.shape_key_tools_props
		
		if context.object:
			obj = context.object
			if (self.validate(context) == False):
				return {'FINISHED'}
			
			# Get async operation data
			self._asyncWorkData = main.SplitAllShapeKeyPairsAsync(obj, self._properties.opt_shapepairs_split_axis)
			
			# Returned data will be non-null if there are some shape keys to split
			if self._asyncWorkData:
				context.window_manager.modal_handler_add(self)
				self._asyncProgressStage = 1
				self._timer = context.window_manager.event_timer_add(0.1, context.window)
				
				return {"RUNNING_MODAL"}
			# Returned data will be null if there are no shape keys to split
			else:
				return {"FINISHED"}
		
	def cancel(self, context):
		context.window_manager.event_timer_remove(self._timer)
		self._timer = None
		self._asyncProgressStage = 0
		

class WM_OT_ShapeKeyTools_OpMergeActive(bpy.types.Operator):
	bl_idname = "wm.shape_key_tools_smartmerge_active"
	bl_label = "Smart Merge Active Shape Key"
	bl_description = "Merges the active mesh's active shape key with its counterpart pair shape key. E.g. MyShapeKeyL will be merged with MyShapeKeyR into a single shape key named MyShapeKeyL+MyShapeKeyR. This operation does NOT use the Vertex Filter!"
	bl_options = {"UNDO"}
	
	def validate(self, context):
		obj = context.object
		
		# Object must be a mesh
		if (obj.type != "MESH"):
			self.report({'ERROR'}, "The active object ('" + obj.name + "', type: " + obj.type + ") is not a mesh!")
			return False
		
		# Object must have enough shape keys
		if (not hasattr(obj.data.shape_keys, "key_blocks") or len(obj.data.shape_keys.key_blocks.keys()) <= 2):
			self.report({'ERROR'}, "The active object must have at least 2 shape keys (excluding the basis shape key).")
			return False
		
		# Active shape key cannot be the basis shape key		
		activeShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(obj.active_shape_key.name)
		if (activeShapeKeyIndex == 0):
			self.report({'ERROR'}, "You cannot merge the basis shape key.")
			return False
		
		return True
	
	def execute(self, context):
		scene = context.scene
		properties = scene.shape_key_tools_props
		
		if context.object:
			obj = context.object
			if (self.validate(context) == False):
				return {'FINISHED'}
			
			main.MergePairActiveShapeKey(obj, properties.opt_shapepairs_split_axis)
		
		return {'FINISHED'}
	
class WM_OT_ShapeKeyTools_OpMergeAllPairs(bpy.types.Operator):
	bl_idname = "wm.shape_key_tools_smartmerge_all_pairs"
	bl_label = "Smart Merge All Shape Keys"
	bl_description = "Merges all shape keys pairs on the active mesh into single left+right shape keys. Only shape keys that use the 'MyShapeKeyL' 'MyShapeKeyR' naming convention will be merged. This operation does NOT use the Vertex Filter!"
	bl_options = {"UNDO"}

	_asyncProgressStage = 0
	_timer = None
	
	_scene = None
	_properties = None

	_asyncWorkData = None

	def asyncWork(self, context):
		self._asyncWorkData["_OpMethod"](self._asyncWorkData) # the actual operation
		
		if self._asyncWorkData["_Finished"]:
			self._asyncProgressStage = 2

	def modal(self, context, event):
		if event.type == "TIMER" and self._asyncProgressStage == 1:
			self.asyncWork(context)
			
		if self._asyncProgressStage >= 2:
			self.cancel(context)
			return {"CANCELLED"}
		
		return {"PASS_THROUGH"}
	
	def validate(self, context):
		obj = context.object
		
		# Object must be a mesh
		if (obj.type != "MESH"):
			self.report({'ERROR'}, "The active object ('" + obj.name + "', type: " + obj.type + ") is not a mesh!")
			return False
		
		# Object must have enough shape keys
		if (not hasattr(obj.data.shape_keys, "key_blocks") or len(obj.data.shape_keys.key_blocks.keys()) <= 2):
			self.report({'ERROR'}, "The active object must have at least 2 shape keys (excluding the basis shape key).")
			return False
		
		return True
	
	def execute(self, context):				
		self._scene = context.scene
		self._properties = self._scene.shape_key_tools_props
		
		if context.object:
			obj = context.object
			if (self.validate(context) == False):
				return {'FINISHED'}
			
			# Get async operation data
			self._asyncWorkData = main.MergeAllShapeKeyPairsAsync(obj, self._properties.opt_shapepairs_split_axis)
			
			# Returned data will be non-null if there are some shape keys to merge
			if self._asyncWorkData:
				context.window_manager.modal_handler_add(self)
				self._asyncProgressStage = 1
				self._timer = context.window_manager.event_timer_add(0.1, context.window)
				
				return {"RUNNING_MODAL"}
			# Returned data will be null if there are no shape keys to merge
			else:
				return {"FINISHED"}
		
	def cancel(self, context):
		context.window_manager.event_timer_remove(self._timer)
		self._timer = None
		self._asyncProgressStage = 0
		


#
#====================================================================================================
#    Arbitrary Split & Merge
#====================================================================================================
#

class WM_OT_ShapeKeyTools_OpSplitByFilter(bpy.types.Operator):
	bl_idname = "wm.shape_key_tools_split_by_filter"
	bl_label = "Split Active Shape Key"
	bl_description = "REQUIRES the Vertex Filter to be enabled! Splits the active mesh's active shape key into two shape keys, using the Vertex Filter to determine which deltas end up in the new shape key"
	bl_options = {"UNDO"}
	
	opt_mode = EnumProperty(
		name = "Split Mode",
		description = "Method for splitting off deltas from this shape key to a new shape key.",
		items = [
			("copy", "Copy", "RED deltas will be copied to the new shape key. The active shape key will remain unchanged."),
			("move", "Move", "RED deltas will be copied to the new shape key, then those deltas will be removed from the active shape key (verts will be reverted to their basis position from the basis shape key)"),
		]
	)
	
	opt_new_shape_key_name = StringProperty(
		name = "New Shape Key Name",
		description = "Name for the newly split shape key",
	)
	
	def draw(self, context):
		layout = self.layout
		topBody = layout.column()
		
		topBody.label("Split off a new shape key from the active shape key, using the Vertex Filter.")
		topBody.label("Verts with RED deltas will be preserved in the new shape key.")
		topBody.label("Verts with BLACK deltas will revert to their basis position in the new shape key.")
		
		optsBox = topBody.box().column()
		optsBox.prop(self, "opt_mode", text="Mode")
		optsBox.prop(self, "opt_new_shape_key_name", text="New Shape Key Name:")
	
	def validate(self, context):
		obj = context.object
		
		# Object must be a mesh
		if (obj.type != "MESH"):
			self.report({'ERROR'}, "The active object ('" + obj.name + "', type: " + obj.type + ") is not a mesh!")
			return False
		
		# Object must have enough shape keys
		if (not hasattr(obj.data.shape_keys, "key_blocks") or len(obj.data.shape_keys.key_blocks.keys()) <= 1):
			self.report({'ERROR'}, "The active object must have at least 1 shape key (excluding the basis shape key).")
			return False
		
		return True
	
	def execute(self, context):
		scene = context.scene
		properties = scene.shape_key_tools_props
		
		if context.object:
			obj = context.object
			if (self.validate(context) == False):
				return {'FINISHED'}
			
			vertexFilterParams = None
			if (properties.opt_global_enable_filterverts):
				vertexFilterParams = properties.getEnabledVertexFilterParams()
			
			main.SplitFilterActiveShapeKey(obj,  self.opt_new_shape_key_name, self.opt_mode, vertexFilterParams)
			
		return {'FINISHED'}
	
	def invoke(self, context, event):
		scene = context.scene
		properties = scene.shape_key_tools_props
		
		if context.object:
			obj = context.object
			if (self.validate(context) == False):
				return {'FINISHED'}
			
			# Default options
			self.opt_new_shape_key_name = obj.active_shape_key.name + "__SPLIT"
			
			return context.window_manager.invoke_props_dialog(self, width=450)
	
class WM_OT_ShapeKeyTools_OpCombineTwo(bpy.types.Operator):
	bl_idname = "wm.shape_key_tools_combine_two"
	bl_label = "Combine Two Shape Keys"
	bl_description = "Combines any two shape keys with various options for blending the two shape keys' deltas together. This operation CAN make use of the Vertex Filter."
	bl_options = {"UNDO"}
	
	latest_shape_keys_items = None
	def getShapeKeys(self, context):
		shapeKeysOrdered = []
		for shapeKeyBlock in context.object.data.shape_keys.key_blocks:
			index = context.object.data.shape_keys.key_blocks.keys().index(shapeKeyBlock.name)
			if (index > 0): # dont include the basis shape key
				shapeKeysOrdered.append((index, shapeKeyBlock.name))
		def s(v):
			return v[0]
		shapeKeysOrdered.sort(key=s)
		latest_shape_keys_items = [(str(tuple[0]), tuple[1], tuple[1], "SHAPEKEY_DATA", tuple[0] - 1) for tuple in shapeKeysOrdered]
		return latest_shape_keys_items
	def inputShapeKeysChanged(self, context):
		if (self.opt_output_newname[:8] == "MERGED__" or self.opt_output_newname == "" or self.opt_output_newname == None):
			sk1Name = context.object.data.shape_keys.key_blocks[int(self.opt_shape_key_1, 10)].name
			sk2Name = context.object.data.shape_keys.key_blocks[int(self.opt_shape_key_2, 10)].name
			self.opt_output_newname = "MERGED__" + sk1Name + "__" + sk2Name
	opt_shape_key_1 = EnumProperty(
		name = "Shape Key 1 (Bottom Layer)",
		description = "One of the two shape keys that will be combined. In regards to the blending operation, this shape key exists on the 'layer' *below* Shape Key 2",
		items = getShapeKeys,
		update = inputShapeKeysChanged,
	)
	opt_shape_key_2 = EnumProperty(
		name = "Shape Key 2 (Top Layer)",
		description = "One of the two shape keys that will be combined. In regards to the blending operation, this shape key exists on the 'layer' *above* Shape Key 1",
		items = getShapeKeys,
		update = inputShapeKeysChanged,
	)
	
	opt_blend_mode = EnumProperty(
		name = "Blend Mode",
		description = "Method for compositing together the positions of the vertices in the two shape keys",
		items = [
			("add", "Additive", "Shape Key 2's deltas will be added to Shape Key 1's deltas. If the Vertex Filter is enabled, only RED deltas from Shape Key 2 will be added to Shape Key 1"),
			("subtract", "Subtract", "Shape Key 2's deltas will be subtracted from Shape Key 1's deltas. If the Vertex Filter is enabled, only RED deltas from Shape Key 2 will be subtracted from Shape Key 1"),
			("multiply", "Multiply", "Shape Key 1's deltas will be multiplied by Shape Key 2's deltas. If the Vertex Filter is enabled, only RED deltas from Shape Key 2 will be multiplied with Shape Key 1"),
			("divide", "Divide", "Shape Key 1's deltas will be divided by Shape Key 2's deltas. If the Vertex Filter is enabled, only RED deltas from Shape Key 2 will be divided into Shape Key 1"),
			("over", "Overwrite", "Shape Key 1's deltas will be replaced with Shape Key 2's deltas. If the Vertex Filter is enabled, only RED deltas from Shape Key 2 will replace their counterparts in Shape Key 1"),
			("lerp", "Lerp", "Shape Key 1's deltas will be lerped towards Shape Key 2's deltas, using the user-specified lerp factor. If the Vertex Filter is enabled, only RED deltas from Shape Key 2 will be lerp'd into Shape Key 1"),
		]
	)
	opt_blend_lerp_factor = FloatProperty(
		name = "Lerp Blend Mode Factor",
		description = "Lerp factor, from 0 to 1. E.g. a value of 0.3 is 30% Shape Key 1 and 70% Shape Key 2",
		min = 0.0,
		max = 1.0,
		soft_min = 0.0,
		soft_max = 1.0,
		default = 0.5,
		precision = 6,
		step = 1,
	)
	
	def optOutputChanged(self, context):
		if (self.opt_output == "replace1"):
			self.opt_delete_shapekey1_on_finish = False
			self.opt_delete_shapekey2_on_finish = True
		elif (self.opt_output == "replace2"):
			self.opt_delete_shapekey2_on_finish = False
			self.opt_delete_shapekey1_on_finish = True
		elif (self.opt_output == "new"):
			self.opt_delete_shapekey2_on_finish = False
			self.opt_delete_shapekey1_on_finish = False
			if (self.opt_output_newname[:8] == "MERGED__" or self.opt_output_newname == "" or self.opt_output_newname == None):
				sk1Name = context.object.data.shape_keys.key_blocks[int(self.opt_shape_key_1, 10)].name
				sk2Name = context.object.data.shape_keys.key_blocks[int(self.opt_shape_key_2, 10)].name
				self.opt_output_newname = "MERGED__" + sk1Name + "__" + sk2Name
	
	opt_output = EnumProperty(
		name = "Output",
		description = "Type of output for the newly combined shape key",
		items = [
			("replace1", "Replace Shape Key 1", "Output the combined shape key result to Shape Key 1."),
			("replace2", "Replace Shape Key 2", "Output the combined shape key result to Shape Key 2."),
			("new", "New Shape Key", "Create a new shape key for the result."),
		],
		update = optOutputChanged
	)
	opt_delete_shapekey1_on_finish = BoolProperty(
		name = "Delete Shape Key 1 On Finish",
		description = "Delete Shape Key 1 after combining",
		default = False,
	)
	opt_delete_shapekey2_on_finish = BoolProperty(
		name = "Delete Shape Key 2 On Finish",
		description = "Delete Shape Key 2 after combining",
		default = True,
	)
	opt_output_newname = StringProperty(
		name = "New Combined Shape Key Name",
		description = "Name for the new, combined shape key",
	)
	
	def check(self, context):
		return True # To force redraws in the operator panel, which is does *not* occur by default
	
	def draw(self, context):
		scene = context.scene
		properties = scene.shape_key_tools_props
		
		layout = self.layout
		topBody = layout.column()
		
		### Header area
		if (properties.opt_global_enable_filterverts):
			warnRow = topBody.row()
			topBody.label("The Vertex Filter is ENABLED and will affect this operation!", icon="ERROR")
		
		### Layers and blend mode
		gLayers = topBody.box().column()
		gLayers.label("Shape Key Layers")
		gLayersInner = gLayers.box().column()
		# Header row
		header = gLayersInner.row().column_flow(columns=3, align=False)
		header.label("") # dummy
		header.label("") # dummy
		header.label("Blend Mode")
		# Top layer row
		layer2 = gLayersInner.row().column_flow(columns=3, align=False)
		layer2.label("Shape Key 2 (top layer)")
		layer2.prop(self, "opt_shape_key_2", text="")
		if (self.opt_blend_mode == "lerp"):
			blendModeRow = layer2.row().column_flow(columns=2, align=False)
			blendModeRow.prop(self, "opt_blend_mode", text="")
			blendModeRow.prop(self, "opt_blend_lerp_factor", text="")
		else:
			layer2.prop(self, "opt_blend_mode", text="")
		# Bottom layer row
		layer1 = gLayersInner.row().column_flow(columns=3, align=False)
		layer1.label("Shape Key 1 (bottom layer)")
		layer1.prop(self, "opt_shape_key_1", text="")
		layer1.label("") # dummy
		
		### Output options
		gOutput = topBody.box().column()
		row = gOutput.row()
		# Type
		row.label("Output")
		row.prop(self, "opt_output", text="")
		# Type-specific options
		subcols = gOutput.row().column_flow(columns=2, align=False)
		subcolsLeft = subcols.column()
		subcolsLeft.label(" ") # dummy
		subcolsLeft.label(" ") # dummy
		subcolsRight = subcols.column()
		# Replace existing shape key
		rowCon1 = subcolsRight.row()
		rowCon1.prop(self, "opt_delete_shapekey1_on_finish", text="Delete Shape Key 1 when done")
		rowCon1.enabled = (self.opt_output == "replace2" or self.opt_output == "new")
		rowCon2 = subcolsRight.row()
		rowCon2.prop(self, "opt_delete_shapekey2_on_finish", text="Delete Shape Key 2 when done")
		rowCon2.enabled = (self.opt_output == "replace1" or self.opt_output == "new")
		# New shape key
		colCon1 = gOutput.column()
		if (self.opt_output == "new"):
			colCon1.label("New Shape Key Name:")
			colCon1.prop(self, "opt_output_newname", text="")
	
	def validate(self, context):
		obj = context.object
		
		# Object must be a mesh
		if (obj.type != "MESH"):
			self.report({'ERROR'}, "The active object ('" + obj.name + "', type: " + obj.type + ") is not a mesh!")
			return False
		
		# Object must have enough shape keys
		if (not hasattr(obj.data.shape_keys, "key_blocks") or len(obj.data.shape_keys.key_blocks.keys()) <= 2):
			self.report({'ERROR'}, "The active object must have at least 2 shape keys (excluding the basis shape key).")
			return False
		
		return True
	
	def execute(self, context):
		scene = context.scene
		properties = scene.shape_key_tools_props
		
		if context.object:
			obj = context.object
			if (self.validate(context) == False):
				return {'FINISHED'}
			
			if (self.opt_shape_key_1 == self.opt_shape_key_2):
				self.report({'ERROR'}, "You cannot combine a shape key with itself.")
				return {'FINISHED'}
			
			dest = self.opt_output_newname
			if (self.opt_output == "replace1"):
				dest = 1
			elif (self.opt_output == "replace2"):
				dest = 2
			
			blendModeParams = None
			if (self.opt_blend_mode == "lerp"):
				blendModeParams = { "Factor": self.opt_blend_lerp_factor }
			
			vertexFilterParams = None
			if (properties.opt_global_enable_filterverts):
				vertexFilterParams = properties.getEnabledVertexFilterParams()
			
			main.MergeAndBlendShapeKeys(
				obj,
				obj.data.shape_keys.key_blocks[int(self.opt_shape_key_1, 10)].name,
				obj.data.shape_keys.key_blocks[int(self.opt_shape_key_2, 10)].name,
				dest,
				self.opt_blend_mode,
				blendModeParams = blendModeParams,
				vertexFilterParams = vertexFilterParams,
				delete1OnFinish = self.opt_delete_shapekey1_on_finish,
				delete2OnFinish = self.opt_delete_shapekey2_on_finish,
			)
		
		return{'FINISHED'}
	
	def invoke(self, context, event):
		scene = context.scene
		properties = scene.shape_key_tools_props
		
		if context.object:
			obj = context.object
			if (self.validate(context) == False):
				return {'FINISHED'}
			
			# Set Shape Key 1 to the active shape key
			activeShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(obj.active_shape_key.name)
			noShapeKeyWasActive = False
			if (activeShapeKeyIndex == 0): # no shape key active (idk how but it happens sometimes)
				noShapeKeyWasActive = True
				activeShapeKeyIndex = 1 # basis shape key active
			old = self.opt_shape_key_1
			self.opt_shape_key_1 = str(activeShapeKeyIndex)
			# If this changed the old value, then do some hueristics to auto pick an initial reasonable Shape Key 2
			if (self.opt_shape_key_1 != old or noShapeKeyWasActive):
				doNext = True
				
				# First see if Shape Key 1 is a L/R shape key with a corresponding opposite side shape key
				mergePairNames = main.FindShapeKeyMergeNames(obj.active_shape_key.name)
				if (mergePairNames[1] != None):
					expectedCompShapeKeyName = mergePairNames[1]
					for keyBlock in obj.data.shape_keys.key_blocks:
						if keyBlock.name == expectedCompShapeKeyName:
							self.opt_shape_key_2 = str(obj.data.shape_keys.key_blocks.keys().index(keyBlock.name))
							doNext = False
							break
				
				# If no hueristic matched, default to the shape key immediately after Shape Key 1 (or immediately before, if Shape Key 1 is the very last one) (or the same, if only 1 non-basis shape key exists)
				if (doNext):
					sk1Index = int(self.opt_shape_key_1, 10)
					if (sk1Index == len(obj.data.shape_keys.key_blocks.keys()) - 1):
						self.opt_shape_key_2 = str(sk1Index - 1)
					elif (len(obj.data.shape_keys.key_blocks.keys()) <= 2):
						self.opt_shape_key_2 = str(sk1Index)
					else:
						self.opt_shape_key_2 = str(sk1Index + 1)
				
			# Launch the op
			return context.window_manager.invoke_props_dialog(self, width=600)


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
	def poll(self,context):
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
		if (obj == None or obj.type != "MESH" or not hasattr(obj.data.shape_keys, "key_blocks") or len(obj.data.shape_keys.key_blocks.keys()) <= 1):
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

def register():
	global UiIconsExtra
	
	UiIconsExtra = bpy.utils.previews.new()
	iconDir = os.path.join(os.path.dirname(__file__), "icons")
	for filename in os.listdir(iconDir):
		if (filename[-4:] == ".png"):
			UiIconsExtra.load(filename[:-4], os.path.join(iconDir, filename), "IMAGE")
			
	bpy.utils.register_module(__name__)
	bpy.types.Scene.shape_key_tools_props = PointerProperty(type=ShapeKeyTools_Properties)

def unregister():
	global UiIconsExtra
	
	bpy.utils.previews.remove(UiIconsExtra)
	
	del bpy.types.Scene.shape_key_tools_props
	bpy.utils.unregister_module(__name__)
	

if __name__ == "__main__":
	register()
