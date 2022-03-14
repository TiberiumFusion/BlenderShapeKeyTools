import math, mathutils
import bpy, bgl, blf


##
## Viewport drawing
##

### Applies default* 2D opengl drawing parameters
#*default = what Blender's defaults** are
#**which may or may not be wrong as the docs do not provide these, so they are figured through reasonable assumptions and empiric testing
def OglDefaults():
	bgl.glDisable(bgl.GL_BLEND)
	
	bgl.glDisable(bgl.GL_LINE_SMOOTH)
	bgl.glLineWidth(1)
	
	bgl.glDisable(bgl.GL_DEPTH_TEST)
	
	bgl.glColor4f(0.0, 0.0, 0.0, 1.0)


### Measures the to-be-drawn size of some 2d text
def Measure2dText(text, size=24, dpi=96):
	blf.size(0, size, dpi)
	return blf.dimensions(0, text)

### Draws text in 2d with the specified viewportspace location, rotation, and alignment
def Draw2dText(text, color, pos=None, rot=0, align=1, size=24, dpi=96):
	blf.size(0, size, dpi)
	textSize = blf.dimensions(0, text)
	
	# Alignment and translation are done together
	px = 0
	py = 0
	if (pos != None):
		px += pos[0]
		py += pos[1]
	#if (align == 1): # left align
	if (align == 0): # center align
		px += -(textSize[0] / 2)
	elif (align == -1): # right align
		px += -(textSize[0])
	blf.position(0, px, py, 0)
	
	blf.enable(0, blf.ROTATION)
	blf.rotation(0, rot)
	
	bgl.glColor4f(*color)
	
	# For some unexplained reason, blf.draw() UNsets GL_BLEND if it is enabled, which undesirable and quite frankly very stupid
	restoreGlBlend = bgl.glIsEnabled(bgl.GL_BLEND)
	bgl.glDisable(bgl.GL_DEPTH_TEST)
	blf.draw(0, text)
	if (restoreGlBlend):
		bgl.glEnable(bgl.GL_BLEND)


##
## Main 2d draw callback
##

def ViewportDraw2d(self, context):
	scene = context.scene
	properties = scene.shape_key_tools_props
	
	OglDefaults()
	
	bgl.glEnable(bgl.GL_BLEND)
	
	viewportBounds = bgl.Buffer(bgl.GL_INT, 4)
	bgl.glGetIntegerv(bgl.GL_VIEWPORT, viewportBounds)
	sW = viewportBounds[2]
	sH = viewportBounds[3]
	
	if (self.State == 1): # Warning message about the preview mesh init process
		line1 = "Initializing preview mesh..."
		line1Size = Measure2dText(line1, 18)
		
		line2 = "This may take a while for detailed meshes with many shape keys"
		line2Size = Measure2dText(line1, 12)
		
		Draw2dText(line1, (1, 0.95, 0.5, 1), (sW / 2, sH - 5 - line1Size[1]), 0, 0, 18)
		Draw2dText(line2, (1, 0.95, 0.6, 1), (sW / 2, sH - 5 - line1Size[1] - 10 - line2Size[1]), 0, 0, 12)
	
	elif (self.State == 2): # Live update mode
		if (self.ValidActiveShapeKey):
			line1 = "Previewing L/R Pair Split"
			line1Size = Measure2dText(line1, 18)
			
			line2 = "Commit this preview with Split Active Shape Key"
			line2Size = Measure2dText(line1, 12)
			
			Draw2dText(line1, (1, 1, 1, 1), (sW / 2, sH - 5 - line1Size[1]), 0, 0, 18)
			Draw2dText(line2, (1, 1, 1, 1), (sW / 2, sH - 5 - line1Size[1] - 10 - line2Size[1]), 0, 0, 12)
		else:
			line1 = "Previewing L/R Pair Split"
			line1Size = Measure2dText(line1, 18)
			
			line2 = "Mesh has no shape keys or the active shape key cannot be split"
			line2Size = Measure2dText(line1, 12)
			
			Draw2dText(line1, (1, 1, 1, 1), (sW / 2, sH - 5 - line1Size[1]), 0, 0, 18)
			Draw2dText(line2, (1, 0.15, 0.15, 1), (sW / 2, sH - 5 - line1Size[1] - 10 - line2Size[1]), 0, 0, 12)
	
	OglDefaults()



##
## Main operator
##

