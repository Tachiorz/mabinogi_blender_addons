bl_info= {
    "name": "Import Mabinogi Pleione Mesh Group",
    "author": "Tachiorz",
    "version": (0, 1),
    "blender": (2, 5, 7),
    "location": "File > Import > Mabinogi Mesh Group (.pmg)",
    "description": "Imports a Mabinogi Mesh Group file",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import"
}

import os
import struct

import bpy
import mathutils
from bpy_extras.image_utils import load_image

material_dict = None

class Vertex:
    x,y,z = 0,0,0
    nx,ny,nz = 0,0,0 # normals
    rgba = 0
    u,v = 0,0

class Skin:
    n = 0
    a = 0
    weight = 1.0
    b = 1
    
class MabinogiMesh:
    bone_name = ""
    mesh_name = ""
    texture_name = ""
    MinorMatrix = [[]*4 for i in range(4)]
    MajorMatrix = [[]*4 for i in range(4)]
    partNo = 0
    isAnimated = 0
    faceVertexCount = 0
    faceCount = 0
    stripFaceVertexCount = 0
    stripFaceCount = 0
    vertCount = 0
    skinCount = 0
    physicsCount = 0
    vertexList = list()
    stripVertexList = list()
    vertexArray = list()
    skinArray = list()
    physicsArray = list()
    morphFrameSize = 0
    morphFrames = ""  # placeholder, not used

def load_matrix4x4(file):
    m = mathutils.Matrix()
    for n in range(4):
        m[n][0:4] = struct.unpack("<4f", file.read(16))
    return m

def save_matrix4x4(file, m):
    for n in range(4):
        [file.write(struct.pack("<f", m[n][i])) for i in range(4)]
    return m
    
def load_quaternion(file):
    q = mathutils.Quaternion()
    q[0:5] = list(struct.unpack("<4f", file.read(16)))
    return q

def save_quaternion(file,q ):
    [file.write(struct.pack("<f", q[i])) for i in range(4)]
    return q

def load_lpstring(file):
    l = struct.unpack("<i", file.read(4))[0]
    return struct.unpack("<%ds" % l, file.read(l))[0].strip(b'\0').decode('ascii')

def load_vertex(file):
    new_v = Vertex()
    new_v.x, new_v.y, new_v.z = struct.unpack("<fff", file.read(12))
    new_v.nx, new_v.ny, new_v.nz, new_v.rgba = struct.unpack("<fffi", file.read(16))
    new_v.u, new_v.v = struct.unpack("<ff", file.read(8))
    return new_v

def load_pmbody17(file, pm):
    # read bounding box
    size = struct.unpack("<i", file.read(4))[0]
    p1 = struct.unpack("<fff", file.read(12))
    p2 = struct.unpack("<fff", file.read(12))
    p3 = struct.unpack("<fff", file.read(12))
    p4 = struct.unpack("<fff", file.read(12))
    u = struct.unpack("<fff", file.read(12))
    # read bounding box end
    pm.vertexList = list()
    for v in range(pm.faceVertexCount):
        pm.vertexList.append(struct.unpack("<h", file.read(2))[0])
    pm.stripVertexList = list()
    for v in range(pm.stripFaceVertexCount):
        pm.stripVertexList.append(struct.unpack("<h", file.read(2))[0])
    pm.vertexArray = list()
    for v in range(pm.vertCount):
        pm.vertexArray.append(load_vertex(file))
    pm.skinArray = list()
    for s in range(pm.skinCount):
        new_s = Skin()
        new_s.n, new_s.a, new_s.weight, new_s.b = struct.unpack("<iifi", file.read(16))
        pm.skinArray.append(new_s)
    pm.physicsArray = list()
    for s in range(pm.physicsCount):
        pm.physicsArray.append(struct.unpack("<32s", file.read(32)))
    if pm.isAnimated != 0:
        unk = struct.unpack("<i", file.read(4))[0]
        pm.morphFrames = file.read(pm.morphFrameSize)
    return pm

