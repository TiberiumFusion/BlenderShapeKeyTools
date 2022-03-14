import sys, os

import bpy
from bpy.props import *

from shape_key_tools import common


class WM_OT_ShapeKeyTools_OpMergeActive(bpy.types.Operator):
	bl_idname = "wm.shape_key_tools_smartmerge_active"
	bl_label = "Smart Merge Active Shape Key"
	bl_description = "Merges the active mesh's active shape key with its counterpart pair shape key. E.g. MyShapeKeyL will be merged with MyShapeKeyR into a single shape key named MyShapeKeyL+MyShapeKeyR. This operation does NOT use the Vertex Filter!"
	bl_options = {"UNDO"}
	
	
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
			
		# The active shape key's name must adhere to the MyShapeKeyL MyShapeKeyR naming convention
		(firstShapeKey, expectedCompShapeKeyName, mergedShapeKeyName) = common.FindShapeKeyMergeNames(obj.active_shape_key.name)
		if (expectedCompShapeKeyName == None):
			return (False, "The active shape key does not follow the MyShapeKeyL MyShapeKeyR naming convention. This operation only works on shape keys that end in L or R.")
		
		# A complementary shape key must exist
		if (not expectedCompShapeKeyName in obj.data.shape_keys.key_blocks.keys()):
			return (False, "No complementary shape key named '" + expectedCompShapeKeyName + "' exists.")
			
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
		
		# Find the name of the complementary shape key and the name of the to-be-merged shape key
		(firstShapeKey, expectedCompShapeKey, mergedShapeKey) = common.FindShapeKeyMergeNames(obj.active_shape_key.name, validateWith=obj)
		
		# Merge em
		if (firstShapeKey[-1] == "L"):
			common.MergeShapeKeyPair(obj, properties.opt_shapepairs_split_axis, firstShapeKey, expectedCompShapeKey, mergedShapeKey, properties.opt_shapepairs_merge_mode)
		else:
			common.MergeShapeKeyPair(obj, properties.opt_shapepairs_split_axis, expectedCompShapeKey, firstShapeKey, mergedShapeKey, properties.opt_shapepairs_merge_mode)
		self.report({'INFO'}, "Merged shape key '" + firstShapeKey + "' with '"  + expectedCompShapeKey + "' to create new '" + mergedShapeKey + "'")
		
		return {'FINISHED'}

	
def register():
	bpy.utils.register_class(WM_OT_ShapeKeyTools_OpMergeActive)
	return WM_OT_ShapeKeyTools_OpMergeActive

def unregister():
	bpy.utils.unregister_class(WM_OT_ShapeKeyTools_OpMergeActive)
	return WM_OT_ShapeKeyTools_OpMergeActive

if (__name__ == "__main__"):
	register()
