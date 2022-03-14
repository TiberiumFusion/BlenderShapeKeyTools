import math, mathutils
import bpy, bgl, blf


##
## Debugging
##

### Gets the status of some ogl params that may be set through glEnable/Disable or otherwise may be controlled by client code or Blender internals and are potentially relevant to the rendering we are doing
def GetGlParams():
	def getInt1(param):
		out = bgl.Buffer(bgl.GL_INT, 1)
		bgl.glGetIntegerv(param, out)
		return out.to_list()[0]
	def getInt2(param):
		out = bgl.Buffer(bgl.GL_INT, 2)
		bgl.glGetIntegerv(param, out)
		return out.to_list()
	def getInt4(param):
		out = bgl.Buffer(bgl.GL_INT, 4)
		bgl.glGetIntegerv(param, out)
		return out.to_list()
		
	def getFloat1(param):
		out = bgl.Buffer(bgl.GL_FLOAT, 1)
		bgl.glGetIntegerv(param, out)
		return out.to_list()[0]
	def getFloat2(param):
		out = bgl.Buffer(bgl.GL_FLOAT, 2)
		bgl.glGetIntegerv(param, out)
		return out.to_list()
	def getFloat4(param):
		out = bgl.Buffer(bgl.GL_FLOAT, 4)
		bgl.glGetIntegerv(param, out)
		return out.to_list()
	def getFloat16(param):
		out = bgl.Buffer(bgl.GL_FLOAT, 16)
		bgl.glGetIntegerv(param, out)
		return out.to_list()
	
	params = {
		"GL_ACCUM_ALPHA_BITS": getInt1(bgl.GL_ACCUM_ALPHA_BITS),
		"GL_ACCUM_BLUE_BITS": getInt1(bgl.GL_ACCUM_BLUE_BITS),
		"GL_ACCUM_CLEAR_VALUE": getFloat4(bgl.GL_ACCUM_CLEAR_VALUE),
		"GL_ACCUM_GREEN_BITS": getInt1(bgl.GL_ACCUM_GREEN_BITS),
		"GL_ACCUM_RED_BITS": getInt1(bgl.GL_ACCUM_RED_BITS),
		"GL_ACTIVE_TEXTURE": getInt1(bgl.GL_ACTIVE_TEXTURE),
		"GL_ALIASED_POINT_SIZE_RANGE": getInt2(bgl.GL_ALIASED_POINT_SIZE_RANGE),
		"GL_ALIASED_LINE_WIDTH_RANGE": getInt2(bgl.GL_ALIASED_LINE_WIDTH_RANGE),
		"GL_ALPHA_BIAS": getFloat1(bgl.GL_ALPHA_BIAS),
		"GL_ALPHA_BITS": getInt1(bgl.GL_ALPHA_BITS),
		"GL_ALPHA_SCALE": getInt1(bgl.GL_ALPHA_SCALE),
		"GL_ALPHA_TEST": getInt1(bgl.GL_ALPHA_TEST),
		"GL_ALPHA_TEST_FUNC": getInt1(bgl.GL_ALPHA_TEST_FUNC),
		"GL_ALPHA_TEST_REF": getFloat1(bgl.GL_ALPHA_TEST_REF),
		"GL_ARRAY_BUFFER_BINDING": getInt1(bgl.GL_ARRAY_BUFFER_BINDING),
		"GL_ATTRIB_STACK_DEPTH": getInt1(bgl.GL_ATTRIB_STACK_DEPTH),
		"GL_AUTO_NORMAL": getInt1(bgl.GL_AUTO_NORMAL),
		"GL_AUX_BUFFERS": getInt1(bgl.GL_AUX_BUFFERS),
		"GL_BLEND": getInt1(bgl.GL_BLEND),
		#"GL_BLEND_COLOR": getFloat4(bgl.GL_BLEND_COLOR), # bgl.GL_BLEND_COLOR doesnt exist
		"GL_BLEND_DST_ALPHA": getInt1(bgl.GL_BLEND_DST_ALPHA),
		"GL_BLEND_DST_RGB": getInt1(bgl.GL_BLEND_DST_RGB),
		"GL_BLEND_EQUATION_RGB": getInt1(bgl.GL_BLEND_EQUATION_RGB),
		"GL_BLEND_EQUATION_ALPHA": getInt1(bgl.GL_BLEND_EQUATION_ALPHA),
		"GL_BLEND_SRC_ALPHA": getInt1(bgl.GL_BLEND_SRC_ALPHA),
		"GL_BLEND_SRC_RGB": getInt1(bgl.GL_BLEND_SRC_RGB),
		"GL_BLUE_BIAS": getFloat1(bgl.GL_BLUE_BIAS),
		"GL_BLUE_BITS": getInt1(bgl.GL_BLUE_BITS),
		"GL_BLUE_SCALE": getInt1(bgl.GL_BLUE_SCALE),
		"GL_CLIENT_ACTIVE_TEXTURE": getInt1(bgl.GL_CLIENT_ACTIVE_TEXTURE),
		"GL_CLIENT_ATTRIB_STACK_DEPTH": getInt1(bgl.GL_CLIENT_ATTRIB_STACK_DEPTH),
		"GL_COLOR_ARRAY": getInt1(bgl.GL_COLOR_ARRAY),
		"GL_COLOR_ARRAY_BUFFER_BINDING": getInt1(bgl.GL_COLOR_ARRAY_BUFFER_BINDING),
		"GL_COLOR_ARRAY_SIZE": getInt1(bgl.GL_COLOR_ARRAY_SIZE),
		"GL_COLOR_ARRAY_STRIDE": getInt1(bgl.GL_COLOR_ARRAY_STRIDE),
		"GL_COLOR_ARRAY_TYPE": getInt1(bgl.GL_COLOR_ARRAY_TYPE),
		"GL_COLOR_CLEAR_VALUE": getFloat4(bgl.GL_COLOR_CLEAR_VALUE),
		"GL_COLOR_LOGIC_OP": getInt1(bgl.GL_COLOR_LOGIC_OP),
		"GL_COLOR_MATERIAL": getInt1(bgl.GL_COLOR_MATERIAL),
		"GL_COLOR_MATERIAL_FACE": getInt1(bgl.GL_COLOR_MATERIAL_FACE),
		"GL_COLOR_MATERIAL_PARAMETER": getInt1(bgl.GL_COLOR_MATERIAL_PARAMETER),
		#"GL_COLOR_MATRIX": getFloat16(bgl.GL_COLOR_MATRIX), # bgl.GL_COLOR_MATRIX doesn't exist
		#"GL_COLOR_MATRIX_STACK_DEPTH": getInt1(bgl.GL_COLOR_MATRIX_STACK_DEPTH), # bgl.GL_COLOR_MATRIX_STACK_DEPTH doesn't exist
		"GL_COLOR_SUM": getInt1(bgl.GL_COLOR_SUM),
		#"GL_COLOR_TABLE": getInt1(bgl.GL_COLOR_TABLE), # bgl.GL_COLOR_TABLE doesn't exist
		"GL_COLOR_WRITEMASK": getInt4(bgl.GL_COLOR_WRITEMASK),
		#"GL_CONVOLUTION_1D": getInt1(bgl.GL_CONVOLUTION_1D), # bgl.GL_CONVOLUTION_1D doesn't exist
		#"GL_CONVOLUTION_2D": getInt1(bgl.GL_CONVOLUTION_2D), # bgl.GL_CONVOLUTION_2D doesn't exist
		"GL_CULL_FACE": getInt1(bgl.GL_CULL_FACE),
		"GL_CULL_FACE_MODE": getInt1(bgl.GL_CULL_FACE_MODE),
		"GL_CURRENT_COLOR": getFloat4(bgl.GL_CURRENT_COLOR),
		"GL_CURRENT_FOG_COORD": getFloat1(bgl.GL_CURRENT_FOG_COORD),
		"GL_CURRENT_INDEX": getInt1(bgl.GL_CURRENT_INDEX),
		"GL_CURRENT_NORMAL": getFloat4(bgl.GL_CURRENT_NORMAL),
		"GL_CURRENT_PROGRAM": getInt1(bgl.GL_CURRENT_PROGRAM),
		"GL_CURRENT_RASTER_COLOR": getFloat4(bgl.GL_CURRENT_RASTER_COLOR),
		"GL_CURRENT_RASTER_POSITION_VALID": getInt4(bgl.GL_CURRENT_RASTER_POSITION_VALID),
		"GL_CURRENT_RASTER_SECONDARY_COLOR": getFloat4(bgl.GL_CURRENT_RASTER_SECONDARY_COLOR),
		"GL_CURRENT_TEXTURE_COORDS": getFloat4(bgl.GL_CURRENT_TEXTURE_COORDS),
		"GL_DEPTH_BIAS": getFloat1(bgl.GL_DEPTH_BIAS),
		"GL_DEPTH_BITS": getInt1(bgl.GL_DEPTH_BITS),
		"GL_DEPTH_CLEAR_VALUE": getFloat1(bgl.GL_DEPTH_CLEAR_VALUE),
		"GL_DEPTH_SCALE": getInt1(bgl.GL_DEPTH_SCALE),
		"GL_DEPTH_TEST": getInt1(bgl.GL_DEPTH_TEST),
		"GL_DEPTH_WRITEMASK": getInt1(bgl.GL_DEPTH_WRITEMASK),
		"GL_DITHER": getInt1(bgl.GL_DITHER),
		"GL_DRAW_BUFFER": getInt1(bgl.GL_DRAW_BUFFER),
		"GL_EDGE_FLAG": getInt1(bgl.GL_EDGE_FLAG),
		"GL_EDGE_FLAG_ARRAY": getInt1(bgl.GL_EDGE_FLAG_ARRAY),
		"GL_EDGE_FLAG_ARRAY_BUFFER_BINDING": getInt1(bgl.GL_EDGE_FLAG_ARRAY_BUFFER_BINDING),
		"GL_EDGE_FLAG_ARRAY_STRIDE": getInt1(bgl.GL_EDGE_FLAG_ARRAY_STRIDE),
		"GL_ELEMENT_ARRAY_BUFFER_BINDING": getInt1(bgl.GL_ELEMENT_ARRAY_BUFFER_BINDING),
		"GL_FEEDBACK_BUFFER_SIZE": getInt1(bgl.GL_FEEDBACK_BUFFER_SIZE),
		"GL_FEEDBACK_BUFFER_TYPE": getInt1(bgl.GL_FEEDBACK_BUFFER_TYPE),
		"GL_FOG": getInt1(bgl.GL_FOG),
		"GL_FOG_COORD_ARRAY": getInt1(bgl.GL_FOG_COORD_ARRAY),
		"GL_FOG_COORD_ARRAY_BUFFER_BINDING": getInt1(bgl.GL_FOG_COORD_ARRAY_BUFFER_BINDING),
		"GL_FOG_COORD_ARRAY_STRIDE": getInt1(bgl.GL_FOG_COORD_ARRAY_STRIDE),
		"GL_FOG_COORD_ARRAY_TYPE": getInt1(bgl.GL_FOG_COORD_ARRAY_TYPE),
		"GL_FOG_COORD_SRC": getInt1(bgl.GL_FOG_COORD_SRC),
		"GL_FOG_COLOR": getFloat4(bgl.GL_FOG_COLOR),
		"GL_FOG_DENSITY": getInt1(bgl.GL_FOG_DENSITY),
		"GL_FOG_END": getInt1(bgl.GL_FOG_END),
		"GL_FOG_HINT": getInt1(bgl.GL_FOG_HINT),
		"GL_FOG_INDEX": getInt1(bgl.GL_FOG_INDEX),
		"GL_FOG_MODE": getInt1(bgl.GL_FOG_MODE),
		"GL_FOG_START": getInt1(bgl.GL_FOG_START),
		"GL_FRONT_FACE": getInt1(bgl.GL_FRONT_FACE),
		"GL_GREEN_BIAS": getFloat1(bgl.GL_GREEN_BIAS),
		"GL_GREEN_BITS": getInt1(bgl.GL_GREEN_BITS),
		"GL_GREEN_SCALE": getInt1(bgl.GL_GREEN_SCALE),
		#"GL_HISTOGRAM": getInt1(bgl.GL_HISTOGRAM), # bgl.GL_HISTOGRAM doesn't exist
		"GL_INDEX_ARRAY": getInt1(bgl.GL_INDEX_ARRAY),
		"GL_INDEX_ARRAY_BUFFER_BINDING": getInt1(bgl.GL_INDEX_ARRAY_BUFFER_BINDING),
		"GL_INDEX_ARRAY_STRIDE": getInt1(bgl.GL_INDEX_ARRAY_STRIDE),
		"GL_INDEX_ARRAY_TYPE": getInt1(bgl.GL_INDEX_ARRAY_TYPE),
		"GL_INDEX_BITS": getInt1(bgl.GL_INDEX_BITS),
		"GL_INDEX_CLEAR_VALUE": getInt1(bgl.GL_INDEX_CLEAR_VALUE),
		"GL_INDEX_LOGIC_OP": getInt1(bgl.GL_INDEX_LOGIC_OP),
		"GL_INDEX_MODE": getInt1(bgl.GL_INDEX_MODE),
		"GL_INDEX_OFFSET": getInt1(bgl.GL_INDEX_OFFSET),
		"GL_INDEX_SHIFT": getInt1(bgl.GL_INDEX_SHIFT),
		"GL_INDEX_WRITEMASK": getInt1(bgl.GL_INDEX_WRITEMASK),
		"GL_LIGHTING": getInt1(bgl.GL_LIGHTING),
		"GL_LIGHT_MODEL_AMBIENT": getFloat4(bgl.GL_LIGHT_MODEL_AMBIENT),
		"GL_LIGHT_MODEL_COLOR_CONTROL": getInt1(bgl.GL_LIGHT_MODEL_COLOR_CONTROL),
		"GL_LIGHT_MODEL_LOCAL_VIEWER": getInt1(bgl.GL_LIGHT_MODEL_LOCAL_VIEWER),
		"GL_LIGHT_MODEL_TWO_SIDE": getInt1(bgl.GL_LIGHT_MODEL_TWO_SIDE),
		"GL_LINE_SMOOTH": getInt1(bgl.GL_LINE_SMOOTH),
		"GL_LINE_SMOOTH_HINT": getInt1(bgl.GL_LINE_SMOOTH_HINT),
		"GL_LINE_STIPPLE": getInt1(bgl.GL_LINE_STIPPLE),
		"GL_LINE_STIPPLE_PATTERN": getInt1(bgl.GL_LINE_STIPPLE_PATTERN),
		"GL_LINE_STIPPLE_REPEAT": getInt1(bgl.GL_LINE_STIPPLE_REPEAT),
		"GL_LINE_WIDTH": getInt1(bgl.GL_LINE_WIDTH),
		"GL_LINE_WIDTH_GRANULARITY": getInt1(bgl.GL_LINE_WIDTH_GRANULARITY),
		"GL_LINE_WIDTH_RANGE": getInt2(bgl.GL_LINE_WIDTH_RANGE),
		"GL_LIST_BASE": getInt1(bgl.GL_LIST_BASE),
		"GL_LIST_INDEX": getInt1(bgl.GL_LIST_INDEX),
		"GL_LIST_MODE": getInt1(bgl.GL_LIST_MODE),
		"GL_LOGIC_OP_MODE": getInt1(bgl.GL_LOGIC_OP_MODE),
		"GL_LOGIC_OP_MODE": getInt1(bgl.GL_LOGIC_OP_MODE),
		"GL_MAP_COLOR": getInt1(bgl.GL_MAP_COLOR),
		"GL_MAP_STENCIL": getInt1(bgl.GL_MAP_STENCIL),
		"GL_MATRIX_MODE": getInt1(bgl.GL_MATRIX_MODE),
		"GL_MAX_CLIP_PLANES": getInt1(bgl.GL_MAX_CLIP_PLANES),
		"GL_MAX_LIGHTS": getInt1(bgl.GL_MAX_LIGHTS),
		"GL_MAX_MODELVIEW_STACK_DEPTH": getInt1(bgl.GL_MAX_MODELVIEW_STACK_DEPTH),
		"GL_MAX_PROJECTION_STACK_DEPTH": getInt1(bgl.GL_MAX_PROJECTION_STACK_DEPTH),
		"GL_MODELVIEW_MATRIX": getFloat16(bgl.GL_MODELVIEW_MATRIX),
		"GL_MODELVIEW_STACK_DEPTH": getInt1(bgl.GL_MODELVIEW_STACK_DEPTH),
		"GL_NAME_STACK_DEPTH": getInt1(bgl.GL_NAME_STACK_DEPTH),
		"GL_NORMAL_ARRAY": getInt1(bgl.GL_NORMAL_ARRAY),
		"GL_NORMAL_ARRAY_BUFFER_BINDING": getInt1(bgl.GL_NORMAL_ARRAY_BUFFER_BINDING),
		"GL_NORMAL_ARRAY_STRIDE": getInt1(bgl.GL_NORMAL_ARRAY_STRIDE),
		"GL_NORMAL_ARRAY_TYPE": getInt1(bgl.GL_NORMAL_ARRAY_TYPE),
		"GL_NORMALIZE": getInt1(bgl.GL_NORMALIZE),
		"GL_PERSPECTIVE_CORRECTION_HINT": getInt1(bgl.GL_PERSPECTIVE_CORRECTION_HINT),
		"GL_PERSPECTIVE_CORRECTION_HINT": getInt1(bgl.GL_PERSPECTIVE_CORRECTION_HINT),
		"GL_POLYGON_MODE": getInt1(bgl.GL_POLYGON_MODE),
		"GL_POLYGON_OFFSET_FACTOR": getFloat1(bgl.GL_POLYGON_OFFSET_FACTOR),
		"GL_POLYGON_OFFSET_UNITS": getFloat1(bgl.GL_POLYGON_OFFSET_UNITS),
		"GL_POLYGON_OFFSET_FILL": getInt1(bgl.GL_POLYGON_OFFSET_FILL),
		"GL_POLYGON_OFFSET_LINE": getInt1(bgl.GL_POLYGON_OFFSET_LINE),
		"GL_POLYGON_OFFSET_POINT": getInt1(bgl.GL_POLYGON_OFFSET_POINT),
		"GL_POLYGON_SMOOTH": getInt1(bgl.GL_POLYGON_SMOOTH),
		"GL_POLYGON_SMOOTH_HINT": getInt1(bgl.GL_POLYGON_SMOOTH_HINT),
		"GL_POLYGON_STIPPLE": getInt1(bgl.GL_POLYGON_STIPPLE),
		"GL_PROJECTION_MATRIX": getFloat16(bgl.GL_PROJECTION_MATRIX),
		"GL_PROJECTION_STACK_DEPTH": getInt1(bgl.GL_PROJECTION_STACK_DEPTH),
		"GL_READ_BUFFER": getInt1(bgl.GL_READ_BUFFER),
		"GL_RED_BIAS": getFloat1(bgl.GL_RED_BIAS),
		"GL_RED_BITS": getInt1(bgl.GL_RED_BITS),
		"GL_RED_SCALE": getInt1(bgl.GL_RED_SCALE),
		"GL_RED_SCALE": getInt1(bgl.GL_RED_SCALE),
		"GL_RENDER_MODE": getInt1(bgl.GL_RENDER_MODE),
		"GL_RESCALE_NORMAL": getInt1(bgl.GL_RESCALE_NORMAL),
		"GL_RGBA_MODE": getInt1(bgl.GL_RGBA_MODE),
		"GL_SAMPLE_BUFFERS": getInt1(bgl.GL_SAMPLE_BUFFERS),
		"GL_SAMPLE_COVERAGE_VALUE": getFloat1(bgl.GL_SAMPLE_COVERAGE_VALUE),
		"GL_SAMPLE_COVERAGE_INVERT": getInt1(bgl.GL_SAMPLE_COVERAGE_INVERT),
		"GL_SAMPLES": getInt1(bgl.GL_SAMPLES),
		"GL_SCISSOR_BOX": getInt4(bgl.GL_SCISSOR_BOX),
		"GL_SCISSOR_TEST": getInt1(bgl.GL_SCISSOR_TEST),
		"GL_SECONDARY_COLOR_ARRAY": getInt1(bgl.GL_SECONDARY_COLOR_ARRAY),
		"GL_SECONDARY_COLOR_ARRAY_BUFFER_BINDING": getInt1(bgl.GL_SECONDARY_COLOR_ARRAY_BUFFER_BINDING),
		"GL_SECONDARY_COLOR_ARRAY_SIZE": getInt1(bgl.GL_SECONDARY_COLOR_ARRAY_SIZE),
		"GL_SECONDARY_COLOR_ARRAY_STRIDE": getInt1(bgl.GL_SECONDARY_COLOR_ARRAY_STRIDE),
		"GL_SECONDARY_COLOR_ARRAY_TYPE": getInt1(bgl.GL_SECONDARY_COLOR_ARRAY_TYPE),
		"GL_SELECTION_BUFFER_SIZE": getInt1(bgl.GL_SELECTION_BUFFER_SIZE),
		"GL_SHADE_MODEL": getInt1(bgl.GL_SHADE_MODEL),
		"GL_SMOOTH_LINE_WIDTH_RANGE": getInt2(bgl.GL_SMOOTH_LINE_WIDTH_RANGE),
		"GL_SMOOTH_LINE_WIDTH_GRANULARITY": getInt1(bgl.GL_SMOOTH_LINE_WIDTH_GRANULARITY),
		"GL_STENCIL_BACK_FAIL": getInt1(bgl.GL_STENCIL_BACK_FAIL),
		"GL_STENCIL_BACK_FUNC": getInt1(bgl.GL_STENCIL_BACK_FUNC),
		"GL_STENCIL_BACK_PASS_DEPTH_FAIL": getInt1(bgl.GL_STENCIL_BACK_PASS_DEPTH_FAIL),
		"GL_STENCIL_BACK_PASS_DEPTH_PASS": getInt1(bgl.GL_STENCIL_BACK_PASS_DEPTH_PASS),
		"GL_STENCIL_BACK_REF": getInt1(bgl.GL_STENCIL_BACK_REF),
		"GL_STENCIL_BACK_VALUE_MASK": getInt1(bgl.GL_STENCIL_BACK_VALUE_MASK),
		"GL_STENCIL_BACK_WRITEMASK": getInt1(bgl.GL_STENCIL_BACK_WRITEMASK),
		"GL_STENCIL_BITS": getInt1(bgl.GL_STENCIL_BITS),
		"GL_STENCIL_CLEAR_VALUE": getInt1(bgl.GL_STENCIL_CLEAR_VALUE),
		"GL_STENCIL_FAIL": getInt1(bgl.GL_STENCIL_FAIL),
		"GL_STENCIL_FUNC": getInt1(bgl.GL_STENCIL_FUNC),
		"GL_STENCIL_PASS_DEPTH_FAIL": getInt1(bgl.GL_STENCIL_PASS_DEPTH_FAIL),
		"GL_STENCIL_PASS_DEPTH_PASS": getInt1(bgl.GL_STENCIL_PASS_DEPTH_PASS),
		"GL_STENCIL_REF": getInt1(bgl.GL_STENCIL_REF),
		"GL_STENCIL_TEST": getInt1(bgl.GL_STENCIL_TEST),
		"GL_STENCIL_VALUE_MASK": getInt1(bgl.GL_STENCIL_VALUE_MASK),
		"GL_STENCIL_WRITEMASK": getInt1(bgl.GL_STENCIL_WRITEMASK),
		"GL_TEXTURE_1D": getInt1(bgl.GL_TEXTURE_1D),
		"GL_TEXTURE_BINDING_1D": getInt1(bgl.GL_TEXTURE_BINDING_1D),
		"GL_TEXTURE_2D": getInt1(bgl.GL_TEXTURE_2D),
		"GL_TEXTURE_BINDING_2D": getInt1(bgl.GL_TEXTURE_BINDING_2D),
		"GL_TEXTURE_3D": getInt1(bgl.GL_TEXTURE_3D),
		"GL_TEXTURE_BINDING_3D": getInt1(bgl.GL_TEXTURE_BINDING_3D),
		"GL_TEXTURE_BINDING_CUBE_MAP": getInt1(bgl.GL_TEXTURE_BINDING_CUBE_MAP),
		"GL_TEXTURE_COORD_ARRAY": getInt1(bgl.GL_TEXTURE_COORD_ARRAY),
		"GL_TEXTURE_COORD_ARRAY_BUFFER_BINDING": getInt1(bgl.GL_TEXTURE_COORD_ARRAY_BUFFER_BINDING),
		"GL_TEXTURE_COORD_ARRAY_SIZE": getInt1(bgl.GL_TEXTURE_COORD_ARRAY_SIZE),
		"GL_TEXTURE_COORD_ARRAY_STRIDE": getInt1(bgl.GL_TEXTURE_COORD_ARRAY_STRIDE),
		"GL_TEXTURE_COORD_ARRAY_TYPE": getInt1(bgl.GL_TEXTURE_COORD_ARRAY_TYPE),
		"GL_TEXTURE_CUBE_MAP": getInt1(bgl.GL_TEXTURE_CUBE_MAP),
		"GL_TEXTURE_MATRIX": getFloat16(bgl.GL_TEXTURE_MATRIX),
		"GL_TEXTURE_STACK_DEPTH": getInt1(bgl.GL_TEXTURE_STACK_DEPTH),
		"GL_VERTEX_ARRAY": getInt1(bgl.GL_VERTEX_ARRAY),
		"GL_VERTEX_ARRAY_BUFFER_BINDING": getInt1(bgl.GL_VERTEX_ARRAY_BUFFER_BINDING),
		"GL_VERTEX_ARRAY_SIZE": getInt1(bgl.GL_VERTEX_ARRAY_SIZE),
		"GL_VERTEX_ARRAY_STRIDE": getInt1(bgl.GL_VERTEX_ARRAY_STRIDE),
		"GL_VERTEX_ARRAY_TYPE": getInt1(bgl.GL_VERTEX_ARRAY_TYPE),
		"GL_VERTEX_PROGRAM_POINT_SIZE": getInt1(bgl.GL_VERTEX_PROGRAM_POINT_SIZE),
		"GL_VERTEX_PROGRAM_TWO_SIDE": getInt1(bgl.GL_VERTEX_PROGRAM_TWO_SIDE),
		"GL_VIEWPORT": getInt4(bgl.GL_VIEWPORT),
	}
	
	for i in range(params["GL_MAX_CLIP_PLANES"]):
		id = "GL_CLIP_PLANE" + str(i)
		if (hasattr(bgl, id)):
			params[id] = getInt1(getattr(bgl, id))
	
	for i in range(params["GL_MAX_LIGHTS"]):
		id = "GL_LIGHT" + str(i)
		if (hasattr(bgl, id)):
			params[id] = getInt1(getattr(bgl, id))
	
	return params



