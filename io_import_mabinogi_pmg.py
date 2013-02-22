bl_info= {
    "name": "Import Mabinogi Pleione Mesh Group",
    "author": "Tachiorz",
    "version": (0, 1),
    "blender": (2, 5, 7),
    "location": "File > Import > Mabinogi Framework (.pmg)",
    "description": "Imports a Mabinogi Mesh Group file",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import"
}

import os
import struct
import copy

import bpy
import mathutils
from bpy_extras.image_utils import load_image

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
    faceVertexCount = 0
    faceCount = 0
    stripFaceVertexCount = 0
    stripFaceCount = 0
    vertCount = 0
    skinCount = 0
    vertexList = list()
    stripVertexList = list()
    vertexArray = list()
    skinArray = list()

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

def load_pm17(file):
    pm = MabinogiMesh()
    pm_size, bone_name, mesh_name = struct.unpack("<i32s128s", file.read(164))
    pm.bone_name = bone_name.strip(b'\0').decode('ascii')
    pm.mesh_name = mesh_name.strip(b'\0').decode('ascii')
    print (pm.mesh_name, pm.bone_name)
    file.seek(128,1)
    pm.MinorMatrix = load_matrix4x4(file)
    pm.MajorMatrix = load_matrix4x4(file)
    pm.partNo, _, _, texture, _ = struct.unpack("<iii32si", file.read(48))
    pm.texture_name = texture.strip(b'\0').decode('ascii')
    file.seek(36,1)
    pm.faceVertexCount, pm.faceCount, pm.stripFaceVertexCount = struct.unpack("<iii", file.read(12))
    pm.stripFaceCount, pm.vertCount, pm.skinCount = struct.unpack("<iii", file.read(12))
    file.seek(60,1)
    file.seek(60,1) # what matrix
    pm.vertexList = list()
    for v in range(pm.faceVertexCount):
        pm.vertexList.append(struct.unpack("<h", file.read(2))[0])
    pm.stripVertexList = list()
    for v in range(pm.stripFaceVertexCount):
        pm.stripVertexList.append(struct.unpack("<h", file.read(2))[0])
    pm.vertexArray = list()
    for v in range(pm.vertCount):
        new_v  = Vertex()
        new_v.x, new_v.y, new_v.z = struct.unpack("<fff", file.read(12))
        new_v.nx, new_v.ny, new_v.nz, new_v.rgba = struct.unpack("<fffi", file.read(16))
        new_v.u, new_v.v = struct.unpack("<ff", file.read(8))
        pm.vertexArray += [new_v]
    #file.seek(pm.skinCount*16,1) # skip skins
    pm.skinArray = list()
    for s in range(pm.skinCount):
        new_s = Skin()
        new_s.n, new_s.a, new_s.weight, new_s.b = struct.unpack("<iifi", file.read(16))
        pm.skinArray += [new_s]
    return pm

