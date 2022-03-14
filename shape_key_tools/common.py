# ////////////////////////////////////////////////////////////////////////////////////////////////////
# //
# //    Common Methods
# //    - Things that are used by multiple Operators/Panels/whatever
# //
# ////////////////////////////////////////////////////////////////////////////////////////////////////

import sys, os, math, mathutils
import bpy


#
#====================================================================================================
#    Helpers
#====================================================================================================
#

### Simple bezier interpolation for values in 0-1
def InterpBezier(x):
	return (3.0 * x * x) - (2.0 * x * x * x)



#
#====================================================================================================
#    Names
#====================================================================================================
#

### Validates the provided shape key name as non-existent and modifies it with Blender's .001, .002, etc styling if it does exist
def ValidateShapeKeyName(obj, name):		
	if (not hasattr(obj.data.shape_keys, "key_blocks") or len(obj.data.shape_keys.key_blocks.keys()) == 0): # no shape keys
		return name, 0
	else:
		newName = name
		conflict = (newName in obj.data.shape_keys.key_blocks.keys())
		numConflicts = 0
		while (conflict):
			numConflicts += 1
			if (numConflicts <= 999):
				newName = name + "." + "{:03d}".format(numConflicts)
			else:
				newName = name + "." + str(numConflicts)
			conflict = (newName in obj.data.shape_keys.key_blocks.keys())
		return newName



#
#====================================================================================================
#    Vertex Filtering
#====================================================================================================
#

### Creates a vertex filtering kernel function per the provided parameters
def CreateVertexFilterKernel(params):
	deltaDistanceMin = 0
	if ("DeltaDistanceMin" in params):
		deltaDistanceMin = params["DeltaDistanceMin"]
	
	deltaDistanceMax = sys.float_info.max
	if ("DeltaDistanceMax" in params):
		deltaDistanceMax = params["DeltaDistanceMax"]
	
	vertexGroupIndex = None
	if ("VertexGroupIndex" in params):
		vertexGroupIndex = int(params["VertexGroupIndex"], 10) # int() because blender requires a string identifier for EnumProperty value IDs (numbers cause silent errors)
	
	def filter(vertVGIndices, delta):
		return (
			(delta.length >= deltaDistanceMin and delta.length <= deltaDistanceMax)
			and
			(vertexGroupIndex == None or vertexGroupIndex in vertVGIndices)
		)
	
	return filter
	


#
#====================================================================================================
#    Pair Split/Merge
#====================================================================================================
#

### Given an existing shape key, determines the new names if this shape key was to be split into L and R halves
# If validateWith = any object, the new names will be validated (and adjusted) for conflicts with existing shape keys
# If validateWith = None, the ideal new names will be returned without modification
def FindShapeKeyPairSplitNames(originalShapeKeyName, validateWith=None):
	newLeftName = None
	newRightName = None
	usesPairNameConvention = False
	if ('+' in originalShapeKeyName):
		nameCuts = originalShapeKeyName.split("+")
		if (nameCuts[0].lower()[-1] == "l" and nameCuts[1].lower()[-1] == "r"):
			newLeftName = nameCuts[0]
			newRightName = nameCuts[1]
			usesPairNameConvention = True
		elif (nameCuts[1].lower()[-1] == "l" and nameCuts[0].lower()[-1] == "r"):
			newLeftName = nameCuts[1]
			newRightName = nameCuts[0]
			usesPairNameConvention = True
		else: # shape key name has a + in it, but the string halves on either side of that + do not end in L and R
			newLeftName = originalShapeKeyName + "L"
			newRightName = originalShapeKeyName + "R"
			usesPairNameConvention = False
	else:
		newLeftName = originalShapeKeyName + "L"
		newRightName = originalShapeKeyName + "R"
		usesPairNameConvention = False
	
	if (validateWith):
		newLeftName = ValidateShapeKeyName(validateWith, newLeftName)
		newRightName = ValidateShapeKeyName(validateWith, newRightName)
	
	return (newLeftName, newRightName, usesPairNameConvention)


