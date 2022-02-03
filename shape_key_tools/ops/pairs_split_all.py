import sys, os

import bpy
from bpy.props import *

from shape_key_tools import common


class WM_OT_ShapeKeyTools_OpSplitAllPairs(bpy.types.Operator):
	bl_idname = "wm.shape_key_tools_split_all_pairs"
	bl_label = "Split All Paired Shape Keys"
	bl_description = "Splits ALL paired shape keys (i.e. shape keys with names like 'MyShapeKeyL+MyShapeKeyR') on the active mesh into two separate shape keys. The left and right halves are determined by your chosen split axis. This operation does NOT use the Vertex Filter!"
	bl_options = {"UNDO"}
	
	
	# report() doesnt print to console when running inside modal() for some weird reason
	# So we have to do that manually
	def preport(self, message):
		print(message)
		self.report({'INFO'}, message)
		
	
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
	
	
	### Persistent op data
	_Timer = None
	
	_Obj = None
	_SplitAxis = None
	_SplitBatch = []
	_CurBatchNum = 0
	_CurVert = 0
	_TotalVerts = 0
	_ModalWorkPacing = 0
	
	
	def execute(self, context):
		scene = context.scene
		properties = scene.shape_key_tools_props
		
		if (self.validateUser(context) == False):
			return {'FINISHED'}
		
		obj = context.object
		
		# Split all shapekeys with the MyShapeKeyL MyShapeKeyR naming convention
		# Examples:
		# - "HappyL+HappyR" becomes HappyL and HappyR
		# - "HappyL+UnhappyR" becomes HappyL and UnhappyR (works, but bad names, cannot recombine later)
		# - "Happyl+happyR" becomes "Happyl" and "happyR" (works, but bad names, cannot recombine later)
		self._SplitBatch = []
		for keyBlock in obj.data.shape_keys.key_blocks:
			(splitLName, splitRName, usesPlusConvention) = common.FindShapeKeyPairSplitNames(keyBlock.name, validateWith=obj)
			if (splitLName != None and splitRName != None and usesPlusConvention == True):
				self._SplitBatch.append((keyBlock.name, splitLName, splitRName))
		
		# Prepare for the modal execution stage
		if (len(self._SplitBatch) > 0):
			self._Obj = obj
			self._SplitAxis = properties.opt_shapepairs_split_axis
			self._CurBatchNum = 0
			self._CurVert = 0
			self._TotalVerts = len(obj.data.vertices) * len(self._SplitBatch)
			self._ModalWorkPacing = 0
			
			context.window_manager.modal_handler_add(self)
			self._Timer = context.window_manager.event_timer_add(0.1, context.window)
			context.window_manager.progress_begin(0, self._TotalVerts)
			
			self.report({'INFO'}, "Preparing to split " + str(len(self._SplitBatch)) + " of " + str(len(obj.data.shape_keys.key_blocks)) + " total shape keys")
			return {"RUNNING_MODAL"}
			
		else:
			return {"FINISHED"}
	
	# Split one shape key at a time per modal event
	def modal(self, context, event):
		if event.type == "TIMER":
			obj = self._Obj
			
			(oldName, splitLName, splitRName) = self._SplitBatch[self._CurBatchNum]
			
			# If we do work every modal() event (or even every 2nd or 3rd), the Blender UI will not update
			# So we always wait a few modal pulses after finishing the last work segment before doing the next work segment
			if (self._ModalWorkPacing == 0): # notify
				# The UI needs one full update cycle after self.report() to display it, so we do this one modal event *before* the actual work
				self.preport("Splitting shape key " + str(self._CurBatchNum + 1) + "/" + str(len(self._SplitBatch)) + " '" + oldName + "' into left: '" + splitLName + "' and right: '" + splitRName + "'")
				
			elif (self._ModalWorkPacing == 1): # work
				# Persistent parameters for all shape key splits
				axis = self._SplitAxis
				
				# Create async progress reporting data so the split method can report progress to the window manager's progress cursor
				asyncProgressReporting = {
					"CurrentVert": self._CurVert,
					"TotalVerts": self._TotalVerts,
				}
				
				# Make the victim shape key active and split it
				obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(oldName)
				common.SplitPairActiveShapeKey(obj, axis, splitLName, splitRName, asyncProgressReporting=asyncProgressReporting)
				
				# Finalize this segment of the async work
				self._CurVert = asyncProgressReporting["CurrentVert"]
				self._CurBatchNum += 1
				
				if (self._CurBatchNum > len(self._SplitBatch) - 1):
					# All work completed
					bpy.context.window_manager.progress_end()
					self.cancel(context)
					self.preport("All shape keys pairs split.")
					return {"CANCELLED"}
				#else: # Need to do more work in the next modal
				
			#else: # rest
			
			self._ModalWorkPacing += 1
			if (self._ModalWorkPacing > 3):
				self._ModalWorkPacing = 0
		
		return {"PASS_THROUGH"}
	
	def cancel(self, context):
		if (self._Timer != None):
			context.window_manager.event_timer_remove(self._Timer)
		self._Timer = None

	
def register():
	bpy.utils.register_class(WM_OT_ShapeKeyTools_OpSplitAllPairs)
	return WM_OT_ShapeKeyTools_OpSplitAllPairs

def unregister():
	bpy.utils.unregister_class(WM_OT_ShapeKeyTools_OpSplitAllPairs)
	return WM_OT_ShapeKeyTools_OpSplitAllPairs

if (__name__ == "__main__"):
	register()