def load_pm17(file):
    pm = MabinogiMesh()
    pm_size, full_name, mesh_name = struct.unpack("<i32s128s", file.read(164))
    pm.bone_name = full_name.strip(b'\0').decode('ascii')  # todo: refactor bone_name - full_name
    pm.mesh_name = mesh_name.strip(b'\0').decode('ascii')
    print (pm.mesh_name, pm.bone_name)
    joint_name, state_name, norm_name, color_name = struct.unpack("32s32s32s32s", file.read(128))
    pm.MinorMatrix = load_matrix4x4(file)
    pm.MajorMatrix = load_matrix4x4(file)
    pm.partNo, _, _, texture, is_texture_mapped = struct.unpack("<iii32si", file.read(48))
    pm.texture_name = texture.strip(b'\0').decode('ascii')
    v = load_vertex(file)
    pm.faceVertexCount, pm.faceCount, pm.stripFaceVertexCount = struct.unpack("<iii", file.read(12))
    pm.stripFaceCount, pm.vertCount, pm.skinCount = struct.unpack("<iii", file.read(12))  # todo: refactor skin - weld
    pm.physicsCount, pm.isAnimated, pm.morphFrameSize, morphFrameCount = struct.unpack("<iiii", file.read(16))
    file.seek(16,1)
    f, faceSize, stripFaceSize, meshSize, skinSize, physicsSize = struct.unpack("<iiiiii", file.read(24))
    pm = load_pmbody17(file, pm)
    return pm

def load_pm20(file, pm_version):
    pm = MabinogiMesh()
    pm_size = struct.unpack("<i", file.read(4))[0]
    pm.MinorMatrix = load_matrix4x4(file)
    pm.MajorMatrix = load_matrix4x4(file)
    pm.partNo, unk1, unk2 = struct.unpack("<iii", file.read(12))
    is_texture_mapped = struct.unpack("<i", file.read(4))[0]
    file.seek(36,1)
    pm.faceVertexCount, pm.faceCount, pm.stripFaceVertexCount = struct.unpack("<iii", file.read(12))
    pm.stripFaceCount, pm.vertCount, pm.skinCount = struct.unpack("<iii", file.read(12))
    pm.physicsCount, pm.isAnimated, pm.morphFrameSize, morphFrameCount = struct.unpack("<iiii", file.read(16))
    file.seek(16,1)
    f, faceSize, stripFaceSize, meshSize, skinSize, physicsSize = struct.unpack("<iiiiii", file.read(24))
    pm.bone_name = load_lpstring(file)
    pm.mesh_name = load_lpstring(file)
    joint_name = load_lpstring(file)
    state_name = load_lpstring(file)
    norm_name = load_lpstring(file)
    if pm_version == 3:
        unk_string = load_lpstring(file)
    color_name = load_lpstring(file)
    pm.texture_name = load_lpstring(file)
    print (pm.mesh_name, pm.bone_name)
    pm = load_pmbody17(file, pm)
    return pm


def init_material_dict(root_path):
    global material_dict
    material_dict = dict()
    for (dirpath, dirnames, filenames) in os.walk(root_path):
        for name in filenames:
            mat_name = name[:-4]
            material_dict[mat_name] = dirpath


