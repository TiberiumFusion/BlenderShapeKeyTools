import sys, os

import bpy
from bpy.props import *

from shape_key_tools import common


class WM_OT_ShapeKeyTools_OpMergeAllPairs(bpy.types.Operator):
	bl_idname = "wm.shape_key_tools_smartmerge_all_pairs"
	bl_label = "Smart Merge All Shape Keys"
	bl_description = "Merges all shape keys pairs on the active mesh into single left+right shape keys. Only shape keys that use the 'MyShapeKeyL' 'MyShapeKeyR' naming convention will be merged. This operation does NOT use the Vertex Filter!"
	bl_options = {"UNDO"}
	
	
	opt_run_async = BoolProperty(
		name = "Run as Modal",
		description = "When true, this modal operator runs normally (asynchronously). When false, this operator will block and run synchronously.",
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
	
	
	### Persistent op data
	_Timer = None
	
	_Obj = None
	_MergeAxis = None
	_MergeMode = None
	_MergeBatch = []
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
		
		# Merge all shape keys that have the MyShapeKeyL MyShapeKeyR naming convention AND have a complementary shape key to merge with
		# Example: "HappyL" and "HappyR" becomes "HappyL+HappyR"
		seen = {}
		self._MergeBatch = []
		for keyBlock in obj.data.shape_keys.key_blocks:
			if (not keyBlock.name in seen):
				(firstShapeKey, expectedCompShapeKey, mergedShapeKey) = common.FindShapeKeyMergeNames(keyBlock.name, validateWith=obj)
				if (expectedCompShapeKey != None and expectedCompShapeKey in obj.data.shape_keys.key_blocks.keys() and not expectedCompShapeKey in seen):
					if (keyBlock.name[-1] == "L"):
						self._MergeBatch.append((firstShapeKey, expectedCompShapeKey, mergedShapeKey))
					else:
						self._MergeBatch.append((expectedCompShapeKey, firstShapeKey, mergedShapeKey))
					seen[firstShapeKey] = True
					seen[expectedCompShapeKey] = True
		
		# Prepare for the modal execution stage
		if (len(self._MergeBatch) > 0):
			self._Obj = obj
			self._MergeAxis = properties.opt_shapepairs_split_axis
			self._MergeMode = properties.opt_shapepairs_merge_mode
			self._CurBatchNum = 0
			self._CurVert = 0
			self._TotalVerts = len(obj.data.vertices) * len(self._MergeBatch)
			self._ModalWorkPacing = 0
			
			self.preport("Preparing to merge " + str(len(self._MergeBatch) * 2) + " of " + str(len(obj.data.shape_keys.key_blocks)) + " total shape keys")
			
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
	
	# Merge one shape key at a time per modal event
	def modal(self, context, event):
		if (event.type == "TIMER"):
			if (self.modalStep(context)): # modalStep only returns True when all work is done
				return {"CANCELLED"}
			else:
				return {"PASS_THROUGH"}
		
		return {"PASS_THROUGH"}
	
	def modalStep(self, context):
		obj = self._Obj
		
		(leftKey, rightKey, mergedName) = self._MergeBatch[self._CurBatchNum]
		
		# If we do work every modal() event (or even every 2nd or 3rd), the Blender UI will not update
		# So we always wait a few modal pulses after finishing the last work segment before doing the next work segment
		if (self._ModalWorkPacing == 0): # notify
			# The UI needs one full update cycle after self.report() to display it, so we do this one modal event *before* the actual work
			self.preport("Merging shape key pair " + str(self._CurBatchNum + 1) + "/" + str(len(self._MergeBatch)) + " '" + leftKey + "' and '" + rightKey + "' into '" + mergedName + "'")
			
		elif (self._ModalWorkPacing == 1): # work
			# Persistent parameters for all shape key merges
			obj = self._Obj
			axis = self._MergeAxis
			mergeMode = self._MergeMode
			
			# Create async progress reporting data so the merge method can report progress to the window manager's progress cursor
			asyncProgressReporting = {
				"CurrentVert": self._CurVert,
				"TotalVerts": self._TotalVerts,
			}
			
			# Merge the two victim shape keys
			common.MergeShapeKeyPair(obj, axis, leftKey, rightKey, mergedName, mergeMode, asyncProgressReporting=asyncProgressReporting)
			
			# Finalize this segment of the async work
			self._CurVert = asyncProgressReporting["CurrentVert"]
			self._CurBatchNum += 1
			
			if (self._CurBatchNum > len(self._MergeBatch) - 1):
				# All work completed
				bpy.context.window_manager.progress_end()
				self.cancel(context)
				self.preport("All shape keys pairs merged.")
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
	bpy.utils.register_class(WM_OT_ShapeKeyTools_OpMergeAllPairs)
	return WM_OT_ShapeKeyTools_OpMergeAllPairs

def unregister():
	bpy.utils.unregister_class(WM_OT_ShapeKeyTools_OpMergeAllPairs)
	return WM_OT_ShapeKeyTools_OpMergeAllPairs

if (__name__ == "__main__"):
	register()