### Splits the active shape key on the specified object into separate left and right halves
# Params:
# - obj: The object who has the active shape key we are going to split
# - optAxis: The world axis which determines which verts go into the "left" and "right" halves
# - newLeftName: Name for the newly split-off left side shape key
# - newRightName: Name for the newly split-off right side shape key
# - (optional) deleteOriginal: If false, the original shape key will be kept instead of deleted
# - (optional) smoothDistance: Distance in world space from the origin of the split axis to crossblend the split shape keys 
# - (optional) asyncProgressReporting: An object provided by __init__ for asynchronous operation (i.e. in a modal)
def SplitPairActiveShapeKey(obj, optAxis, newLeftName, newRightName, smoothDistance=0, deleteOriginal=True, asyncProgressReporting=None):
	originalShapeKeyName = obj.active_shape_key.name
	originalShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(originalShapeKeyName)
	
	# Basis shape key cannot be split (assume this is key 0)
	if (originalShapeKeyIndex == 0):
		raise Exception("You cannot split the basis shape key")
	
	# Create the two copies
	obj.shape_key_add(name=str(newLeftName), from_mix=True)
	newLeftShapeKeyIndex = len(obj.data.shape_keys.key_blocks) - 1
	obj.shape_key_add(name=str(newRightName), from_mix=True)
	newRightShapeKeyIndex = len(obj.data.shape_keys.key_blocks) - 1
	
	# Split axis factor
	axis = 0
	if (optAxis == "+X" or optAxis == "-X"):
		axis = 0
	elif (optAxis == "+Y" or optAxis == "-Y"):
		axis = 1
	elif (optAxis == "+Z" or optAxis == "-Z"):
		axis = 2
	axisFlip = 1
	if optAxis[0] == "-":
		axisFlip = -1
	
	# Async progress reporting
	reportAsyncProgress = False
	wm = None
	currentVert = 0
	totalVerts = 0
	if asyncProgressReporting:
		reportAsyncProgress = True
		wm = bpy.context.window_manager
		currentVert = asyncProgressReporting["CurrentVert"]
		totalVerts = asyncProgressReporting["TotalVerts"]
	
	basisShapeKeyVerts = obj.data.shape_keys.key_blocks[0].data
	originalShapeKeyVerts = obj.data.shape_keys.key_blocks[originalShapeKeyIndex].data
	leftShapeKeyVerts = obj.data.shape_keys.key_blocks[newLeftShapeKeyIndex].data
	rightShapeKeyVerts = obj.data.shape_keys.key_blocks[newRightShapeKeyIndex].data
	
	for vert in obj.data.vertices:
		if reportAsyncProgress:
			currentVert += 1
			if (currentVert % 100 == 0): # Only break for the UI thread every 100 verts. I'm not sure how much of a performance hit progress_update() incurs, but there's no need to call it faster than 60Hz.
				wm.progress_update(currentVert)
		
		basisVertPos = basisShapeKeyVerts[vert.index].co
		
		# The coordinate of the vert on the basis shape key determines whether it is a left (+aXis) or right (-aXis) vert
		axisSplitCoord = 0
		if (axis == 0):
			axisSplitCoord = basisVertPos.x
		elif (axis == 1):
			axisSplitCoord = basisVertPos.y
		elif (axis == 2):
			axisSplitCoord = basisVertPos.z
		axisSplitCoord *= axisFlip
		
		# if axisSplitCoord < 0: this vert is on the right side
		# if axisSplitCoord == 0: this vert is exactly on the middle of the split axis
		# if axisSplitCoord > 0: this vert is on the left side
		
		# Both the left and right shape keys are identical and start out with all deltas from both sides
		# So we are removing deltas from one side or the other instead of adding them in order to achieve the two split shape keys
		
		if (axisSplitCoord < 0): # Vert is on the right side
			if (axisSplitCoord < -smoothDistance or smoothDistance == 0): # Vert is outside of the smoothing radius or smoothing is disabled, so no crossfade
				leftShapeKeyVerts[vert.index].co = basisVertPos * 1 # Remove this (right side) delta from the left shape key
			else: # Vert is inside the smoothing radius, so factor the deltas for both the left and right shape keys to achieve the crossfade
				leftShapeKeyVerts[vert.index].co = basisVertPos * 1 # Remove this (right side) delta from the left shape key
				t = InterpBezier((smoothDistance - axisSplitCoord) / (2.0 * smoothDistance))
				rightShapeKeyVerts[vert.index].co = basisVertPos.lerp(originalShapeKeyVerts[vert.index].co, t)
				leftShapeKeyVerts[vert.index].co = basisVertPos.lerp(originalShapeKeyVerts[vert.index].co, 1.0 - t)
		
		elif (axisSplitCoord >= 0): # Vert is on the left side (or center)
			if (axisSplitCoord > smoothDistance or smoothDistance == 0): # Vert is outside of the smoothing radius or smoothing is disabled, so no crossfade
				rightShapeKeyVerts[vert.index].co = basisVertPos * 1 # Remove this (left side) delta from the right shape key
			else: # Vert is inside the smoothing radius, so factor the deltas for both the left and right shape keys to achieve the crossfade
				t = InterpBezier((smoothDistance - axisSplitCoord) / (2.0 * smoothDistance))
				leftShapeKeyVerts[vert.index].co = basisVertPos.lerp(originalShapeKeyVerts[vert.index].co, 1.0 - t)
				rightShapeKeyVerts[vert.index].co = basisVertPos.lerp(originalShapeKeyVerts[vert.index].co, t)
			
	# Move the two copies in the shape key list to sit after the original shape key
	while (newLeftShapeKeyIndex > originalShapeKeyIndex + 1):
		# Move left copy
		obj.active_shape_key_index = newLeftShapeKeyIndex
		bpy.ops.object.shape_key_move(type="UP")
		# Move right copy (will always be on the tail of the left copy)
		obj.active_shape_key_index = newRightShapeKeyIndex
		bpy.ops.object.shape_key_move(type="UP")
		newLeftShapeKeyIndex -= 1
		newRightShapeKeyIndex -= 1
	
	# Delete original shape key
	if (deleteOriginal):
		obj.active_shape_key_index = originalShapeKeyIndex
		bpy.ops.object.shape_key_remove()
	
	# Select the new L shape key
	obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(newLeftName)
	
	# Update async progress reporting for delta verts processed
	if reportAsyncProgress:
		asyncProgressReporting["CurrentVert"] = currentVert