##
## Helpers
##

### Checks whether or not the provided euler angles (in RADIANS) are aligned with any world axis
def IsEulerOrtho(rX, rY, rZ):
	nRX = abs(rX) % (math.pi / 2)
	nRY = abs(rY) % (math.pi / 2)
	nRZ = abs(rZ) % (math.pi / 2)
	epsilon = 0.00001 # 1e-5 instead of 1e-6 to help account for quat<->euler conversion errors
	return (math.isclose(nRX, 0, abs_tol=epsilon) and math.isclose(nRY, 0, abs_tol=epsilon) and math.isclose(nRZ, 0, abs_tol=epsilon))

### Gets the projected depth of a worldspace point in "window"space (because Blender exposes a so-called "perspective" matrix instead of a projection matrix)
def GetPointSceneDepth(context, x, y, z):
	p = context.space_data.region_3d.perspective_matrix * mathutils.Vector((x, y, z, 1))
	return p.w



##
## Viewport drawing
##

### Draws a simple line
def DrawLine(color, start, end, width=1):
	bgl.glLineWidth(width)
	bgl.glColor4f(*color)
	bgl.glBegin(bgl.GL_LINES)
	bgl.glVertex3f(*start)
	bgl.glVertex3f(*end)
	bgl.glEnd()


### Draws a simple quad
def DrawQuad(p1, p2, p3, p4, fillColor=None, outlineColor=None, outlineWidth=1):
	if (fillColor != None):
		bgl.glColor4f(*fillColor)
		bgl.glBegin(bgl.GL_QUADS)
		bgl.glVertex3f(*p1)
		bgl.glVertex3f(*p2)
		bgl.glVertex3f(*p3)
		bgl.glVertex3f(*p4)
		bgl.glEnd()
	if (outlineColor != None):
		bgl.glLineWidth(outlineWidth)
		bgl.glColor4f(*outlineColor)
		bgl.glBegin(bgl.GL_LINE_LOOP)
		bgl.glVertex3f(*p1)
		bgl.glVertex3f(*p2)
		bgl.glVertex3f(*p3)
		bgl.glVertex3f(*p4)
		bgl.glEnd()


