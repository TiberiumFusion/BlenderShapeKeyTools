import sys, os

import bpy
from bpy.props import *

from shape_key_tools import common


class WM_OT_ShapeKeyTools_OpSplitAllPairs(bpy.types.Operator):
	bl_idname = "wm.shape_key_tools_split_all_pairs"
	bl_label = "Split All Paired Shape Keys"
	bl_description = "Splits ALL paired shape keys (i.e. shape keys with names like 'MyShapeKeyL+MyShapeKeyR') on the active mesh into two separate shape keys. The left and right halves are determined by your chosen split axis. This operation does NOT use the Vertex Filter!"
	bl_options = {"UNDO"}
	
	
	opt_run_async = BoolProperty(
		name = "Run as Modal",
		description = "When true, this modal operator runs normally (asynchronously). When false, this operator will block and run synchronously.",
		default = True,
	)
	
	
	opt_delete_originals = BoolProperty(
		name = "Delete Original Shape Keys",
		description = "Delete the original shape keys after creating each pair of new split shape keys.",
		default = True,
	)
	
	opt_clear_preview = BoolProperty(
		name = "Clear Live Preview if Enabled",
		description = "Disable the pair split preview after splitting if it is currently enabled.",
		default = True,
	)
	
	
	# report() doesnt print to console when running inside modal() for some weird reason
	# So we have to do that manually
	def preport(self, message):
		print(message)
		if (self.opt_run_async):
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
	_SmoothingDistance = 0
	_SplitBatch = []
	_CurBatchNum = 0
	_CurVert = 0
	_TotalVerts = 0
	_ModalWorkPacing = 0
	
	
	def invoke(self, context, event):
		if (event.shift):
			return context.window_manager.invoke_props_dialog(self, width=500)
		else:
			return self.execute(context)
	
	
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
			self._SmoothingDistance = properties.opt_shapepairs_split_smoothdist
			if (properties.opt_shapepairs_split_mode == "sharp"):
				self._SmoothingDistance = 0
			self._CurBatchNum = 0
			self._CurVert = 0
			self._TotalVerts = len(obj.data.vertices) * len(self._SplitBatch)
			self._ModalWorkPacing = 0
			
			# If the user was previewing this split, disable the preview now
			if (self.opt_clear_preview):
				properties.opt_shapepairs_splitmerge_preview_split_left = False
				properties.opt_shapepairs_splitmerge_preview_split_right = False
			
			self.preport("Preparing to split " + str(len(self._SplitBatch)) + " of " + str(len(obj.data.shape_keys.key_blocks)) + " total shape keys")
			
			context.window_manager.progress_begin(0, self._TotalVerts)
			
			if (self.opt_run_async):
				context.window_manager.modal_handler_add(self)
				self._Timer = context.window_manager.event_timer_add(0.01, context.window)
				return {"RUNNING_MODAL"}
			else:
				modalComplete = None
				while (not modalComplete):
					modalComplete = self.modalStep(context)
				return {"FINISHED"}
			
		else:
			return {"FINISHED"}
	
	# Split one shape key at a time per modal event
	def modal(self, context, event):
		if (event.type == "TIMER"):
			if (self.modalStep(context)): # modalStep only returns True when all work is done
				return {"CANCELLED"}
			else:
				return {"PASS_THROUGH"}
		
		return {"PASS_THROUGH"}
	
	def modalStep(self, context):
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
			smoothingDistance = self._SmoothingDistance
			
			# Create async progress reporting data so the split method can report progress to the window manager's progress cursor
			asyncProgressReporting = {
				"CurrentVert": self._CurVert,
				"TotalVerts": self._TotalVerts,
			}
			
			# Make the victim shape key active and split it
			obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(oldName)
			common.SplitPairActiveShapeKey(obj, axis, splitLName, splitRName, smoothingDistance, self.opt_delete_originals, asyncProgressReporting=asyncProgressReporting)
			
			# Finalize this segment of the async work
			self._CurVert = asyncProgressReporting["CurrentVert"]
			self._CurBatchNum += 1
			
			if (self._CurBatchNum > len(self._SplitBatch) - 1):
				# All work completed
				bpy.context.window_manager.progress_end()
				self.cancel(context)
				self.preport("All shape keys pairs split.")
				return True
			
			#else: # Need to do more work in the next modal
			
		#else: # rest
		
		self._ModalWorkPacing += 1
		if (self._ModalWorkPacing > 3):
			self._ModalWorkPacing = 0
	
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