### Given an existing shape key, determines the expected name of the complementary shape key (the L for the R, or the R for the L) and the name of the final shape key if they two were merged
# If validateWith = any object, the to-be-merged name will be validated (and adjusted) for conflicts with existing shape keys
# If validateWith = None, the ideal to-be-merged name will be returned without modification
def FindShapeKeyMergeNames(shapeKeyName, validateWith=None):
	expectedCompShapeKeyName = None
	mergedShapeKeyName = None
	if shapeKeyName[-1] == "L":
		expectedCompShapeKeyName = shapeKeyName[:-1] + "R"
		mergedShapeKeyName = shapeKeyName + "+" + expectedCompShapeKeyName
	if shapeKeyName[-1] == "R":
		expectedCompShapeKeyName = shapeKeyName[:-1] + "L"
		mergedShapeKeyName = expectedCompShapeKeyName + "+" + shapeKeyName
	
	if (validateWith):
		mergedShapeKeyName = ValidateShapeKeyName(validateWith, mergedShapeKeyName)
	
	return (shapeKeyName, expectedCompShapeKeyName, mergedShapeKeyName)


### Merges the specified shape key pair (two shape keys with names like "MyShapeKeyL" and "MyShapeKeyR") on the specified object into a single shape key
# Params:
# - obj: The object who has the two specified shape keys to be merged
# - optAxis: The world axis which determines which verts belong to the "left" and "right" halves of the combined shape key
# - shapeKeyLeftName: Name of the "left" side shape key to be merged
# - shapeKeyRightName: Name of the "right" side shape key to be merged
# - mergedShapeKeyName: Name of the soon-to-be merged shape key
# - mode: Name of the mode to use for merging the left and right deltas
# - (optional) deleteInputShapeKeys: Defaults to delete the left and right shape keys creating the new merged key
# - (optional) asyncProgressReporting: An object provided by __init__ for asynchronous operation (i.e. in a modal)
def MergeShapeKeyPair(obj, optAxis, shapeKeyLeftName, shapeKeyRightName, mergedShapeKeyName, mode, deleteInputShapeKeys=True, asyncProgressReporting=None):
	# Find the indices of the left and right shape keys
	leftShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(shapeKeyLeftName)
	rightShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(shapeKeyRightName)
	
	# Neither shape key can be the basis key (assume this is key 0)
	if (leftShapeKeyIndex == 0 or rightShapeKeyIndex == 0):
		raise Exception("The basis shape key cannot be merged.")
	
	key0 = obj.data.shape_keys.key_blocks[0]
	leftShapeKey = obj.data.shape_keys.key_blocks[leftShapeKeyIndex]
	rightShapeKey = obj.data.shape_keys.key_blocks[rightShapeKeyIndex]
	
	# If the two shape keys are relative to a key other than key 0 (should be the basis shape, assuming the user isn't being weird), change them now and restore the relative key at the end
	leftOldBasisKey = leftShapeKey.relative_key
	rightOldBasisKey = rightShapeKey.relative_key
	if (leftOldBasisKey != key0):
		leftShapeKey.relative_key = key0
	if (rightOldBasisKey != key0):
		rightShapeKey.relative_key = key0
	
	# Create a new shape key from the basis
	obj.active_shape_key_index = 0
	obj.shape_key_add(name=str(mergedShapeKeyName), from_mix=False)
	newShapeKeyIndex = len(obj.data.shape_keys.key_blocks) - 1
	newShapeKey = obj.data.shape_keys.key_blocks[newShapeKeyIndex]
	
	# Cherry pick which verts to bring into the new shape key from the -/+ sides of the left and right shape keys pair
	axis = 0
	if (optAxis == "+X" or optAxis == "-X"):
		axis = 0
	elif (optAxis == "+Y" or optAxis == "-Y"):
		axis = 1
	elif (optAxis == "+Z" or optAxis == "-Z"):
		axis = 2
	axisFlip = 1
	if optAxis[0] == "-":
		axisFlip = -1
	
	# Async progress reporting
	reportAsyncProgress = False
	wm = None
	currentVert = 0
	totalVerts = 0
	if asyncProgressReporting:
		reportAsyncProgress = True
		wm = bpy.context.window_manager
		currentVert = asyncProgressReporting["CurrentVert"]
		totalVerts = asyncProgressReporting["TotalVerts"]
	
	basisShapeKeyVerts = key0.data
	mergedShapeKeyVerts = newShapeKey.data
	leftShapeKeyVerts = leftShapeKey.data
	rightShapeKeyVerts = rightShapeKey.data
	
	for vert in obj.data.vertices:
		if reportAsyncProgress:
			currentVert += 1
			if (currentVert % 100 == 0):
				wm.progress_update(currentVert)
		
		baseVertPos = basisShapeKeyVerts[vert.index].co
		
		axisSplitCoord = 0
		if (axis == 0):
			axisSplitCoord = baseVertPos.x
		elif (axis == 1):
			axisSplitCoord = baseVertPos.y
		elif (axis == 2):
			axisSplitCoord = baseVertPos.z
		axisSplitCoord *= axisFlip
		
		if (mode == "overwrite"):	
			# If the original vert is -aXis (right side), then we pick the flexed vert from the Right shape key
			if (axisSplitCoord < 0):
				mergedShapeKeyVerts[vert.index].co = rightShapeKeyVerts[vert.index].co * 1
			# If the original vert is +aXis (left side), then we pick the flexed vert from the Left shape key
			if (axisSplitCoord >= 0):
				mergedShapeKeyVerts[vert.index].co = leftShapeKeyVerts[vert.index].co * 1
		
		elif (mode == "additive"):
			# Add the deltas of both the left and right halves together
			leftDelta = leftShapeKeyVerts[vert.index].co - baseVertPos
			rightDelta = rightShapeKeyVerts[vert.index].co - baseVertPos
			mergedShapeKeyVerts[vert.index].co = baseVertPos + leftDelta + rightDelta
	
	# Restore relative_key for the two input shape keys if necessary
	if (leftOldBasisKey != key0):
		leftShapeKey.relative_key = leftOldBasisKey
	if (rightOldBasisKey != key0):
		rightShapeKey.relative_key = rightOldBasisKey
	
	# Set the relative_key for the new merged shape key to whatever the relative key was for the left shape key
	newShapeKey.relative_key = leftOldBasisKey
	
	# Move the new merged shape key in the shape key list to sit after the firstmost shape key of the pair in the shape key list
	originalShapeKeyIndex = min(leftShapeKeyIndex, rightShapeKeyIndex)
	while (newShapeKeyIndex > originalShapeKeyIndex + 1):
		# Move left copy
		obj.active_shape_key_index = newShapeKeyIndex
		bpy.ops.object.shape_key_move(type="UP")
		newShapeKeyIndex -= 1
	
	# Delete the left and right shape keys
	if (deleteInputShapeKeys):
		obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(shapeKeyLeftName)
		bpy.ops.object.shape_key_remove()
		obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(shapeKeyRightName)
		bpy.ops.object.shape_key_remove()
	
	# Reselect merged shape key
	obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(mergedShapeKeyName)
	
	# Update async progress reporting for delta verts processed
	if reportAsyncProgress:
		asyncProgressReporting["CurrentVert"] = currentVert