def load_pmg(filename,
             context):
    '''Read the PMG file.'''

    name, ext= os.path.splitext(os.path.basename(filename))
    file= open(filename, 'rb')


    try:
        magic, version, head_size, mesh_name, subgroup_count = struct.unpack("<4shi128si", file.read(142))
    except:
        print("Error parsing file header!")
        file.close()
        return
    if magic != b'pmg\x00':
        print("Not a supported file type!")
        file.close()
        return
    if version != 0x0102:
        print("Not a supported version!")
        file.close()
        return

    mesh_count = 0
    pm_subgroups_count = list()
    for i in range(subgroup_count):
        subgroup_name, pmCount = struct.unpack("<64si", file.read(68))
        file.seek(0xCC * pmCount, 1)  # skip pm header
        pm_subgroups_count.append(pmCount)
        mesh_count += pmCount
    print ("mesh count", mesh_count)

    pm_subgroups = list()
    for sg in range(subgroup_count):
        pm = list()
        for i in range(pm_subgroups_count[sg]):
            pm_magic, pm_version = struct.unpack("<4sh", file.read(6))
            if pm_magic != b'pm!\x00':
                print("Not a supported pm type!")
                file.close()
                return
            if pm_version not in (1793, 2, 3):
                print("Not a supported pm version!", pm_version)
                file.close()
                return
            print("reading mesh")
            if pm_version == 1793 : pm.append(load_pm17(file))
            if pm_version == 2 : pm.append(load_pm20(file))
            if pm_version == 3 : pm.append(load_pm20(file, pm_version))
        pm_subgroups.append(pm)

    addon_prefs = context.user_preferences.addons[__name__].preferences
    if material_dict is None:
        init_material_dict(addon_prefs.materials_path)

    #find if the selected object is a an armature
    bone_space = mathutils.Matrix(((0, 1, 0, 0),
                                   (0, 0, 1, 0),
                                   (1, 0, 0, 0),
                                   (0, 0, 0, 1)))
    armature = None
    sel_ob = None
    edit_bones = dict()
    if len(context.selected_objects) > 0:
        sel_ob = context.selected_objects[0]
        if type(sel_ob.data) == bpy.types.Armature:
            armature = sel_ob.data
            eb = armature.bones
            for i in range(len(eb)):
                bone_id = eb[i].name[eb[i].name.index('__')+3:]
                edit_bones[bone_id] = eb[i]
        else:
            # todo: deselect
            sel_ob.select = False
            print("Selected object isn't armature")
            sel_ob = None
    scn = context.scene
    prev_ob = None
    for sgi in range(len(pm_subgroups)):
        pm = pm_subgroups[sgi]
        if prev_ob is not None:
            prev_ob.select = False
            prev_ob = None
        for i in range(len(pm)):
            #Add to blender
            print("adding mesh", pm[i].mesh_name)
            bmesh = bpy.data.meshes.new(pm[i].mesh_name)
            #add vertices
            bmesh.vertices.add(pm[i].vertCount)
            for v in range(pm[i].vertCount):
                bmesh.vertices[v].co = (pm[i].vertexArray[v].x, pm[i].vertexArray[v].y, pm[i].vertexArray[v].z)
            #add polygons
            bmesh.polygons.add(pm[i].faceCount)
            for v in range(pm[i].faceCount):
                bmesh.polygons[v].loop_start = v*3
                bmesh.polygons[v].loop_total = 3
            #add loops
            bmesh.loops.add(pm[i].faceVertexCount)
            for v in range(pm[i].faceVertexCount):
                bmesh.loops[v].vertex_index = pm[i].vertexList[v]
            #add materials
            name = pm[i].texture_name
            #image = load_image(name + ".dds", os.path.dirname(filename), recursive=True, place_holder=True)
            if name not in bpy.data.materials:
                print("LOADING TEXTURE ", name)
                if name in material_dict:
                    image = load_image(name + ".dds", material_dict[name], recursive=True, place_holder=True)
                else:
                    image = load_image(name + ".dds", os.path.dirname(filename), recursive=True, place_holder=True)
                texture = bpy.data.textures.new(name=name, type='IMAGE')
                texture.image = image
                material = bpy.data.materials.new(name=name)
                material.use_shadeless = True
                material.use_transparency = True
                material.alpha = 0.0
                mtex = material.texture_slots.add()
                mtex.texture = texture
                mtex.texture_coords = 'UV'
                mtex.use_map_color_diffuse = True
                mtex.use_map_alpha = True
            else:
                material = bpy.data.materials[name]
                image = material.texture_slots[0].texture.image
            bmesh.materials.append(material)
            #add textures
            bmesh.uv_textures.new()
            uvl = bmesh.uv_layers.active.data[:]
            for v in range(pm[i].faceVertexCount):
                idx = pm[i].vertexList[v]
                uvl[v].uv = (pm[i].vertexArray[idx].u, 1-pm[i].vertexArray[idx].v)
                #print(pm[i].vertexArray[idx].u,pm[i].vertexArray[idx].v)
            for face in bmesh.uv_textures[0].data:
                face.image = image
            bmesh.validate()
            bmesh.update()
            ob = bpy.data.objects.new(pm[i].mesh_name + "_subgroup" + str(sgi), bmesh)
            (vector, rot, scale) = pm[i].MinorMatrix.decompose()
            #ob.location = rot * vector
            if sel_ob is not None:
                ob.parent = sel_ob
                ob.parent_type = 'OBJECT'
                bone_M = edit_bones[pm[i].bone_name].matrix_local * bone_space.inverted()
                ob.matrix_world = bone_M * pm[i].MinorMatrix
            else:
                ob.matrix_world = pm[i].MajorMatrix
            scn.objects.link(ob)
            #add skins
            skinList = list()
            for s in pm[i].skinArray:
                skinList += (s.n,)
            vgroup = ob.vertex_groups.new()
            vgroup.name = "_" + pm[i].bone_name
            vgroup.add(pm[i].vertexList,1.0,'REPLACE')
            if armature is not None:
                bones = dict()
                for bone in armature.bones:
                    bone_name = bone.name[bone.name.index('__')+3:]
                    bones[bone_name] = bone
                if pm[i].bone_name in bones:
                    vgroup.name = bones[pm[i].bone_name].name
                #bone = armature.bones.get('_' + pm[i].bone_name)
                #if bone is None: bone = armature.bones.get('-' + pm[i].bone_name)
                #if bone is not None:
                #    vgroup.name = bone.name
            ob.select = True
            if prev_ob is not None: prev_ob.select = True
            bpy.context.scene.objects.active = ob
            bpy.ops.object.join()
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.remove_doubles(threshold=0.1)
            bpy.ops.object.mode_set(mode='OBJECT')
            prev_ob = ob
        # add armature modifiers
        for v in prev_ob.vertex_groups:
            m = prev_ob.modifiers.new(v.name, 'ARMATURE')
            m.object = sel_ob
            m.vertex_group = v.name

    file.close()