# Param cls must be the __class__ object
def Disable(cls, fromBlendFileChange=False):
	if (cls.InstanceInfo != None):
		opInstance = cls.InstanceInfo[0]
		opContext = cls.InstanceInfo[1]
		cls.InstanceInfo = None
		
		## Selection helpers
		def deselectAll():
			for obj in bpy.data.objects:
				obj.select = False
		def activeSelect(obj):
			obj.select = True
			opContext.scene.objects.active = obj
		def singleSelect(obj):
			deselectAll()
			activeSelect(obj)
		
		# Remove the modal timer
		if (opInstance._Timer != None):
			opContext.window_manager.event_timer_remove(opInstance._Timer)
		opInstance._Timer = None
		
		# Remove the 2d drawing callback
		if (opInstance._Drawing2dHandle != None):
			bpy.types.SpaceView3D.draw_handler_remove(opInstance._Drawing2dHandle, "WINDOW")
			opInstance._Drawing2dHandle = None
		
		# Remove the preview mesh object
		if (fromBlendFileChange == False):
			if (opInstance.PreviewMeshObject != None):
				opInstance.PreviewMeshObject.hide = False
				singleSelect(opInstance.PreviewMeshObject)
				bpy.ops.object.delete()
				opInstance.OriginalMeshObject.hide = False
				singleSelect(opInstance.OriginalMeshObject)
	


### Sets to false all properties which would cause this operator to run
def UnsetEnablerProperties(context):
	scene = context.scene
	properties = scene.shape_key_tools_props
	
	properties.opt_shapepairs_splitmerge_preview_split_left = False
	properties.opt_shapepairs_splitmerge_preview_split_right = False



