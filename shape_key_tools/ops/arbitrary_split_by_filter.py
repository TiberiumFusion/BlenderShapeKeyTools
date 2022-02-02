import sys, os

import bpy
from bpy.props import *

from shape_key_tools import common


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
		info = topBody.box().column()
		info.label("Verts with RED deltas will be preserved in the new shape key.")
		info.label("Verts with BLACK deltas will revert to their basis position in the new shape key.")
		
		optsBox = topBody.box().column()
		optsBox.prop(self, "opt_mode", text="Mode")
		optsBox.prop(self, "opt_new_shape_key_name", text="New Shape Key Name:")
	
	
	def validate(self, context):
		# This op requires an active object
		if (context.object == None or hasattr(context, "object") == False):
			return (False, "No object is selected.")
			
		obj = context.object
		
		# Object must be a mesh
		if (obj.type != "MESH"):
			return (False, "The active object ('" + obj.name + "', type: " + obj.type + ") is not a mesh.")
		
		# Object must have enough shape keys
		if (not hasattr(obj.data.shape_keys, "key_blocks") or len(obj.data.shape_keys.key_blocks.keys()) <= 1):
			return (False, "The active object must have at least 1 shape key (excluding the basis shape key).")
		
		# Active shape key cannot be the basis shape key
		activeShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(obj.active_shape_key.name)
		if (activeShapeKeyIndex == 0):
			return (False, "You cannot split the basis shape key.")
		
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
		
		# Build the vertex filter parameter dict
		vertexFilterParams = None
		if (properties.opt_global_enable_filterverts):
			vertexFilterParams = properties.getEnabledVertexFilterParams()
		
		# Do the split
		common.SplitFilterActiveShapeKey(obj,  self.opt_new_shape_key_name, self.opt_mode, vertexFilterParams)
		
		return {'FINISHED'}
	
	def invoke(self, context, event):
		scene = context.scene
		properties = scene.shape_key_tools_props
		
		if (self.validateUser(context) == False):
			return {'FINISHED'}
		
		obj = context.object
		
		# Default options
		self.opt_new_shape_key_name = obj.active_shape_key.name + "__SPLIT"
		
		return context.window_manager.invoke_props_dialog(self, width=450)

	
def register():
	bpy.utils.register_class(WM_OT_ShapeKeyTools_OpSplitByFilter)
	return WM_OT_ShapeKeyTools_OpSplitByFilter

def unregister():
	bpy.utils.unregister_class(WM_OT_ShapeKeyTools_OpSplitByFilter)
	return WM_OT_ShapeKeyTools_OpSplitByFilter

if (__name__ == "__main__"):
	register()