### Draws a series of identical quads with a repeating constant worldspace offset from the previous quad
def DrawQuadArray(p1, p2, p3, p4, offset=None, count=1, skipReference=False, fillColor=None, outlineColor=None, outlineWidth=1):
	# Reference quad
	if (skipReference != True):
		DrawQuad(p1, p2, p3, p4, fillColor, outlineColor, outlineWidth)
	# Array'd quads
	if (offset == None):
		offset = (0, 0, 0)
	if (count - 1 > 0):
		for i in range(count - 1):
			offX = offset[0] * (i + 1)
			offY = offset[1] * (i + 1)
			offZ = offset[2] * (i + 1)
			fp1 = (p1[0] + offX, p1[1] + offY, p1[2] + offZ)
			fp2 = (p2[0] + offX, p2[1] + offY, p2[2] + offZ)
			fp3 = (p3[0] + offX, p3[1] + offY, p3[2] + offZ)
			fp4 = (p4[0] + offX, p4[1] + offY, p4[2] + offZ)
			DrawQuad(fp1, fp2, fp3, fp4, fillColor, outlineColor, outlineWidth)


### Draws a simple cuboid
def DrawCuboid(min, max, fillColor=None, outlineColor=None, outlineWidth=1):
	### Build geometry
	verts = [
		# 'Front' face (when looking at 0,0,0 from 100,0,0)
		(max[0], min[1], max[2]), # top left (as viewed with perspective projection)
		(max[0], max[1], max[2]), # top right
		(max[0], max[1], min[2]), # bottom right
		(max[0], min[1], min[2]), # bottom left
		
		# 'Left' face
		(min[0], min[1], max[2]), # top rear (same perspective pov)
		(max[0], min[1], max[2]), # top front
		(max[0], min[1], min[2]), # bottom front
		(min[0], min[1], min[2]), # bottom rear
		
		# 'Back' face
		(min[0], max[1], max[2]), # top right
		(min[0], min[1], max[2]), # top left
		(min[0], min[1], min[2]), # bottom left
		(min[0], max[1], min[2]), # bottom right
		
		# 'Right' face
		(max[0], max[1], max[2]), # top front
		(min[0], max[1], max[2]), # top rear
		(min[0], max[1], min[2]), # bottom rear
		(max[0], max[1], min[2]), # bottom front
		
		# 'Top' face
		(min[0], min[1], max[2]), # rear left
		(min[0], max[1], max[2]), # rear right
		(max[0], max[1], max[2]), # front right
		(max[0], min[1], max[2]), # front left
		
		# 'Bottom' face
		(min[0], max[1], min[2]), # rear right
		(min[0], min[1], min[2]), # rear left
		(max[0], min[1], min[2]), # front left
		(max[0], max[1], min[2]), # front right
	]
	
	### Draw it
	if (fillColor != None):
		bgl.glColor4f(*fillColor)
		bgl.glBegin(bgl.GL_QUADS)
		for v in verts:
			bgl.glVertex3f(*v)
		bgl.glEnd()
	if (outlineColor != None):
		bgl.glLineWidth(outlineWidth)
		bgl.glColor4f(*outlineColor)
		for i in range(int(len(verts) / 4)):
			bgl.glBegin(bgl.GL_LINE_LOOP)
			for t in range(4):
				bgl.glVertex3f(*verts[(i * 4) + t])
			bgl.glEnd()


