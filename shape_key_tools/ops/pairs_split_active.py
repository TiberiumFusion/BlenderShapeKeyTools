import sys, os

import bpy
from bpy.props import *

from shape_key_tools import common


class WM_OT_ShapeKeyTools_OpSplitActivePair(bpy.types.Operator):
	bl_idname = "wm.shape_key_tools_split_active_pair"
	bl_label = "Split Active Shape Key"
	bl_description = "Splits the active shape key on the active mesh into two separate shape keys. The left and right halves are determined by your chosen split axis. This operation does NOT use the Vertex Filter!"
	bl_options = {"UNDO"}
	
	
	opt_delete_original = BoolProperty(
		name = "Delete Original Shape Key",
		description = "Delete the original shape key after creating the two new split shape keys.",
		default = True,
	)
	
	opt_clear_preview = BoolProperty(
		name = "Clear Live Preview if Enabled",
		description = "Disable the pair split preview after splitting if it is currently enabled.",
		default = True,
	)
	
	
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
		
		# Determine the names for the two new (half) shape keys
		oldName = obj.active_shape_key.name
		(splitLName, splitRName, usesPlusConvention) = common.FindShapeKeyPairSplitNames(oldName, validateWith=obj)
		if (usesPlusConvention == False): # shape key name is not in MyShapeKeyL+MyShapeKeyR format
			self.report({'INFO'}, "Shape key '" + obj.active_shape_key.name + "' does not use the 'MyShapeKeyL+MyShapeKeyR' naming convention!")
		
		# Split the active shape key
		smoothingDistance = properties.opt_shapepairs_split_smoothdist
		if (properties.opt_shapepairs_split_mode == "sharp"):
			smoothingDistance = 0
		common.SplitPairActiveShapeKey(obj, properties.opt_shapepairs_split_axis, splitLName, splitRName, smoothingDistance, self.opt_delete_original)
		self.report({'INFO'}, "Split shape key '" + oldName + "' into left: '"  + splitLName + "' and right: '" + splitRName + "'")
		
		# If the user was previewing this split, disable the preview now and make active the shape key side that was being previewed (L or R)
		if (self.opt_clear_preview):
			if (properties.opt_shapepairs_splitmerge_preview_split_left):
				obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(splitLName)
			elif (properties.opt_shapepairs_splitmerge_preview_split_right):
				obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(splitRName)
			properties.opt_shapepairs_splitmerge_preview_split_left = False
			properties.opt_shapepairs_splitmerge_preview_split_right = False
		
		return {'FINISHED'}

	
def register():
	bpy.utils.register_class(WM_OT_ShapeKeyTools_OpSplitActivePair)
	return WM_OT_ShapeKeyTools_OpSplitActivePair

def unregister():
	bpy.utils.unregister_class(WM_OT_ShapeKeyTools_OpSplitActivePair)
	return WM_OT_ShapeKeyTools_OpSplitActivePair

if (__name__ == "__main__"):
	register()
