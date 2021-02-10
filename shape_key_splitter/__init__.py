bl_info = {
	"name": "Shape Key Splitter",
	"author": "TiberiumFusion",  
	"version": (1, 0, 0, 1),
	"blender": (2, 78, 0),
	"location": "Object > Tools > Shape Key Splitter",
	"description": "Splits and merges shape keys on axis boundaries. Useful for separating and combining the left and right halves of expressions.",
	"wiki_url": "https://github.com/TiberiumFusion/BlenderShapeKeySplitter",
	"tracker_url": "https://github.com/TiberiumFusion/BlenderShapeKeySplitter/issues",
	"warning": "",
	"category": "Tools",
}

import bpy
from bpy.props import *
from . import splitter

class ShapeKeySplitter_Properties(bpy.types.PropertyGroup):
	opt_split_axis = EnumProperty(
		name = "Split Axis",
		description = "Choose the axis boundary for splitting/merging shape keys.",
		items = [
			("+X", "+X", "Split/merge shape keys into a +X half and a -X half. +X is the left side and -X is the right side. Pick this if your character faces -Y"),
			("+Y", "+Y", "Split/merge shape keys into a +Y half and a -Y half. +Y is the left side and -Y is the right side. Pick this if your character faces +X"),
			("+Z", "+Z", "Split/merge shape keys into a +Z half and a -Z half. +Z is the left side and -Z is the right side."),
			("-X", "-X", "Split/merge shape keys into a -X half and a +X half. -X is the left side and +X is the right side. Pick this if your character faces +Y"),
			("-Y", "-Y", "Split/merge shape keys into a -Y half and a +Y half. -Y is the left side and +Y is the right side. Pick this if your character faces -X"),
			("-Z", "-Z", "Split/merge shape keys into a -Z half and a +Z half. -Z is the left side and +Z is the right side."),
		]
	)

class WM_OT_ShapeKeySplitter_OpSplitSelected(bpy.types.Operator):
	bl_idname = "wm.shape_key_splitter_split_selected"
	bl_label = "Split Selected Shape Key"
	bl_description = "Splits the currently selected shape key on the current mesh into two individual shape keys, a left and right half."
	bl_options = {"UNDO"}

	def execute(self, context):
		scene = context.scene
		properties = scene.shape_key_splitter
		
		if context.object:
			currentShapeKeyIndex = context.object.data.shape_keys.key_blocks.keys().index(context.object.active_shape_key.name)
			newNameData = splitter.FindShapeKeySplitNames(context.object.active_shape_key.name)
			splitter.SplitSelectedShapeKey(context.object, properties.opt_split_axis, newNameData[0], newNameData[1])
			context.object.active_shape_key_index = currentShapeKeyIndex # reselect the shape key at the original's index (will be the left split shape key)
		
		return{'FINISHED'}
	
class WM_OT_ShapeKeySplitter_OpSplitAllPairs(bpy.types.Operator):
	bl_idname = "wm.shape_key_splitter_split_all_pairs"
	bl_label = "Split All Paired Shape Keys"
	bl_description = "Splits all shape keys on the current mesh into left and right halves."
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

	def execute(self, context):				
		self._scene = context.scene
		self._properties = self._scene.shape_key_splitter
		
		if context.object:
			# Get async operation data
			self._asyncWorkData = splitter.SplitAllShapeKeyPairsAsync(context.object, self._properties.opt_split_axis)
			
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
		

class WM_OT_ShapeKeySplitter_OpMergeSelected(bpy.types.Operator):
	bl_idname = "wm.shape_key_splitter_merge_selected"
	bl_label = "Smart Merge Selected Shape Key"
	bl_description = "Merges the selected shape key with its opposite side shapekey. E.g. if you select MyShapeKeyL and click this button, MyShapeKeyL will be merged with MyShapeKeyR (if it exists) into a single shape key named MyShapeKeyL+MyShapeKeyR"
	bl_options = {"UNDO"}

	def execute(self, context):
		scene = context.scene
		properties = scene.shape_key_splitter
		
		if context.object:
			currentShapeKeyIndex = context.object.data.shape_keys.key_blocks.keys().index(context.object.active_shape_key.name)
			splitter.MergeSelectedShapeKey(context.object, properties.opt_split_axis)
			context.object.active_shape_key_index = currentShapeKeyIndex # reselect the shape key at the original's index (will be new merged shape key)
		
		return{'FINISHED'}
	
class WM_OT_ShapeKeySplitter_OpMergeAllPairs(bpy.types.Operator):
	bl_idname = "wm.shape_key_splitter_merge_all_pairs"
	bl_label = "Smart Merge All Shape Keys Pairs"
	bl_description = "Merges all shape keys pairs on the current mesh into single left+right shape keys."
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

	def execute(self, context):				
		self._scene = context.scene
		self._properties = self._scene.shape_key_splitter
		
		if context.object:
			# Get async operation data
			self._asyncWorkData = splitter.MergeAllShapeKeyPairsAsync(context.object, self._properties.opt_split_axis)
			
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
		

class OBJECT_PT_ShapeKeySplitter_Panel(bpy.types.Panel):
	bl_label = "Shape Key Splitter"
	bl_idname = "OBJECT_PT_shape_key_splitter_panel"
	bl_space_type = "VIEW_3D" 
	bl_region_type = "TOOLS"
	bl_category = "Tools"
	bl_context = "objectmode"
	bl_options = {"DEFAULT_CLOSED"}
	
	@classmethod
	def poll(self,context):
		return context.object is not None
		
	def draw(self, context):
		scene = context.scene
		properties = scene.shape_key_splitter
	
		layout = self.layout
		layout.label("Split")
		layout.operator("wm.shape_key_splitter_split_selected")
		layout.operator("wm.shape_key_splitter_split_all_pairs")
		layout.label("Merge")
		layout.operator("wm.shape_key_splitter_merge_selected")
		layout.operator("wm.shape_key_splitter_merge_all_pairs")
		layout.label("Split/Merge Axis")
		layout.prop(properties, "opt_split_axis", "")

def register():
	bpy.utils.register_module(__name__)
	bpy.types.Scene.shape_key_splitter = PointerProperty(type=ShapeKeySplitter_Properties)

def unregister():
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()