### bpy operator
class VIEW_3D_OT_ShapeKeyTools_SplitPairPreview(bpy.types.Operator):
	bl_idname = "view3d.shape_key_tools_splitpair_preview"
	bl_label = "Shape Key Tools Split Pair Preview Mesh"
	bl_options = {'INTERNAL'}
	
	## Statics
	InstanceInfo = None # Contains info on the currently running singleton instance of the operator. None when not running.
	
	## Instance vars
	State = 0
	StateModals = 0 # Number of modal() calls that have occurred since the last state change
	
	OriginalMeshObject = None # The mesh which the preview mesh is representing
	PreviewMeshObject = None # The preview mesh object we are working with
	ValidActiveShapeKey = False # Only true when the mesh has >=2 shape keys and user's selected active shape key is not key 0
	LastActiveShapeKeyIndex = None # The index of the shape key on the original mesh that the user had active last time we checked
	LastUsedSplitParams = None # Dictionary of the pair split params last used to split the preview mesh's active shape key. None when the preview mesh is first initialized.
	
	
	### Hook for when the current blend file is closing
	def BlendFilePreLoadWatcher(self, context):
		try:
			Disable(self.__class__, True)
		except:
			pass
	
	
	### Returns true if this operator is valid to continue running, false otherwise
	def Validate(self, context):
		scene = context.scene
		properties = scene.shape_key_tools_props
		
		# Ensure the user still wants to see the preview
		if (properties.opt_shapepairs_splitmerge_preview_split_left == False and properties.opt_shapepairs_splitmerge_preview_split_right == False):
			return False
		
		# If the user has selected a different mesh, we can't assume things are in sync anymore
		
		
		return True
	
	
	### Set a new state and reset the counter for modal() calls
	def ChangeState(self, newState):
		self.State = newState
		self.StateModals = 0
	
	
	### Initial preview mesh setup
	def InitPreviewMesh(self, context):
		## Selection helpers
		def deselectAll():
			for obj in bpy.data.objects:
				obj.select = False
		def activeSelect(obj):
			obj.select = True
			context.scene.objects.active = obj
		def singleSelect(obj):
			deselectAll()
			activeSelect(obj)
		
		
		self.OriginalMeshObject = context.object
		
		
		### The blend file might've been saved with the preview enabled and we're initializing from that and thus the preview mesh already exists in the scene
		# If so we will delete this old preview mesh and create a new one
		expectedPreviewMeshName = "zzz_DO_NOT_TOUCH__SHAPE_KEY_TOOLS__PREVIEW_SHAPE_KEY_SPLIT__" + self.OriginalMeshObject.name
		for obj in bpy.data.objects:
			if (obj.name == expectedPreviewMeshName):
				singleSelect(obj)
				bpy.ops.object.delete()
		
		
		### Ensure the active mesh is selectable
		self.OriginalMeshObject.hide = False
		singleSelect(self.OriginalMeshObject)
		
		
		### Duplicate the active mesh
		bpy.ops.object.duplicate()
		self.PreviewMeshObject = context.object
		
		# Rename it
		self.PreviewMeshObject.name = expectedPreviewMeshName
		
		# If it only has 0 or 1 shape keys (i.e. no real shape keys, only the basis shape key), or the active shape key is the key 0 (should be the basis), we wont preview anything
		self.ValidActiveShapeKey = (hasattr(self.PreviewMeshObject.data.shape_keys, "key_blocks") and len(self.PreviewMeshObject.data.shape_keys.key_blocks) >= 2 and self.PreviewMeshObject.active_shape_key_index > 0)
		if (self.ValidActiveShapeKey):
			# Ensure the active shape keys relative shape is key 0
			previewMeshActiveShape = self.PreviewMeshObject.data.shape_keys.key_blocks[self.PreviewMeshObject.active_shape_key_index]
			previewMeshActiveShape.relative_key = self.PreviewMeshObject.data.shape_keys.key_blocks[0]
			# Remove all shape keys except the active one and key 0
			bpy.ops.object.shape_key_move(type="BOTTOM")
			while (len(self.PreviewMeshObject.data.shape_keys.key_blocks) > 2):
				self.PreviewMeshObject.active_shape_key_index = len(self.PreviewMeshObject.data.shape_keys.key_blocks) - 2
				bpy.ops.object.shape_key_remove()
			self.PreviewMeshObject.active_shape_key_index = 1
		
		
		### Reselect the original object
		singleSelect(self.OriginalMeshObject)
		
		# Hide it
		self.OriginalMeshObject.hide = True
		
		# The original object is selected, so the properties panel is showing all its shape keys and the user can select and manipulate them as expected
		# However, that object is hidden, so what they see instead in the viewport is the preview model
		
		
		### Reset some tracked data
		self.LastActiveShapeKeyIndex = self.OriginalMeshObject.active_shape_key_index # This preview mesh will be valid so long as the user doesn't change the active shape key
		self.LastUsedSplitParams = None
	
	
	### Keeps the preview mesh synchronized with the original mesh
	def UpdatePreviewMesh(self, context):
		scene = context.scene
		properties = scene.shape_key_tools_props
		
		## Selection helpers
		def deselectAll():
			for obj in bpy.data.objects:
				obj.select = False
		def activeSelect(obj):
			obj.select = True
			context.scene.objects.active = obj
		def singleSelect(obj):
			deselectAll()
			activeSelect(obj)
		
		# Ensure the preview mesh stays visible and the original mesh stays hidden
		self.PreviewMeshObject.hide = False
		self.OriginalMeshObject.hide = True
		
		# If the user selects something that isnt the original mesh or preview mesh, then we will end the preview and disable this operator
		if (not (context.object == self.OriginalMeshObject or context.object == self.PreviewMeshObject)):
			newSelection = context.object
			UnsetEnablerProperties(context)
			Disable(self.__class__)
			singleSelect(newSelection)
			return
		
		# If the user selects the preview mesh (i.e. most likely by clicking it in the viewport), change the selection back to the original mesh
		if (context.object == self.PreviewMeshObject):
			singleSelect(self.OriginalMeshObject)
		
		# If the user has changed the active shape key, we need to create a new preview mesh for it
		if (self.OriginalMeshObject.active_shape_key_index != self.LastActiveShapeKeyIndex):
			# Delete the existing preview mesh
			singleSelect(self.PreviewMeshObject)
			bpy.ops.object.delete()
			# Reselect the original mesh
			self.OriginalMeshObject.hide = False
			singleSelect(self.OriginalMeshObject)
			# Prepare to re-initialize a new preview mesh
			self.ChangeState(1)
			return
		
		### If we have a valid active shape key to preview splitting, do that now
		if (self.ValidActiveShapeKey):
			# Update the split shape keys if needed
			needsUpdate = (self.LastUsedSplitParams == None) # If we have no record of the last split params, then we havent done the initial split yet
			if (needsUpdate == False): # Check if the user's chosen split/merge params have meaningfully changed and thus necessitate a new split to preview
				if (self.LastUsedSplitParams["opt_shapepairs_split_axis"] != properties.opt_shapepairs_split_axis):
					needsUpdate = True
				if (self.LastUsedSplitParams["opt_shapepairs_split_mode"] != properties.opt_shapepairs_split_mode):
					# sharp -> smooth w/ dist=0 doesnt need an update
					# smooth w/ dist 0 -> sharp doesnt need an update
					# all other situations need an update
					if (not (
						(self.LastUsedSplitParams["opt_shapepairs_split_mode"] == "sharp" and properties.opt_shapepairs_split_mode == "smooth" and properties.opt_shapepairs_split_smoothdist == 0)
						or
						(self.LastUsedSplitParams["opt_shapepairs_split_mode"] == "smooth" and self.LastUsedSplitParams["opt_shapepairs_split_smoothdist"] == 0 and properties.opt_shapepairs_split_mode == "sharp")
						)):
						needsUpdate = True
				if (self.LastUsedSplitParams["opt_shapepairs_split_mode"] == "smooth" and properties.opt_shapepairs_split_mode == "smooth" and self.LastUsedSplitParams["opt_shapepairs_split_smoothdist"] != properties.opt_shapepairs_split_smoothdist):
					needsUpdate = True
			if (needsUpdate):
				# Select the preview mesh so we can operate on it
				singleSelect(self.PreviewMeshObject)
				# If old split keys still exist, delete them
				while (len(self.PreviewMeshObject.data.shape_keys.key_blocks) > 2):
					self.PreviewMeshObject.active_shape_key_index = len(self.PreviewMeshObject.data.shape_keys.key_blocks) - 1
					bpy.ops.object.shape_key_remove()
				# Split the active (and only) shape key. Unlike typical usage of this op, we want to keep the original shape key, and we dont want to turn off the split preview when it finishes
				bpy.ops.wm.shape_key_tools_split_active_pair(opt_delete_original=False, opt_clear_preview=False)
				
				# Update tracked params
				if (self.LastUsedSplitParams == None):
					self.LastUsedSplitParams = {}
				self.LastUsedSplitParams["opt_shapepairs_split_axis"] = properties.opt_shapepairs_split_axis
				self.LastUsedSplitParams["opt_shapepairs_split_mode"] = properties.opt_shapepairs_split_mode
				self.LastUsedSplitParams["opt_shapepairs_split_smoothdist"] = properties.opt_shapepairs_split_smoothdist
			
			# The user can swap between previewing the left or right split key, so keep that synced			
			if (properties.opt_shapepairs_splitmerge_preview_split_left):
				newIndex = len(self.PreviewMeshObject.data.shape_keys.key_blocks) - 2
				if (newIndex != self.PreviewMeshObject.active_shape_key_index): # because I think setting active_shape_key_index always trigger some expensive UI refreshes, even if the value is the same
					self.PreviewMeshObject.active_shape_key_index = newIndex
			elif (properties.opt_shapepairs_splitmerge_preview_split_right):
				newIndex = len(self.PreviewMeshObject.data.shape_keys.key_blocks) - 1
				if (newIndex != self.PreviewMeshObject.active_shape_key_index):
					self.PreviewMeshObject.active_shape_key_index = newIndex
			
		
	
	def modal(self, context, event):
		self.StateModals += 1
		
		if (self.Validate(context)):
			if (self.State == 1): # we need to reinit the preview, but first we're idling for 5 modal()s to give the drawing overlay a chance to warn the user about the lag that InitPreviewMesh() might incur
				if (self.StateModals > 5):
					self.InitPreviewMesh(context)
					self.ChangeState(2)
			
			elif (self.State == 2): # preview is set up and running, keep it updated
				self.UpdatePreviewMesh(context)
			
			return {'PASS_THROUGH'}
		else:
			Disable(self.__class__)
			return {'CANCELLED'}
	
	
	def execute(self, context):
		if (context.area.type == "VIEW_3D"):
			# Setup 2D drawing callback for the viewport
			self._Drawing2dHandle = bpy.types.SpaceView3D.draw_handler_add(ViewportDraw2d, (self, context), "WINDOW", "POST_PIXEL")
			# Since manipulating with many shape keys on complex meshes can hang the Blender UI for several seconds, we will draw some status text in the viewport so the user know what's going on while Blender is frozen
			
			# Opening a different blend file will stop this op before modal() has a chance to notice the blend file has changed
			# So we need to watch for that and clean up the drawing callback as needed
			bpy.app.handlers.load_pre.append(self.BlendFilePreLoadWatcher)
			
			self.__class__.InstanceInfo = (self, context)
			
			# Prep for initial operator setup so we can work with the user's currently selected mesh
			self.ChangeState(1)
			# We want to wait at least one or two rendered frames before running InitPreviewMesh so that the viewport drawing hook can warn the user about the potential incoming freeze
			# modal() will do this and call InitPreviewMesh() very shortly after this execute()
			
			context.window_manager.modal_handler_add(self)
			self._Timer = context.window_manager.event_timer_add(0.017, context.window) # See notes in internal_viewport_visuals.py on this
			
			return {'RUNNING_MODAL'}
		else:
			# If the viewport isn't available, disable the Properties which enable this operator
			print("Viewport not available. Split pair preview has been disabled.")
			UnsetEnablerProperties(context)
			return {'CANCELLED'}
	

def register():
	bpy.utils.register_class(VIEW_3D_OT_ShapeKeyTools_SplitPairPreview)
	return VIEW_3D_OT_ShapeKeyTools_SplitPairPreview

def unregister():
	Disable(VIEW_3D_OT_ShapeKeyTools_SplitPairPreview)
	bpy.utils.unregister_class(VIEW_3D_OT_ShapeKeyTools_SplitPairPreview)
	return VIEW_3D_OT_ShapeKeyTools_SplitPairPreview

if __name__ == "__main__":
	register()