### Draws text in 3d with the specified worldspace location, rotation, and alignment
def Draw3dText(text, color, worldpos=None, localpos=None, rotations=None, scale=None, align=1, size=24, dpi=96):
	blf.size(0, size, dpi)
	textSize = blf.dimensions(0, text)
	
	bgl.glMatrixMode(bgl.GL_MODELVIEW)
	bgl.glPushMatrix()
	
	if (scale != None):
		bgl.glScalef(*scale)
	
	if (rotations != None):
		for rot in rotations:
			bgl.glRotatef(rot[0], rot[1], rot[2], rot[3]) # stride: angle, axis (xyz)
	
	# Worldspace translation is done with bgl
	if (worldpos != None):
		bgl.glTranslatef(*worldpos)
	
	# Alignment and local translation is done with bfl
	lx = 0
	ly = 0
	lz = 0
	if (localpos != None):
		lx += localpos[0]
		ly += localpos[1]
		lz += localpos[2]
	#if (align == 1): # left align
	if (align == 0): # center align
		lx += -(textSize[0] / 2)
	elif (align == -1): # right align
		lx += -(textSize[0])
	blf.position(0, lx, ly, lz)
	
	bgl.glColor4f(*color)
	
	# For some unexplained reason, blf.draw() UNsets GL_BLEND if it is enabled, which undesirable and quite frankly very stupid
	restoreGlBlend = bgl.glIsEnabled(bgl.GL_BLEND)
	blf.draw(0, text)
	if (restoreGlBlend):
		bgl.glEnable(bgl.GL_BLEND)
	
	bgl.glPopMatrix()