#
#====================================================================================================
#    Arbitrary Split/Merge
#====================================================================================================
#

### Merges the two specified shape keys on the specified object into a single shape key, using various blend modes
# Params:
# - obj: The object who has the two specified shape keys to be merged
# - shapeKey1Name: Name of the shape key to use as the lower layer in blending
# - shapeKey2Name: Name of the shape key to use as the upper layer in blending
# - destination: Either 1 (output to shape key 1), 2 (output to shape key 2), or a string (name of a new shape key to create)
# - blendMode: Name of the blend mode
# - (optional) blendModeParams: Dictionary of parameters specific to the chosen blend mode
# - (optional) vertexFilterParams: Dictionary of parameters for vertex filtering. If None, vertex filtering is disabled.
# - (optional) delete1OnFinish: If true, shape key 1 will be deleted after the merge is complete
# - (optional) delete2OnFinish: If true, shape key 2 will be deleted after the merge is complete
# - (optional) asyncProgressReporting: An object provided by __init__ for asynchronous operation (i.e. in a modal)
def MergeAndBlendShapeKeys(obj, shapeKey1Name, shapeKey2Name, destination, blendMode, blendModeParams=None, vertexFilterParams=None, delete1OnFinish=False, delete2OnFinish=False, asyncProgressReporting=None):
	# New shape key from the basis (if we are outputting to a new shape key)
	newShapeKeyIndex = None
	if (isinstance(destination, str)):
		obj.active_shape_key_index = 0
		obj.shape_key_add(name=str(destination), from_mix=False)
		newShapeKeyIndex = len(obj.data.shape_keys.key_blocks) - 1
	
	# Find the indices of the source shape keys
	lowerShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(shapeKey1Name)
	upperShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(shapeKey2Name)
	
	key0 = obj.data.shape_keys.key_blocks[0]
	lowerShapeKey = obj.data.shape_keys.key_blocks[lowerShapeKeyIndex]
	upperShapeKey = obj.data.shape_keys.key_blocks[upperShapeKeyIndex]
	
	# If the two shape keys are relative to a key other than key 0 (should be the basis shape, assuming the user isn't being weird), change them now and restore the relative key at the end
	lowerOldBasisKey = lowerShapeKey.relative_key
	upperOldBasisKey = upperShapeKey.relative_key
	if (lowerOldBasisKey != key0):
		lowerShapeKey.relative_key = key0
	if (upperOldBasisKey != key0):
		upperShapeKey.relative_key = key0
	
	basisShapeKeyVerts = key0.data
	lowerShapeKeyVerts = lowerShapeKey.data
	upperShapeKeyVerts = upperShapeKey.data
	newShapeKeyVerts = None
	if (newShapeKeyIndex != None):
		newShapeKeyVerts = obj.data.shape_keys.key_blocks[newShapeKeyIndex].data
	
	destinationShapeKeyName = None
	destinationShapeKeyVerts = None
	if (destination == 1):
		destinationShapeKeyName = shapeKey1Name
		destinationShapeKeyVerts = lowerShapeKeyVerts
	elif (destination == 2):
		destinationShapeKeyName = shapeKey2Name
		destinationShapeKeyVerts = upperShapeKeyVerts
	else:
		destinationShapeKeyName = destination
		destinationShapeKeyVerts = newShapeKeyVerts
	
	
	### Blend-mode-specific params
	blendModeLerp_Factor = None
	if (blendMode == "lerp"):
		blendModeLerp_Factor = min(max(0, blendModeParams["Factor"]), 1)
	
	
	### Vertex filter kernel
	vertexFilterKernel = None
	doVertexFiltering = False
	if (vertexFilterParams != None):
		doVertexFiltering = True
		vertexFilterKernel = CreateVertexFilterKernel(vertexFilterParams)
		
	
	# Async progress reporting
	reportAsyncProgress = False
	wm = None
	currentVert = 0
	totalVerts = 0
	if asyncProgressReporting:
		reportAsyncProgress = True
		wm = bpy.context.window_manager
		currentVert = asyncProgressReporting["CurrentVert"]
		totalVerts = asyncProgressReporting["TotalVerts"]
	
	### Iterate all the verts and combine the deltas as per the blend mode
	for vert in obj.data.vertices:
		if reportAsyncProgress:
			currentVert += 1
			if (currentVert % 100 == 0):
				wm.progress_update(currentVert)
		
		# Unfortunately, bpy does not expose relative position of each vert, so we have to calculate the deltas ourself
		basePos = basisShapeKeyVerts[vert.index].co
		lowerDelta = lowerShapeKeyVerts[vert.index].co - basePos
		upperDelta = upperShapeKeyVerts[vert.index].co - basePos
		
		# Filter the upper vert if vertex filtering is enabled
		vertPassesFilter = True # RED verts are True, BLACK verts are False.
		if (doVertexFiltering):
			vgIndices = [vg.group for vg in vert.groups]
			vertPassesFilter = vertexFilterKernel(vgIndices, upperDelta)
		
		### Blend the upper shape key's delta with the lower shape key's delta
		if (vertPassesFilter): # We only incorporate RED verts into combined shape key
			newDelta = None
			
			# Additive
			if (blendMode == "add"):
				newDelta = lowerDelta + upperDelta
			
			# Subtractive
			elif (blendMode == "subtract"):
				newDelta = lowerDelta - upperDelta
			
			# Multiply
			elif (blendMode == "multiply"):
				newDelta = lowerDelta * upperDelta
			
			# Divide
			elif (blendMode == "divide"):
				newDelta = lowerDelta * upperDelta
				
			# Overwrite
			elif (blendMode == "over"):
				newDelta = upperDelta
				
			# Lerp
			elif (blendMode == "lerp"):
				newDelta = lowerDelta.lerp(upperDelta, blendModeLerp_Factor)
			
			# Update the destination shape key
			destinationShapeKeyVerts[vert.index].co = basePos + newDelta
		
	# If outputting to a new shape key, move the new merged shape key in the shape key list to sit after the upper shape key
	if (newShapeKeyIndex != None):
		while (newShapeKeyIndex > upperShapeKeyIndex + 1):
			obj.active_shape_key_index = newShapeKeyIndex
			bpy.ops.object.shape_key_move(type="UP")
			newShapeKeyIndex -= 1
	
	# Restore relative_key for the two input shape keys if necessary
	if (lowerOldBasisKey != key0):
		lowerShapeKey.relative_key = lowerOldBasisKey
	if (upperOldBasisKey != key0):
		upperShapeKey.relative_key = upperOldBasisKey
	
	# Delete the source shape keys if desired
	if (delete1OnFinish):
		obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(shapeKey1Name)
		bpy.ops.object.shape_key_remove()
	if (delete2OnFinish):
		obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(shapeKey2Name)
		bpy.ops.object.shape_key_remove()
	
	# Make the destination shape key active
	obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(destinationShapeKeyName)
	
	# Update async progress reporting for delta verts processed
	if reportAsyncProgress:
		asyncProgressReporting["CurrentVert"] = currentVert


