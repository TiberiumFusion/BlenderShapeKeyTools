import sys, os

import bpy
from bpy.props import *

from shape_key_tools import common


class ShapeKeyTools_ApplyModifiersToShapeKeys_OptListItem(bpy.types.PropertyGroup):
	type = StringProperty()
	is_compatible = BoolProperty()
	do_apply = BoolProperty()
	
	is_visible_in_viewport = BoolProperty()
	def is_visible_in_viewport_readonly_get(self):
		return self.is_visible_in_viewport
	def is_visible_in_viewport_readonly_set(self, value):
		pass
	is_visible_in_viewport_readonly = BoolProperty(
		get = is_visible_in_viewport_readonly_get,
		set = is_visible_in_viewport_readonly_set,
	)


ModifierTypeInfo = {
	# modifier type name: (icon name, is compatible with this operation)
	"DATA_TRANSFER": ("MOD_DATA_TRANSFER", True),
	"MESH_CACHE": ("MOD_MESHDEFORM", False),
	"MESH_SEQUENCE_CACHE": ("MOD_MESHDEFORM", False),
	"NORMAL_EDIT": ("MOD_NORMALEDIT", False),
	"UV_PROJECT": ("MOD_UVPROJECT", True),
	"UV_WARP": ("MOD_UVPROJECT", True),
	"VERTEX_WEIGHT_EDIT": ("MOD_VERTEX_WEIGHT", True),
	"VERTEX_WEIGHT_MIX": ("MOD_VERTEX_WEIGHT", True),
	"VERTEX_WEIGHT_PROXIMITY": ("MOD_VERTEX_WEIGHT", True),
	
	"ARRAY": ("MOD_ARRAY", False),
	"BEVEL": ("MOD_BEVEL", False),
	"BOOLEAN": ("MOD_BOOLEAN", False),
	"BUILD": ("MOD_BUILD", False),
	"DECIMATE": ("MOD_DECIM", False),
	"EDGE_SPLIT": ("MOD_EDGESPLIT", False),
	"MASK": ("MOD_MASK", False),
	"MIRROR": ("MOD_MIRROR", False),
	"MULTIRES": ("MOD_MULTIRES", False),
	"REMESH": ("MOD_REMESH", False),
	"SCREW": ("MOD_SCREW", False),
	"SKIN": ("MOD_SKIN", False),
	"SOLIDIFY": ("MOD_SOLIDIFY", False),
	"SUBSURF": ("MOD_SUBSURF", False),
	"TRIANGULATE": ("MOD_TRIANGULATE", False),
	"WIREFRAME": ("MOD_WIREFRAME", False),
	
	"ARMATURE": ("MOD_ARMATURE", True),
	"CAST": ("MOD_CAST", True),
	"CORRECTIVE_SMOOTH": ("MOD_SMOOTH", True),
	"CURVE": ("MOD_CURVE", True),
	"DISPLACE": ("MOD_DISPLACE", True),
	"HOOK": ("HOOK", True),
	"LAPLACIANSMOOTH": ("MOD_SMOOTH", True),
	"LAPLACIANDEFORM": ("MOD_MESHDEFORM", True),
	"LATTICE": ("MOD_LATTICE", True),
	"MESH_DEFORM": ("MOD_MESHDEFORM", True),
	"SHRINKWRAP": ("MOD_SHRINKWRAP", True),
	"SIMPLE_DEFORM": ("MOD_SIMPLEDEFORM", True),
	"SMOOTH": ("MOD_SMOOTH", True),
	"SURFACE_DEFORM": ("MOD_MESHDEFORM", True),
	"WARP": ("MOD_WARP", True),
	"WAVE": ("MOD_WAVE", True),
	
	"CLOTH": ("MOD_CLOTH", False),
	"COLLISION": ("MOD_PHYSICS", False),
	"DYNAMIC_PAINT": ("MOD_DYNAMICPAINT", False),
	"EXPLODE": ("MOD_EXPLODE", False),
	"FLUID_SIMULATION": ("MOD_FLUIDSIM", False),
	"OCEAN": ("MOD_OCEAN", False),
	"PARTICLE_INSTANCE": ("MOD_PARTICLES", False),
	"PARTICLE_SYSTEM": ("MOD_PARTICLES", False),
	"SMOKE": ("MOD_SMOKE", False),
	"SOFT_BODY": ("MOD_SOFT", False),
}