### Draws a fancy looking grid on a world axis aligned plane
def DrawWorldPlaneGrid(self, context, fillColor, lineColor, plane, half=None):
	# We build the geometry in the xy plane and swizzle it for the others
	# And we use the user's chosen floor grid params (under Viewport -> Display) to scale the grid divisions
	
	### Grid halves
	typeX = 0 # 0 = draw full grid, -1 = draw negative side only, 1 = draw positive side only
	typeY = 0 # ditto but for y dimen
	if (half == "-x"):
		typeX = -1
		typeY = 0
	elif (half == "+x"):
		typeX = 1
		typeY = 0
	elif (half == "-y"):
		typeX = 0
		typeY = -1
	elif (half == "+y"):
		typeX = 0
		typeY = 1
	
	### Grid fill
	planeQuadSize = context.space_data.clip_end # Camera frustum farz
	pqMinX = -planeQuadSize
	pqMaxX = planeQuadSize
	pqMinY = -planeQuadSize
	pqMaxY = planeQuadSize
	if (typeX == -1):
		pqMaxX = 0
	if (typeX == 1):
		pqMinX = 0
	if (typeY == -1):
		pqMaxY = 0
	if (typeY == 1):
		pqMinY = 0
	planeQuad = [(pqMinX, pqMinY, 0), (pqMaxX, pqMinY, 0), (pqMaxX, pqMaxY, 0), (pqMinX, pqMaxY, 0)]
	
	### Grid divisions
	
	# Side lengths of the grid squares
	bigDivSize = 100 * context.space_data.grid_scale
	smallDivSize = 10 * context.space_data.grid_scale
	
	bigGridLines = []
	maxBigGridLines = 30 # Per pos/neg grid half (so real max total is this *2)
	bigGridLineCount = min(math.ceil(planeQuadSize / bigDivSize), maxBigGridLines * 2)
	for i in range(0, bigGridLineCount):
		grad = (i * bigDivSize)
		gridRadius = min(planeQuadSize, bigGridLineCount * bigDivSize)
		# Gradations along y axis, lines run along x
		vMinX = -gridRadius
		vMaxX = gridRadius
		if (typeX < 0):
			vMaxX = 0
		elif (typeX > 0):
			vMinX = 0
		if (typeY >= 0):
			bigGridLines.extend([(vMinX, grad, 0), (vMaxX, grad, 0)])
		if (typeY <= 0):
			bigGridLines.extend([(vMinX, -grad, 0), (vMaxX, -grad, 0)])
		# Gradations along x axis, lines run along y
		vMinY = -gridRadius
		vMaxY = gridRadius
		if (typeY < 0):
			vMaxY = 0
		elif (typeY > 0):
			vMinY = 0
		if (typeX >= 0):
			bigGridLines.extend([(grad, vMinY, 0), (grad, vMaxY, 0)])
		if (typeX <= 0):
			bigGridLines.extend([(-grad, vMinY, 0), (-grad, vMaxY, 0)])
	
	smallGridLines = []
	maxSmallGridLines = maxBigGridLines * 10
	smallGridLineCount = min(math.ceil(planeQuadSize / smallDivSize), maxSmallGridLines * 2)
	for i in range(0, smallGridLineCount):
		grad = (i * smallDivSize)
		gridRadius = min(planeQuadSize, smallGridLineCount * smallDivSize)
		# Gradations along y axis, lines run along x
		vMinX = -gridRadius
		vMaxX = gridRadius
		if (typeX < 0):
			vMaxX = 0
		elif (typeX > 0):
			vMinX = 0
		if (typeY >= 0):
			smallGridLines.extend([(vMinX, grad, 0), (vMaxX, grad, 0)])
		if (typeY <= 0):
			smallGridLines.extend([(vMinX, -grad, 0), (vMaxX, -grad, 0)])
		# Gradations along x axis, lines run along y
		vMinY = -gridRadius
		vMaxY = gridRadius
		if (typeY < 0):
			vMaxY = 0
		elif (typeY > 0):
			vMinY = 0
		if (typeX >= 0):
			smallGridLines.extend([(grad, vMinY, 0), (grad, vMaxY, 0)])
		if (typeX <= 0):
			smallGridLines.extend([(-grad, vMinY, 0), (-grad, vMaxY, 0)])
	
	### Plane switch
	if (plane == "xz" or plane == "zx"):
		# Grid fill
		newPlaneQuad = []
		for v in planeQuad:
			newPlaneQuad.append((v[0], 0, v[1]))
		planeQuad = newPlaneQuad
		# Grid lines
		newBigGridLines = []
		newSmallGridLines = []
		for v in bigGridLines:
			newBigGridLines.append((v[0], 0, v[1]))
		for v in smallGridLines:
			newSmallGridLines.append((v[0], 0, v[1]))
		bigGridLines = newBigGridLines
		smallGridLines = newSmallGridLines
	elif (plane == "yz" or plane == "zy"):
		# Grid fill
		newPlaneQuad = []
		for v in planeQuad:
			newPlaneQuad.append((0, v[0], v[1]))
		planeQuad = newPlaneQuad
		# Grid lines
		newBigGridLines = []
		newSmallGridLines = []
		for v in bigGridLines:
			newBigGridLines.append((0, v[0], v[1]))
		for v in smallGridLines:
			newSmallGridLines.append((0, v[0], v[1]))
		bigGridLines = newBigGridLines
		smallGridLines = newSmallGridLines
	
	### Draw it
	# Fill
	if (fillColor != None):
		DrawQuad(planeQuad[0], planeQuad[1], planeQuad[2], planeQuad[3], fillColor)
	
	# Big grid divisions
	bgl.glLineWidth(4)
	bgl.glColor4f(*lineColor)
	bgl.glBegin(bgl.GL_LINES)
	for line in bigGridLines:
		bgl.glVertex3f(*line)
	bgl.glEnd()
	
	# Small grid divisions
	lineColor2 = (lineColor[0], lineColor[1], lineColor[2], lineColor[3] * 0.5)
	bgl.glLineWidth(2)
	bgl.glColor4f(*lineColor)
	bgl.glBegin(bgl.GL_LINES)
	for line in smallGridLines:
		bgl.glVertex3f(*line)
	bgl.glEnd()
	

### Applies default* opengl drawing parameters
#*default = what Blender's defaults** are
#**which may or may not be wrong as the docs do not provide these, so they are figured through reasonable assumptions and empiric testing
def OglDefaults():
	bgl.glDisable(bgl.GL_BLEND)
	
	bgl.glDisable(bgl.GL_LINE_SMOOTH)
	bgl.glLineWidth(1)
	
	bgl.glEnable(bgl.GL_DEPTH_TEST)
	bgl.glDepthMask(True)
	
	bgl.glDisable(bgl.GL_CULL_FACE)
	bgl.glCullFace(bgl.GL_BACK)
	
	bgl.glColor4f(0.0, 0.0, 0.0, 1.0)


##
## Main 3d draw callback
##