### Splits off a new shape key from the active shape key, using the Vertex Filter to determine which deltas go to which shape key
# Params:
# - obj: The object who has the two specified shape keys to be merged
# - newShapeKeyName: Name of to-be-created new shape key
# - mode: Name of the split mode to use
# - vertexFilterParams: Dictionary of parameters for vertex filtering
# - (optional) asyncProgressReporting: An object provided by __init__ for asynchronous operation (i.e. in a modal)
def SplitFilterActiveShapeKey(obj, newShapeKeyName, mode, vertexFilterParams, asyncProgressReporting=None):
	if (vertexFilterParams == None):
		raise Exception("Vertex filter parameters must be specified.")
	
	sourceShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(obj.active_shape_key.name)
	
	# New shape key from the basis
	obj.active_shape_key_index = 0
	obj.shape_key_add(name=str(newShapeKeyName), from_mix=False)
	newShapeKeyIndex = len(obj.data.shape_keys.key_blocks) - 1
	
	basisShapeKeyVerts = obj.data.shape_keys.key_blocks[0].data
	sourceShapeKeyVerts = obj.data.shape_keys.key_blocks[sourceShapeKeyIndex].data
	newShapeKeyVerts = obj.data.shape_keys.key_blocks[newShapeKeyIndex].data
	
	# Vertex filter kernel
	vertexFilterKernel = CreateVertexFilterKernel(vertexFilterParams)
	
	# Async progress reporting
	reportAsyncProgress = False
	wm = None
	currentVert = 0
	totalVerts = 0
	if asyncProgressReporting:
		reportAsyncProgress = True
		wm = bpy.context.window_manager
		currentVert = asyncProgressReporting["CurrentVert"]
		totalVerts = asyncProgressReporting["TotalVerts"]
	
	### Update the verts of all the involved shape keys
	for vert in obj.data.vertices:
		if reportAsyncProgress:
			currentVert += 1
			if (currentVert % 100 == 0):
				wm.progress_update(currentVert)
		
		# Unfortunately, bpy does not expose relative position of each vert, so we have to calculate the deltas ourself
		basePos = basisShapeKeyVerts[vert.index].co
		sourcePos = sourceShapeKeyVerts[vert.index].co
		sourceDelta = sourcePos - basePos
		
		# Filter the vertex
		vgIndices = [vg.group for vg in vert.groups]
		vertPassesFilter = vertexFilterKernel(vgIndices, sourceDelta) # RED verts are True, BLACK verts are False.
		
		### Change shape key verts depending on the operation mode
		# RED deltas make it into the new shape key. BLACK deltas do not (those verts revert to their basis pos defined in the basis shape key).
		if (vertPassesFilter):
			if (mode == "copy"):
				# Copy delta to new shape key and leave the original shape key unchanged
				newShapeKeyVerts[vert.index].co = sourcePos * 1
			
			elif (mode == "move"):
				# Copy delta to new shape key and neutralize the delta in the original shape key
				newShapeKeyVerts[vert.index].co = sourcePos * 1
				sourceShapeKeyVerts[vert.index].co = basePos * 1
	
	# Make the newly created shape key active
	obj.active_shape_key_index = newShapeKeyIndex
	# And move it to sit after original shape key
	while (newShapeKeyIndex > sourceShapeKeyIndex + 1):
		# Move left copy
		obj.active_shape_key_index = newShapeKeyIndex
		bpy.ops.object.shape_key_move(type="UP")
		newShapeKeyIndex -= 1
	
	# Update async progress reporting for delta verts processed
	if reportAsyncProgress:
		asyncProgressReporting["CurrentVert"] = currentVert