def load_pm20(file):
    pm = MabinogiMesh()
    pm_size = struct.unpack("<i", file.read(4))[0]
    pm.MinorMatrix = load_matrix4x4(file)
    pm.MajorMatrix = load_matrix4x4(file)
    file.seek(12,1)
    pm.partNo = struct.unpack("<i", file.read(4))[0]
    file.seek(36,1)
    pm.faceVertexCount, pm.faceCount, pm.stripFaceVertexCount = struct.unpack("<iii", file.read(12))
    pm.stripFaceCount, pm.vertCount, pm.skinCount = struct.unpack("<iii", file.read(12))
    file.seek(56,1)
    l = struct.unpack("<i", file.read(4))[0]
    bone_name = struct.unpack("<%ds" % l, file.read(l))[0]
    l = struct.unpack("<i", file.read(4))[0]
    mesh_name = struct.unpack("<%ds" % l, file.read(l))[0]
    l = struct.unpack("<i", file.read(4))[0]
    bone_name2 = struct.unpack("<%ds" % l, file.read(l))[0]
    l = struct.unpack("<i", file.read(4))[0]
    bone_name3 = struct.unpack("<%ds" % l, file.read(l))[0]
    pm.bone_name = bone_name.strip(b'\0').decode('ascii')
    pm.mesh_name = mesh_name.strip(b'\0').decode('ascii')
    print (pm.mesh_name, pm.bone_name)
    file.seek(4,1)
    l = struct.unpack("<i", file.read(4))[0]
    color_map = struct.unpack("<%ds" % l, file.read(l))[0]
    l = struct.unpack("<i", file.read(4))[0]
    texture = struct.unpack("<%ds" % l, file.read(l))[0]
    pm.texture_name = texture.strip(b'\0').decode('ascii')
    file.seek(64,1)
    pm.vertexList = list()
    for v in range(pm.faceVertexCount):
        pm.vertexList += [struct.unpack("<h", file.read(2))[0]]
    pm.stripVertexList = list()
    for v in range(pm.stripFaceVertexCount):
        pm.stripVertexList += [struct.unpack("<h", file.read(2))[0]]
    pm.vertexArray = list()
    for v in range(pm.vertCount):
        new_v  = Vertex()
        new_v.x, new_v.y, new_v.z = struct.unpack("<fff", file.read(12))
        new_v.nx, new_v.ny, new_v.nz, new_v.rgba = struct.unpack("<fffi", file.read(16))
        new_v.u, new_v.v = struct.unpack("<ff", file.read(8))
        pm.vertexArray += [new_v]
    #file.seek(pm.skinCount*16,1) # skip skins
    pm.skinArray = list()
    for s in range(pm.skinCount):
        new_s = Skin()
        new_s.n, new_s.a, new_s.weight, new_s.b = struct.unpack("<iifi", file.read(16))
        pm.skinArray += [new_s]
    return pm

def load_pmg(filename,
             context):
    '''Read the PMG file.'''

    name, ext= os.path.splitext(os.path.basename(filename))
    file= open(filename, 'rb')


    try:
        magic, version, head_size, mesh_name, mesh_type  = struct.unpack("<4shi128si", file.read(142))
    except:
        print("Error parsing file header!")
        file.close()
        return
    if magic != b'pmg\x00':
        print("Not a supported file type!")
        file.close()
        return
    if version != 258:
        print("Not a supported version!")
        file.close()
        return

    file.seek(64,1)
    mesh_count = struct.unpack("<i", file.read(4))[0]
    print ("mesh count", mesh_count)

    if mesh_type == 1:
        file.seek(204*mesh_count,1) # PM headers
    elif mesh_type == 5:
        file.seek(204*mesh_count,1) # PM headers
        file.seek(272*4,1) # PM2 headers
        mesh_count += 4
    else:
        print("Not supported PMG type", mesh_type)
        file.close()
        return
    pm = list()
    for i in range(mesh_count):
        pm_magic, pm_version  = struct.unpack("<4sh", file.read(6))
        if pm_magic != b'pm!\x00':
            print("Not a supported pm type!")
            file.close()
            return
        if pm_version != 1793 and pm_version != 2:
            print("Not a supported pm version!", pm_version)
            file.close()
            return

        print("reading mesh")
        if pm_version == 1793 : pm += [load_pm17(file)]
        if pm_version == 2 : pm += [load_pm20(file)]

    #find if the selected object is a an armature
    armature = None
    sel_ob = None
    if len(context.selected_objects) > 0:
        sel_ob = context.selected_objects[0]
        if type(sel_ob.data) == bpy.types.Armature : armature = sel_ob.data
        else : print("No armature selected")
    scn = context.scene
    prev_ob = None
    for i in range(mesh_count):
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
            material =  bpy.data.materials[name]
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
        ob = bpy.data.objects.new(pm[i].mesh_name, bmesh)
        (vector, rot, scale) = pm[i].MinorMatrix.decompose()
        #ob.location = rot * vector
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
            bone = armature.bones.get('_' + pm[i].bone_name)
            if bone is None: bone = armature.bones.get('-' + pm[i].bone_name)
            if bone is not None:
                vgroup.name = bone.name
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

def menu_func_mabinogi_pmg(self, context):
    self.layout.operator(IMPORT_MABINOGI_pmg.bl_idname, text="Mabinogi Mesh Group (.pmg)")

def register():
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_import.append(menu_func_mabinogi_pmg)


def unregister():
    bpy.utils.unregister_module(__name__)

    bpy.types.INFO_MT_file_import.remove(menu_func_mabinogi_pmg)

if __name__ == "__main__":
    register()
