import sys, os

import bpy
from bpy.props import *

from shape_key_tools import common


class WM_OT_ShapeKeyTools_OpCombineTwo(bpy.types.Operator):
	bl_idname = "wm.shape_key_tools_combine_two"
	bl_label = "Combine Two Shape Keys"
	bl_description = "Combines any two shape keys with various options for blending the two shape keys' deltas together. If the Vertex Filter is enabled, the deltas will be filtered before blending."
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
		# This op requires an active object
		if (context.object == None or hasattr(context, "object") == False):
			return (False, "No object is selected.")
			
		obj = context.object
		
		# Object must be a mesh
		if (obj.type != "MESH"):
			return (False, "The active object ('" + obj.name + "', type: " + obj.type + ") is not a mesh.")
		
		# Object must have enough shape keys
		if (not hasattr(obj.data.shape_keys, "key_blocks") or len(obj.data.shape_keys.key_blocks.keys()) <= 2):
			return (False, "The active object must have at least 2 shape keys (excluding the basis shape key).")
		
		return (True, None)
		
	def validateUser(self, context):
		(isValid, invalidReason) = self.validate(context)
		if (isValid):
			return True
		else:
			if self:
				self.report({'ERROR'}, invalidReason)
			return False
	
	@classmethod
	def poll(cls, context):
		(isValid, invalidReason) = cls.validate(None, context)
		return isValid
	
	
	def execute(self, context):
		scene = context.scene
		properties = scene.shape_key_tools_props
		
		if (self.validateUser(context) == False):
			return {'FINISHED'}
		
		obj = context.object
		
		if (self.opt_shape_key_1 == self.opt_shape_key_2):
			self.report({'ERROR'}, "You cannot combine a shape key with itself.")
			return {'FINISHED'}
		
		dest = self.opt_output_newname
		if (self.opt_output == "replace1"):
			dest = 1
		elif (self.opt_output == "replace2"):
			dest = 2
		
		# Build blend mode param dict
		blendModeParams = None
		if (self.opt_blend_mode == "lerp"):
			blendModeParams = { "Factor": self.opt_blend_lerp_factor }
		
		# Build vertex filter param dict
		vertexFilterParams = None
		if (properties.opt_global_enable_filterverts):
			vertexFilterParams = properties.getEnabledVertexFilterParams()
		
		# Blend and merge
		common.MergeAndBlendShapeKeys(
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
		
		if (self.validateUser(context) == False):
			return {'FINISHED'}
		
		obj = context.object
			
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
			(firstShapeKey, expectedCompShapeKey, mergedShapeKey) = common.FindShapeKeyMergeNames(obj.active_shape_key.name)
			if (expectedCompShapeKey != None):
				if (expectedCompShapeKey in obj.data.shape_keys.key_blocks.keys()):
					self.opt_shape_key_2 = str(obj.data.shape_keys.key_blocks.keys().index(expectedCompShapeKey))
					doNext = False
			
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

	
def register():
	bpy.utils.register_class(WM_OT_ShapeKeyTools_OpCombineTwo)
	return WM_OT_ShapeKeyTools_OpCombineTwo

def unregister():
	bpy.utils.unregister_class(WM_OT_ShapeKeyTools_OpCombineTwo)
	return WM_OT_ShapeKeyTools_OpCombineTwo

if (__name__ == "__main__"):
	register()