class WM_OT_ShapeKeyTools_ApplyModifiersToShapeKeys(bpy.types.Operator):
	bl_idname = "wm.shape_key_tools_apply_modifiers_to_shape_keys"
	bl_label = "Apply Modifiers To Shape Keys"
	bl_description = "Applies compatible modifiers to the active mesh's base vertices and shape keys. Modifiers which change vertex count are incompatible. This operation does *not* use the Vertex Filter."
	bl_options = {"UNDO"}
	
	
	opt_modifiers = CollectionProperty(
		type = ShapeKeyTools_ApplyModifiersToShapeKeys_OptListItem,
		name = "Available Modifiers",
		description = "Choose which modifiers to apply to the base mesh and its shape keys."
	)
	
	
	# report() doesnt print to console when running inside modal() for some weird reason
	# So we have to do that manually
	def preport(self, message):
		print(message)
		self.report({'INFO'}, message)
		
	
	def draw(self, context):
		scene = context.scene
		properties = scene.shape_key_tools_props
		
		layout = self.layout
		topBody = layout.column()
		
		### Usage info
		topBody.label("Apply modifiers (in stack order) to the base mesh and all of its shape keys.")
		topBody.label("This operation may take a while, especially on detailed meshes.")
		for optListItem in self.opt_modifiers:
			if (optListItem.is_compatible == False):
				topBody.box().label("Modifiers that change vertex count cannot be applied.", icon="ERROR")
				break
		
		### List of modifiers
		gModifiers = topBody.box().column()
		# Modifier rows
		for optListItem in self.opt_modifiers:
			modifierTypeInfo = ModifierTypeInfo[optListItem.type]
			icon = modifierTypeInfo[0]
			cols = gModifiers.column_flow(columns=2, align=False)
			row1 = cols.row()
			row1.alignment = "LEFT"
			row1.prop(optListItem, "is_visible_in_viewport_readonly", icon="RESTRICT_VIEW_OFF", text="", emboss=True)
			row1.label(optListItem.name, icon=icon)
			row2 = cols.row()
			applyWrapper = row2.row()
			applyWrapper.alignment = "LEFT"
			if (optListItem.is_compatible == False):
				applyWrapper.enabled = False
				applyWrapper.prop(optListItem, "do_apply", text="Incompatible", icon="ERROR", emboss=False)
			else:
				applyWrapper.prop(optListItem, "do_apply", text="Apply Modifier", emboss=True)
	
	
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
	
	
	### Op helpers
	def deselectAll(self):
		for obj in bpy.data.objects:
			obj.select = False
	
	def activeSelect(self, context, obj):
		obj.select = True
		context.scene.objects.active = obj
	
	def singleSelect(self, context, obj):
		self.deselectAll()
		self.activeSelect(context, obj)
	
	
	### Persistent op data
	_Timer = None
	
	_Obj = None
	_ModifierApplyOrder = []
	_ShapeKeyDependencies = {}
	_ShapeKeyObj = None
	_CurWorkspaceObj = None
	_WorkStage = -1
	_WorkSubstage = -1
	_CurShapeKeyIndex = 0
	_TotalShapeKeys = 0
	
	
	def execute(self, context):
		scene = context.scene
		properties = scene.shape_key_tools_props
		
		if (self.validateUser(context) == False):
			return {'FINISHED'}
		
		obj = context.object
		
		### Do as much here as possible before we get into the modal work stages
		# Many bpy.ops require a full UI update cycle when run in modal() but not when run in execute(). Both execute and modal are synchronous, so I don't see why this is the case... Blender is inconsistent and weird. What else is new?
		# Ultimately, it means we have to juggle and spread out the work over an excessive amount of modal events
		
		# The chosen modifiers will be applied in stack order
		chosenModifiers = []
		for optListItem in self.opt_modifiers:
			if (optListItem.do_apply):
				chosenModifiers.append(optListItem.name)
		self._ModifierApplyOrder = []
		for modifier in obj.modifiers:
			if (modifier.name in chosenModifiers):
				self._ModifierApplyOrder.append(modifier.name)
		
		if (len(self._ModifierApplyOrder) > 0):
			self._ModalWorkPacing = 0
			self._WorkStage = 0
			self._WorkSubstage = 0
			self._Obj = obj
			self._TotalShapeKeys = len(obj.data.shape_keys.key_blocks.keys()) # includes the basis shape key!
			self._CurShapeKeyIndex = 0
			
			# Flatten the shape key dependency tree by making all shape keys relative to the first shape key (which *should* be the basis, but Blender does not enforce this... nothing we can do, sadly)
			self._ShapeKeyDependencies = {}
			for keyBlock in obj.data.shape_keys.key_blocks:
				self._ShapeKeyDependencies[keyBlock.name] = keyBlock.relative_key.name # keep track of the dependencies so we can restore them later
				keyIndex = obj.data.shape_keys.key_blocks.keys().index(keyBlock.name)
				if (keyIndex > 0):
					keyBlock.relative_key = obj.data.shape_keys.key_blocks[0] # "it just works" because setting relative_key makes blender recalculate the shape key deltas to be relative to the new local basis shape key
			
			# Duplicate the active object so we can separate its shape keys from its base mesh and work on them independently
			self.singleSelect(context, obj)
			bpy.ops.object.duplicate()
			self._ShapeKeyObj = context.scene.objects.active
			self._ShapeKeyObj.name = "_DELETE_ME__ " + obj.name + "__SKALL" # bold name in case the op fails and this doesnt get deleted and the user sees it
			
			# Set the active object's active shape key to what we need for the next modal event
			obj.active_shape_key_index = self._TotalShapeKeys - 1
			
			# Preemptively report what will happen in the next modal stage so we can save a modal event right off the bat
			self.report({'INFO'}, "Applying modifiers to base mesh")
			
			# Begin the next stage of work in the modal events
			context.window_manager.modal_handler_add(self)
			self._Timer = context.window_manager.event_timer_add(0.1, context.window)
			context.window_manager.progress_begin(0, self._TotalShapeKeys + 0.1)
			context.window_manager.progress_update(0.1)
			
			self.report({'INFO'}, "Preparing to apply " + str(len(self._ModifierApplyOrder)) + " modifiers to the base mesh + all " + str(self._TotalShapeKeys - 1) + " shape keys")
			return {"RUNNING_MODAL"}
			
		else:
			return {"FINISHED"}
	
	# Work on one shape key per modal event
	def modal(self, context, event):
		if event.type == "TIMER":
			obj = self._Obj
			skObj = self._ShapeKeyObj
			workspaceObj = self._CurWorkspaceObj
			
			# This operation is complex and procedes through several work stages that carefully distributes the work in order to appease modal()'s weird behavior oddities
			if (self._WorkStage == 0):
				### Very first modal event
				self.singleSelect(context, obj)
				
				# Remove all shape keys
				basisShapeKeyName = obj.data.shape_keys.key_blocks[0].name
				self.singleSelect(context, obj)
				for i in range(self._TotalShapeKeys):
					bpy.ops.object.shape_key_remove()
				
				# Apply the user's chosen modifiers to the base mesh
				for modifierName in self._ModifierApplyOrder:
					bpy.ops.object.modifier_apply(apply_as="DATA", modifier=modifierName)
				
				# Create the new basis shape key
				bpy.ops.object.shape_key_add()
				obj.data.shape_keys.key_blocks[0].name = basisShapeKeyName
				
				# On to the per-shape key work
				self._CurShapeKeyIndex = 1 # start the per-shape key work with the first "real" shape key (skip the basis shape key)
				self._WorkStage = 1
				self._WorkSubstage = 0
				context.window_manager.progress_update(1)
			
			elif (self._WorkStage == 1):
				### Process each shape key in turn
				# Substages here allow for UI update cycles to appease the Blender deities and rid us of the voodoo that happens in modal()
				curShapeKeyName = skObj.data.shape_keys.key_blocks[self._CurShapeKeyIndex].name
				
				if (self._WorkSubstage == 0):
					# Notify for the shape key we are about to process
					self.preport("Applying modifiers to shape key " + str(self._CurShapeKeyIndex) + "/" + str(self._TotalShapeKeys - 1) + " '" + curShapeKeyName + "'")
					
					# Set the active shape key index to that shape key
					skObj.active_shape_key_index = skObj.data.shape_keys.key_blocks.keys().index(curShapeKeyName)
					
					self._WorkSubstage = 1
					
				elif (self._WorkSubstage == 1):
					# Duplicate the shape key object
					self.singleSelect(context, skObj)
					bpy.ops.object.duplicate()
					workspaceObj = context.scene.objects.active
					workspaceObj.name = "_DELETE_ME__" + obj.name + "__SK_" + curShapeKeyName
					self._CurWorkspaceObj = workspaceObj
					
					# Move the shape key we are interested in to the end of the list
					self.singleSelect(context, workspaceObj)
					bpy.ops.object.shape_key_move(type="BOTTOM")
					
					# Set the active shape key in preparation for the next substage
					workspaceObj.active_shape_key_index = len(workspaceObj.data.shape_keys.key_blocks.keys()) - 2
					
					self._WorkSubstage = 2
				
				elif (self._WorkSubstage == 2):
					# Apply the active shape key to the base mesh
					self.singleSelect(context, workspaceObj)
					for i in range(len(workspaceObj.data.shape_keys.key_blocks.keys())):
						bpy.ops.object.shape_key_remove()
					
					# Apply the user's chosen modifiers to the base mesh
					for modifierName in self._ModifierApplyOrder:
						bpy.ops.object.modifier_apply(apply_as="DATA", modifier=modifierName)
					
					# Add the workspace obj back to the source object as a new shape key
					self.singleSelect(context, workspaceObj)
					self.activeSelect(context, obj)
					bpy.ops.object.join_shapes() # always puts the new shape key at the end of the list
					newShapeKey = obj.data.shape_keys.key_blocks[len(obj.data.shape_keys.key_blocks.keys()) - 1]
					newShapeKey.name = curShapeKeyName
					
					# Copy the original shape key's pose parameters to the new shape key
					origShapeKey = skObj.data.shape_keys.key_blocks[skObj.data.shape_keys.key_blocks.keys().index(curShapeKeyName)]
					newShapeKey.slider_min = origShapeKey.slider_min
					newShapeKey.slider_max = origShapeKey.slider_max
					newShapeKey.value = origShapeKey.value
					newShapeKey.interpolation = origShapeKey.interpolation
					newShapeKey.vertex_group = origShapeKey.vertex_group # this is a string, not a VertexGroup
					newShapeKey.mute = origShapeKey.mute
					# relative_key will be set in the final work segment
					
					# Delete the workspace object
					self.singleSelect(context, workspaceObj)
					bpy.ops.object.delete()
					
					# On to the next shape key
					self._CurShapeKeyIndex += 1
					self._WorkSubstage = 0
					context.window_manager.progress_update(self._CurShapeKeyIndex)
					
					if (self._CurShapeKeyIndex > self._TotalShapeKeys - 1):
						self._WorkStage = 2
						self._WorkSubstage = 0
					#else: # Still have more shape keys to go
			
			elif (self._WorkStage == 2):
				### Final things and tidying up
				self.singleSelect(context, obj)
				
				# Restore the blend shape dependencies
				for keyBlock in obj.data.shape_keys.key_blocks:
					relKey = None
					relKeyName = self._ShapeKeyDependencies[keyBlock.name]
					if (relKeyName in obj.data.shape_keys.key_blocks):
						relKeyIndex = obj.data.shape_keys.key_blocks.keys().index(relKeyName)
						keyBlock.relative_key = obj.data.shape_keys.key_blocks[relKeyIndex]
				# In my testing, the blend file must be saved and Blender restarted in order to later change the relative keys using the shape key panel
				
				# Delete the shape key object
				self.singleSelect(context, skObj)
				bpy.ops.object.delete()
				
				# Reselect the original object
				self.singleSelect(context, obj)
				
				# Done
				bpy.context.window_manager.progress_end()
				self.cancel(context)
				self.preport("Modifiers applied to base mesh and all shape keys.")
				return {"CANCELLED"}
				
			# Ensure the same object is selected at the end of every modal event so that the UI doesn't rapidly change
			self.singleSelect(context, obj)
		
		return {"PASS_THROUGH"}
	
	def cancel(self, context):
		if (self._Timer != None):
			context.window_manager.event_timer_remove(self._Timer)
		self._Timer = None
	
	
	def invoke(self, context, event):
		scene = context.scene
		properties = scene.shape_key_tools_props
		
		if (self.validateUser(context) == False):
			return {'FINISHED'}
		
		obj = context.object
		
		# Show all of the object's modifiers, but disable & mark the incompatible ones
		self.opt_modifiers.clear()
		for modifier in obj.modifiers:
			if (modifier.type in ModifierTypeInfo):
				optListItem = self.opt_modifiers.add()
				optListItem.name = modifier.name
				optListItem.do_apply = False
				
				optListItem.is_visible_in_viewport = modifier.show_viewport
				
				modifierTypeInfo = ModifierTypeInfo[modifier.type]
				optListItem.type = modifier.type
				optListItem.is_compatible = modifierTypeInfo[1]
		
		return context.window_manager.invoke_props_dialog(self, width=550)
	
def register():
	bpy.utils.register_class(ShapeKeyTools_ApplyModifiersToShapeKeys_OptListItem)
	bpy.utils.register_class(WM_OT_ShapeKeyTools_ApplyModifiersToShapeKeys)
	return WM_OT_ShapeKeyTools_ApplyModifiersToShapeKeys

def unregister():
	bpy.utils.unregister_class(WM_OT_ShapeKeyTools_ApplyModifiersToShapeKeys)
	bpy.utils.unregister_class(ShapeKeyTools_ApplyModifiersToShapeKeys_OptListItem)
	return WM_OT_ShapeKeyTools_ApplyModifiersToShapeKeys

if (__name__ == "__main__"):
	register()