def ViewportDraw(self, context):
	scene = context.scene
	properties = scene.shape_key_tools_props
	
	OglDefaults()
	
	bgl.glEnable(bgl.GL_BLEND)
	bgl.glEnable(bgl.GL_LINE_SMOOTH)
	
	
	##
	## Split/merge axis visualization
	##
	
	gridFillColorSplit = (1.0, 0.9, 0.0, 0.2)
	gridLineColorSplit = (1.0, 0.9, 0.0, 0.3)
	
	gridFillColorLeft = (0.0, 1.0, 0.0, 0.2)
	gridLineColorLeft = (0.0, 1.0, 0.0, 0.25)
	
	gridFillColorRight = (1.0, 0.0, 0.0, 0.2)
	gridLineColorRight = (1.0, 0.0, 0.0, 0.25)
	
	gridLabelTextSize = 26
	
	smoothRegionFillColor = (0.0, 0.5, 1.0, 0.2)
	smoothRegionLineColor = (0.0, 0.5, 1.0, 0.3)
	
	smoothRegionIntervalFillColor = (0.0, 0.2, 1.0, 0.15)
	smoothRegionIntervalLineColor = (0.0, 0.2, 1.0, 0.35)
	
	splitAxis = properties.opt_shapepairs_split_axis
	splitMode = properties.opt_shapepairs_split_mode
	smoothingRadius = properties.opt_shapepairs_split_smoothdist
	
	drawSplitPlane = properties.opt_shapepairs_splitmerge_viewportvisualize_show_splitplane
	drawLRPlanes = properties.opt_shapepairs_splitmerge_viewportvisualize_show_splithalves
	drawSmoothRegion = properties.opt_shapepairs_splitmerge_viewportvisualize_show_smoothregion and splitMode == "smooth"
	
	viewportProjType = context.space_data.region_3d.view_perspective #https://blender.stackexchange.com/questions/181110/what-is-the-python-command-to-check-if-current-view-is-in-orthographic-or-perspe
	viewportIsOrtho = (viewportProjType == "ORTHO")
	
	# Because everything is translucent, we will read depth only (no write) and be very particular with the draw order
	# For this reason, all the geometry is split in two at 0,0,0 and we draw the halves with a basic depth sort
	
	def DrawSplitPlane(side):
		if (side == "pos"):
			if (splitAxis == "+X" or splitAxis == "-X"):
				DrawWorldPlaneGrid(self, context, gridFillColorSplit, gridLineColorSplit, "yz", "+x")
			elif (splitAxis == "+Y" or splitAxis == "-Y"):
				DrawWorldPlaneGrid(self, context, gridFillColorSplit, gridLineColorSplit, "xz", "+x")
			elif (splitAxis == "+Z" or splitAxis == "-Z"):
				DrawWorldPlaneGrid(self, context, gridFillColorSplit, gridLineColorSplit, "xy", "+x")
		elif (side == "neg"):
			if (splitAxis == "+X" or splitAxis == "-X"):
				DrawWorldPlaneGrid(self, context, gridFillColorSplit, gridLineColorSplit, "yz", "-x")
			elif (splitAxis == "+Y" or splitAxis == "-Y"):
				DrawWorldPlaneGrid(self, context, gridFillColorSplit, gridLineColorSplit, "xz", "-x")
			elif (splitAxis == "+Z" or splitAxis == "-Z"):
				DrawWorldPlaneGrid(self, context, gridFillColorSplit, gridLineColorSplit, "xy", "-x")
	
	def DrawSmoothingRegion(side):
		cuboidDepth = context.space_data.clip_end # Camera frustum farz
		intervalOffset = 3 * context.space_data.grid_scale
		intervalCount = 200
		
		# If the view is orthographic AND the camera is orthogonal, we can draw a simpler & better visualization of the smoothing cuboid region
		headOnView = False
		if (viewportIsOrtho):
			camAngles = context.space_data.region_3d.view_rotation.to_euler("XYZ") # RADIANS
			if (IsEulerOrtho(camAngles.x, camAngles.y, camAngles.z)):
				headOnView = True
		
		if (splitAxis == "+X" or splitAxis == "-X"):
			if (headOnView):
				# Main fill
				cuboidDepth *= 0.49 # In order to make the faces parallel with the ortho plane actually show up when viewed head on
				if (side == "pos"):
					DrawCuboid(min=(-smoothingRadius, 0, -cuboidDepth), max=(smoothingRadius, cuboidDepth, cuboidDepth), fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
				elif (side == "neg"):
					DrawCuboid(min=(-smoothingRadius, -cuboidDepth, -cuboidDepth), max=(smoothingRadius, 0, cuboidDepth), fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
			else:
				# Main fill
				if (side == "pos"):
					DrawCuboid(min=(-smoothingRadius, 0, -cuboidDepth), max=(smoothingRadius, cuboidDepth, cuboidDepth), fillColor=smoothRegionFillColor, outlineColor=smoothRegionLineColor, outlineWidth=1)
				elif (side == "neg"):
					DrawCuboid(min=(-smoothingRadius, -cuboidDepth, -cuboidDepth), max=(smoothingRadius, 0, cuboidDepth), fillColor=smoothRegionFillColor, outlineColor=smoothRegionLineColor, outlineWidth=1)
				# Longitude intervals
				tl = (-smoothingRadius, 0, cuboidDepth)
				tr = (smoothingRadius, 0, cuboidDepth)
				br = (smoothingRadius, 0, -cuboidDepth)
				bl = (-smoothingRadius, 0, -cuboidDepth)
				if (side == "pos"):
					DrawQuadArray(tl, tr, br, bl, offset=(0, intervalOffset, 0), count=intervalCount, fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
				elif (side == "neg"):
					DrawQuadArray(tl, tr, br, bl, offset=(0, -intervalOffset, 0), count=intervalCount, fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
				# Latitude intervals
				if (side == "neg"):
					tl = (-smoothingRadius, 0, 0)
					tr = (smoothingRadius, 0, 0)
					br = (smoothingRadius, -cuboidDepth, 0)
					bl = (-smoothingRadius, -cuboidDepth, 0)
				elif (side == "pos"):
					tl = (-smoothingRadius, cuboidDepth, 0)
					tr = (smoothingRadius, cuboidDepth, 0)
					br = (smoothingRadius, 0, 0)
					bl = (-smoothingRadius, 0, 0)
				DrawQuadArray(tl, tr, br, bl, offset=(0, 0, -intervalOffset), count=intervalCount, fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
				DrawQuadArray(tl, tr, br, bl, offset=(0, 0, intervalOffset), count=intervalCount, fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
		elif (splitAxis == "+Y" or splitAxis == "-Y"):
			if (headOnView):
				# Main fill
				cuboidDepth *= 0.49 # In order to make the faces parallel with the ortho plane actually show up when viewed head on
				if (side == "pos"):
					DrawCuboid(min=(0, -smoothingRadius, -cuboidDepth), max=(cuboidDepth, smoothingRadius, cuboidDepth), fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
				elif (side == "neg"):
					DrawCuboid(min=(-cuboidDepth, -smoothingRadius, -cuboidDepth), max=(0, smoothingRadius, cuboidDepth), fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
			else:
				# Main fill
				if (side == "pos"):
					DrawCuboid(min=(0, -smoothingRadius, -cuboidDepth), max=(cuboidDepth, smoothingRadius, cuboidDepth), fillColor=smoothRegionFillColor, outlineColor=smoothRegionLineColor, outlineWidth=1)
				elif (side == "neg"):
					DrawCuboid(min=(-cuboidDepth, -smoothingRadius, -cuboidDepth), max=(0, smoothingRadius, cuboidDepth), fillColor=smoothRegionFillColor, outlineColor=smoothRegionLineColor, outlineWidth=1)
				# Longitude intervals
				tl = (0, -smoothingRadius, cuboidDepth)
				tr = (0, smoothingRadius, cuboidDepth)
				br = (0, smoothingRadius, -cuboidDepth)
				bl = (0, -smoothingRadius, -cuboidDepth)
				if (side == "pos"):
					DrawQuadArray(tl, tr, br, bl, offset=(intervalOffset, 0, 0), count=intervalCount, fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
				if (side == "neg"):
					DrawQuadArray(tl, tr, br, bl, offset=(-intervalOffset, 0, 0), count=intervalCount, fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
				# Latitude intervals
				if (side == "neg"):
					tl = (0, -smoothingRadius, 0)
					tr = (0, smoothingRadius, 0)
					br = (-cuboidDepth, smoothingRadius, 0)
					bl = ( -cuboidDepth, -smoothingRadius, 0)
				elif (side == "pos"):
					tl = (cuboidDepth, -smoothingRadius, 0)
					tr = (cuboidDepth, smoothingRadius, 0)
					br = (0, smoothingRadius, 0)
					bl = (0, -smoothingRadius, 0)
				DrawQuadArray(tl, tr, br, bl, offset=(0, 0, -intervalOffset), count=intervalCount, fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
				DrawQuadArray(tl, tr, br, bl, offset=(0, 0, intervalOffset), count=intervalCount, fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
		elif (splitAxis == "+Z" or splitAxis == "-Z"):
			if (headOnView):
				# Main fill
				cuboidDepth *= 0.49 # In order to make the faces parallel with the ortho plane actually show up when viewed head on
				if (side == "pos"):
					DrawCuboid(min=(0, -cuboidDepth, -smoothingRadius), max=(cuboidDepth, cuboidDepth, smoothingRadius), fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
				elif (side == "neg"):
					DrawCuboid(min=(-cuboidDepth, -cuboidDepth, -smoothingRadius), max=(0, cuboidDepth, smoothingRadius), fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
			else:
				# Main fill
				if (side == "pos"):
					DrawCuboid(min=(0, -cuboidDepth, -smoothingRadius), max=(cuboidDepth, cuboidDepth, smoothingRadius), fillColor=smoothRegionFillColor, outlineColor=smoothRegionLineColor, outlineWidth=1)
				elif (side == "neg"):
					DrawCuboid(min=(-cuboidDepth, -cuboidDepth, -smoothingRadius), max=(0, cuboidDepth, smoothingRadius), fillColor=smoothRegionFillColor, outlineColor=smoothRegionLineColor, outlineWidth=1)
				# Longitude intervals
				tl = (0, cuboidDepth, -smoothingRadius)
				tr = (0, cuboidDepth, smoothingRadius)
				br = (0, -cuboidDepth, smoothingRadius)
				bl = (0, -cuboidDepth, -smoothingRadius)
				if (side == "neg"):
					DrawQuadArray(tl, tr, br, bl, offset=(-intervalOffset, 0, 0), count=intervalCount, fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
				elif (side == "pos"):
					DrawQuadArray(tl, tr, br, bl, offset=(intervalOffset, 0, 0), count=intervalCount, fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
				# Latitude intervals
				if (side == "neg"):
					tl = (0, 0, -smoothingRadius)
					tr = (0, 0, smoothingRadius)
					br = (-cuboidDepth, 0, smoothingRadius)
					bl = (-cuboidDepth, 0, -smoothingRadius)
				elif (side == "pos"):
					tl = (cuboidDepth, 0, -smoothingRadius)
					tr = (cuboidDepth, 0, smoothingRadius)
					br = (0, 0, smoothingRadius)
					bl = (0, 0, -smoothingRadius)
				DrawQuadArray(tl, tr, br, bl, offset=(0, -intervalOffset, 0), count=intervalCount, fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
				DrawQuadArray(tl, tr, br, bl, offset=(0, intervalOffset, 0), count=intervalCount, fillColor=smoothRegionIntervalFillColor, outlineColor=smoothRegionIntervalLineColor, outlineWidth=1)
	
	def DrawLeftPlane():
		if (splitAxis == "+X"):
			DrawWorldPlaneGrid(self, context, gridFillColorLeft, gridLineColorLeft, "xz", "+x")
		elif (splitAxis == "-X"):
			DrawWorldPlaneGrid(self, context, gridFillColorLeft, gridLineColorLeft, "xz", "-x")
		elif (splitAxis == "+Y"):
			DrawWorldPlaneGrid(self, context, gridFillColorLeft, gridLineColorLeft, "yz", "+x")
		elif (splitAxis == "-Y"):
			DrawWorldPlaneGrid(self, context, gridFillColorLeft, gridLineColorLeft, "yz", "-x")
		elif (splitAxis == "+Z"):
			DrawWorldPlaneGrid(self, context, gridFillColorLeft, gridLineColorLeft, "zy", "+y")
		elif (splitAxis == "-Z"):
			DrawWorldPlaneGrid(self, context, gridFillColorLeft, gridLineColorLeft, "zy", "-y")
	
	def DrawRightPlane():
		if (splitAxis == "+X"):
			DrawWorldPlaneGrid(self, context, gridFillColorRight, gridLineColorRight, "xz", "-x")
		elif (splitAxis == "-X"):
			DrawWorldPlaneGrid(self, context, gridFillColorRight, gridLineColorRight, "xz", "+x")
		elif (splitAxis == "+Y"):
			DrawWorldPlaneGrid(self, context, gridFillColorRight, gridLineColorRight, "yz", "-x")
		elif (splitAxis == "-Y"):
			DrawWorldPlaneGrid(self, context, gridFillColorRight, gridLineColorRight, "yz", "+x")
		elif (splitAxis == "+Z"):
			DrawWorldPlaneGrid(self, context, gridFillColorRight, gridLineColorRight, "zy", "-y")
		elif (splitAxis == "-Z"):
			DrawWorldPlaneGrid(self, context, gridFillColorRight, gridLineColorRight, "zy", "+y")
	
	def DrawLeftText():
		bgl.glEnable(bgl.GL_CULL_FACE)
		if (splitAxis == "+X"):
			Draw3dText("Left", color=gridLineColorLeft, localpos=(5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(90, 1, 0, 0)], scale=None, align=1, size=gridLabelTextSize)
			Draw3dText("Left", color=gridLineColorLeft, localpos=(-5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(90, 1, 0, 0), (180, 0, 1, 0)], scale=None, align=-1, size=gridLabelTextSize)
		elif (splitAxis == "-X"):
			Draw3dText("Left", color=gridLineColorLeft, localpos=(-5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(90, 1, 0, 0)], scale=None, align=-1, size=gridLabelTextSize)
			Draw3dText("Left", color=gridLineColorLeft, localpos=(5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(90, 1, 0, 0), (180, 0, 1, 0)], scale=None, align=1, size=gridLabelTextSize)
		elif (splitAxis == "+Y"):
			Draw3dText("Left", color=gridLineColorLeft, localpos=(5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(90, 1, 0, 0), (90, 0, 1, 0)], scale=None, align=1, size=gridLabelTextSize)
			Draw3dText("Left", color=gridLineColorLeft, localpos=(-5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(90, 1, 0, 0), (90, 0, 1, 0), (180, 0, 1, 0)], scale=None, align=-1, size=gridLabelTextSize)
		elif (splitAxis == "-Y"):
			Draw3dText("Left", color=gridLineColorLeft, localpos=(-5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(90, 1, 0, 0), (90, 0, 1, 0)], scale=None, align=-1, size=gridLabelTextSize)
			Draw3dText("Left", color=gridLineColorLeft, localpos=(5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(90, 1, 0, 0), (90, 0, 1, 0), (180, 0, 1, 0)], scale=None, align=1, size=gridLabelTextSize)
		elif (splitAxis == "+Z"):
			Draw3dText("Left", color=gridLineColorLeft, localpos=(5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(-90, 0, 1, 0)], scale=None, align=1, size=gridLabelTextSize)
			Draw3dText("Left", color=gridLineColorLeft, localpos=(-5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(-90, 0, 1, 0), (180, 0, 1, 0)], scale=None, align=-1, size=gridLabelTextSize)
		elif (splitAxis == "-Z"):
			Draw3dText("Left", color=gridLineColorLeft, localpos=(-5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(-90, 0, 1, 0)], scale=None, align=-1, size=gridLabelTextSize)
			Draw3dText("Left", color=gridLineColorLeft, localpos=(5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(-90, 0, 1, 0), (180, 0, 1, 0)], scale=None, align=1, size=gridLabelTextSize)
		bgl.glDisable(bgl.GL_CULL_FACE)
	
	def DrawRightText():
		bgl.glEnable(bgl.GL_CULL_FACE)
		if (splitAxis == "+X"):
			Draw3dText("Right", color=gridLineColorRight, localpos=(-5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(90, 1, 0, 0)], scale=None, align=-1, size=gridLabelTextSize)
			Draw3dText("Right", color=gridLineColorRight, localpos=(5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(90, 1, 0, 0), (180, 0, 1, 0)], scale=None, align=1, size=gridLabelTextSize)
		elif (splitAxis == "-X"):
			Draw3dText("Right", color=gridLineColorRight, localpos=(5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(90, 1, 0, 0)], scale=None, align=1, size=gridLabelTextSize)
			Draw3dText("Right", color=gridLineColorRight, localpos=(-5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(90, 1, 0, 0), (180, 0, 1, 0)], scale=None, align=-1, size=gridLabelTextSize)
		elif (splitAxis == "+Y"):
			Draw3dText("Right", color=gridLineColorRight, localpos=(-5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(90, 1, 0, 0), (90, 0, 1, 0)], scale=None, align=-1, size=gridLabelTextSize)
			Draw3dText("Right", color=gridLineColorRight, localpos=(5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(90, 1, 0, 0), (90, 0, 1, 0), (180, 0, 1, 0)], scale=None, align=1, size=gridLabelTextSize)
		elif (splitAxis == "-Y"):
			Draw3dText("Right", color=gridLineColorRight, localpos=(5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(90, 1, 0, 0), (90, 0, 1, 0)], scale=None, align=1, size=gridLabelTextSize)
			Draw3dText("Right", color=gridLineColorRight, localpos=(-5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(90, 1, 0, 0), (90, 0, 1, 0), (180, 0, 1, 0)], scale=None, align=-1, size=gridLabelTextSize)
		elif (splitAxis == "+Z"):
			Draw3dText("Right", color=gridLineColorRight, localpos=(-5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(-90, 0, 1, 0)], scale=None, align=-1, size=gridLabelTextSize)
			Draw3dText("Right", color=gridLineColorRight, localpos=(5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(-90, 0, 1, 0), (180, 0, 1, 0)], scale=None, align=1, size=gridLabelTextSize)
		elif (splitAxis == "-Z"):
			Draw3dText("Right", color=gridLineColorRight, localpos=(5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(-90, 0, 1, 0)], scale=None, align=1, size=gridLabelTextSize)
			Draw3dText("Right", color=gridLineColorRight, localpos=(-5, 5, 0), worldpos=(0, 0, 0.1), rotations=[(-90, 0, 1, 0), (180, 0, 1, 0)], scale=None, align=-1, size=gridLabelTextSize)
		bgl.glDisable(bgl.GL_CULL_FACE)
	
	### Use axis depths to sort the geometry
	dTestDist = 0.1
	dNegX = (GetPointSceneDepth(context, -dTestDist, 0, 0), 1) # tuple with dummy 2nd value for unique hashing purposes
	dNegY = (GetPointSceneDepth(context, 0, -dTestDist, 0), 2)
	dNegZ = (GetPointSceneDepth(context, 0, 0, -dTestDist), 3)
	dPosX = (GetPointSceneDepth(context, dTestDist, 0, 0), 4)
	dPosY = (GetPointSceneDepth(context, 0, dTestDist, 0), 5)
	dPosZ = (GetPointSceneDepth(context, 0, 0, dTestDist), 6)
	
	### Bind the draw ops to each axis direction
	# This is ugly as hell and the nested methods are significantly unperformant, but it makes this whole thing a lot more readable than something optimized for rendering
	drawOps = {}
	
	if (splitAxis == "+X" or splitAxis == "-X"):
		def nx():
			if (drawLRPlanes):
				if (splitAxis == "+X"):
					DrawRightPlane()
					DrawRightText()
				elif (splitAxis == "-X"):
					DrawLeftPlane()
					DrawLeftText()
		drawOps[dNegX] = nx
		def px():
			if (drawLRPlanes):
				if (splitAxis == "+X"):
					DrawLeftPlane()
					DrawLeftText()
				elif (splitAxis == "-X"):
					DrawRightPlane()
					DrawRightText()
		drawOps[dPosX] = px
		def ny():
			if (drawSplitPlane):
				DrawSplitPlane(side="neg")
			if (drawSmoothRegion):
				DrawSmoothingRegion(side="neg")
		drawOps[dNegY] = ny
		def py():
			if (drawSplitPlane):
				DrawSplitPlane(side="pos")
			if (drawSmoothRegion):
				DrawSmoothingRegion(side="pos")
		drawOps[dPosY] = py
		drawOps[dNegZ] = None
		drawOps[dPosZ] = None
	
	elif (splitAxis == "+Y" or splitAxis == "-Y"):
		def nx():
			if (drawSplitPlane):
				DrawSplitPlane(side="neg")
			if (drawSmoothRegion):
				DrawSmoothingRegion(side="neg")
		drawOps[dNegX] = nx
		def px():
			if (drawSplitPlane):
				DrawSplitPlane(side="pos")
			if (drawSmoothRegion):
				DrawSmoothingRegion(side="pos")
		drawOps[dPosX] = px
		def ny():
			if (drawLRPlanes):
				if (splitAxis == "+Y"):
					DrawRightPlane()
					DrawRightText()
				elif (splitAxis == "-Y"):
					DrawLeftPlane()
					DrawLeftText()
		drawOps[dNegY] = ny
		def py():
			if (drawLRPlanes):
				if (splitAxis == "+Y"):
					DrawLeftPlane()
					DrawLeftText()
				elif (splitAxis == "-Y"):
					DrawRightPlane()
					DrawRightText()
		drawOps[dPosY] = py
		drawOps[dNegZ] = None
		drawOps[dPosZ] = None
	
	elif (splitAxis == "+Z" or splitAxis == "-Z"):
		def nx():
			if (drawSplitPlane):
				DrawSplitPlane(side="neg")
			if (drawSmoothRegion):
				DrawSmoothingRegion(side="neg")
		drawOps[dNegX] = nx
		def px():
			if (drawSplitPlane):
				DrawSplitPlane(side="pos")
			if (drawSmoothRegion):
				DrawSmoothingRegion(side="pos")
		drawOps[dPosX] = px
		drawOps[dNegY] = None
		drawOps[dPosY] = None
		def nz():
			if (drawLRPlanes):
				if (splitAxis == "+Z"):
					DrawRightPlane()
					DrawRightText()
				elif (splitAxis == "-Z"):
					DrawLeftPlane()
					DrawLeftText()
		drawOps[dNegZ] = nz
		def pz():
			if (drawLRPlanes):
				if (splitAxis == "+Z"):
					DrawLeftPlane()
					DrawLeftText()
				elif (splitAxis == "-Z"):
					DrawRightPlane()
					DrawRightText()
		drawOps[dPosZ] = pz
	
	### Sort and draw
	bgl.glDepthMask(False)
	
	depthOrder = list(drawOps.keys())
	depthOrder.sort(key=lambda x: x[0], reverse=True)
	for depth in depthOrder:
		op = drawOps[depth]
		if (op != None):
			op()
	
	bgl.glDepthMask(True)
	
	
	### Done with all drawing, restore defaults
	OglDefaults()


##
## Main operator
##

### Returns true if any of multiple properties require this operator to draw something
def ShouldDrawAnything(context):
	scene = context.scene
	properties = scene.shape_key_tools_props
	
	# Main addon panel poll check
	if (bpy.types.OBJECT_PT_shape_key_tools_panel.poll(context) == False):
		return False
	
	# Specific property checks that enable the viewport visuals
	return (properties.opt_shapepairs_splitmerge_viewportvisualize)


### Sets to false all properties which would cause ShouldDrawAnything() to return true
def UnsetDrawingEnablerProperties(context):
	scene = context.scene
	properties = scene.shape_key_tools_props
	
	properties.opt_shapepairs_splitmerge_viewportvisualize = False


### Removes the drawing callback and considers the operator as disabled
# Param cls must be the __class__ object
def Disable(cls, context):
	if (cls.DrawingHandle3d != None):
		bpy.types.SpaceView3D.draw_handler_remove(cls.DrawingHandle3d, "WINDOW")
		cls.DrawingHandle3d = None
	cls.IsRunning = False


### bpy operator
class VIEW_3D_OT_ShapeKeyTools_ViewportVisuals(bpy.types.Operator):
	bl_idname = "view3d.shape_key_tools_viewport_visuals"
	bl_label = "Shape Key Tools Viewport Visuals"
	bl_options = {'INTERNAL'}
	
	## Statics
	IsRunning = False # True when an instance of this operator is running
	DrawingHandle3d = None # bpy handle for the 3d viewport drawing callback
	
	
	### Hook for when the current blend file is closing
	def BlendFilePreLoadWatcher(self, context):
		try:
			Disable(self.__class__, context)
		except:
			pass
	
	
	def RemoveModalTimer(self, context):		
		if (self._Timer != None):
			context.window_manager.event_timer_remove(self._Timer)
		self._Timer = None
	
	
	def modal(self, context, event):
		if (self.__class__.IsRunning and ShouldDrawAnything(context)):
			context.area.tag_redraw() # Ensure viewport refreshes
			return {'PASS_THROUGH'}
		else:
			self.RemoveModalTimer(context)
			Disable(self.__class__, context)
			context.area.tag_redraw() # Ensure viewport refreshes
			return {'CANCELLED'}
	
	
	def execute(self, context):
		if (context.area.type == "VIEW_3D"):
			# Setup 3D drawing callback for the viewport
			self.__class__.DrawingHandle3d = bpy.types.SpaceView3D.draw_handler_add(ViewportDraw, (self, context), 'WINDOW', 'POST_VIEW')
			
			# Opening a different blend file will stop this op before modal() has a chance to notice the blend file has changed
			# So we need to watch for that and clean up the drawing callback as needed
			bpy.app.handlers.load_pre.append(self.BlendFilePreLoadWatcher)
			
			self.__class__.IsRunning = True
			
			context.window_manager.modal_handler_add(self)
			self._Timer = context.window_manager.event_timer_add(0.017, context.window) # This shouldn't be necessary, but it prevents weird UI behavior from occurring
			# If this timer is not set: if the user clicks a control (like a checkbox) to disable the operator, then the entire UI will ignore mouse interaction until the user left clicks once anywhere in the window
			# Specifially, the left mouse button is stuck in the down state during this time. Moving the cursor over things like checkboxes will uncheck them.
			
			return {'RUNNING_MODAL'}
		else:
			# If the viewport isn't available, disable the Properties which enable this operator
			print("Viewport not available. Viewport visualization options have been disabled.")
			UnsetDrawingEnablerProperties(context)
			return {'CANCELLED'}
	

def register():
	bpy.utils.register_class(VIEW_3D_OT_ShapeKeyTools_ViewportVisuals)
	return VIEW_3D_OT_ShapeKeyTools_ViewportVisuals

def unregister():
	Disable(VIEW_3D_OT_ShapeKeyTools_ViewportVisuals)
	bpy.utils.unregister_class(VIEW_3D_OT_ShapeKeyTools_ViewportVisuals)
	return VIEW_3D_OT_ShapeKeyTools_ViewportVisuals

if __name__ == "__main__":
	register()