from bpy.props import StringProperty

class IMPORT_MABINOGI_pmg(bpy.types.Operator):
    '''Import PMG Operator.'''
    bl_idname= "import.pmg"
    bl_label= "Import PMG"
    bl_description= "Import a Mabinogi Mesh Group file"
    bl_options= {'REGISTER', 'UNDO'}

    filepath= StringProperty(name="File Path", description="Filepath used for importing the PMG file", maxlen=1024, default="")
    
    filter_glob = StringProperty(
        default = "*.pmg",
        options = {'HIDDEN'},
    )
    
    def execute(self, context):
        load_pmg(self.filepath,
                 context)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm= context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


class IMPORT_MABINOGI_pmg_prefs(bpy.types.AddonPreferences):
    '''Import PMG preferences.'''
    bl_idname = __name__
    materials_path = StringProperty(
        name="Path to materials:",
        subtype='DIR_PATH'
    )

    def draw(self, context):
            layout = self.layout
            layout.label(text="Import PMG preferences")
            layout.prop(self, "materials_path")


def menu_func_mabinogi_pmg(self, context):
    self.layout.operator(IMPORT_MABINOGI_pmg.bl_idname, text="Mabinogi Mesh Group (.pmg)")

def register():
    global material_dict
    material_dict = None
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_import.append(menu_func_mabinogi_pmg)


def unregister():
    bpy.utils.unregister_module(__name__)

    bpy.types.INFO_MT_file_import.remove(menu_func_mabinogi_pmg)

if __name__ == "__main__":
    register()
