bl_info= {
    "name": "Import Mabinogi Framework",
    "author": "Tachiorz",
    "version": (0, 3),
    "blender": (2, 5, 7),
    "location": "File > Import > Mabinogi Framework (.frm)",
    "description": "Imports a Mabinogi Framework",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export"
}

import os
import struct

import bpy
import mathutils

class MabinogiBone():
    """Framework Bone structure
    Used in bone import. Discarded after importing to blender data.
    Link -- unknown
    name -- bone name, used to bind meshes
    quat1 -- unknown
    quat2 -- unknown, contains global bone coordinate
    """
    GlobalToLocal = mathutils.Matrix()
    LocalToGlobal = mathutils.Matrix()
    Link = mathutils.Matrix()
    name = b''
    boneid = 0
    parentid = -1
    quat1 = mathutils.Quaternion()
    quat2 = mathutils.Quaternion()

class MabinogiHash():
    """Hash of bone names"""
    count = 0 # number of keys in hash
    count2= 0
    size1 = 0
    size2 = 0
    totalsize = 0
    h1 = list() #[maxlen][256]
    h2 = list() #[maxlen][256]
    h3 = list()
    maxlen = 0 # max length of key
    keys = list()
    hash1 = 0
    hash2 = 0

    def ExportQuerySize(self):
        self.size2 = 2*self.count2
        self.size1 = self.maxlen*512
        self.totalsize = 28 + self.size2 + self.size1*2
        return self.totalsize

    def GenerateRandomTable(self):
        self.h1 = list()
        self.h2 = list()
        self.h3 = [0] * self.count2
        for pos in range(self.maxlen):
            self.h1.append(list())
            self.h2.append(list())
            for i in range(256):
                self.h1[pos].append(ord(os.urandom(1)))
                self.h2[pos].append(ord(os.urandom(1)))
                self.h1[pos][i] %= self.count2
                self.h2[pos][i] %= self.count2

    def F(self, key):
        self.hash1 = 0
        self.hash2 = 0
        l = len(key)
        if l <= self.maxlen:
            for i in range(l):
                self.hash1 += self.h1[i][ord(key[i])]
                self.hash2 += self.h2[i][ord(key[i])]
                if self.hash1 >= self.count2:
                    self.hash1 -= self.count2
                if self.hash2 >= self.count2:
                    self.hash2 -= self.count2
            return 1
        else:
            return 0

    def AddKey(self,key):
        print("Adding key ",key)
        self.keys.append(key)
        self.count = len(self.keys)
        self.count2 = self.count*2
        if self.maxlen < len(key):
            self.maxlen = len(key)

    def CheckCycle(self):
        check1 = [[-1]*self.count2 for _ in range(self.count2)]
        check2 = [0] * self.count2
        i = 0
        for key in self.keys:
            self.F(key)
            if self.hash1 == self.hash2 or check1[self.hash1][self.hash2] != -1:
                return False
            check1[self.hash1][self.hash2] = i
            check1[self.hash2][self.hash1] = i
            i += 1
        for i in range(self.count2):
            if check2[i] == 0:
                self.h3[i] = 0
                if self.Traverse(-1, i, check1, check2):
                    return False
        return True

    def Traverse(self, xx, y, check1, check2):
        check2[y] = 1
        if self.count2 <= 0:
            return False
        for x in range(self.count2):
            c = check1[y][x]
            if c != -1:
                if check2[x] == 1:
                    if x != xx:
                        return True
                else:
                    self.h3[x] = c - self.h3[y]
                    while self.h3[x] < 0:
                        self.h3[x] += self.count
                    while self.h3[x] >= self.count:
                        self.h3[x] -= self.count
                    if self.Traverse(y, x, check1, check2):
                        return True
        return False

    def BuildTable(self):
        """Generates hash from names added by AddKey()"""
        result = False
        while not result:
            print("trying to build hash...")
            self.GenerateRandomTable()
            result = self.CheckCycle()

    def GetHashValue(self, key):
        self.F(key)
        result = self.h3[self.hash1] + self.h3[self.hash2]
        while result < 0:
            result += self.count
        while result >= self.count:
            result -= self.count
        return result

    def ToFile(self, file):
        """Writes hash to file
        BuildTable() must be called first!
        """
        file.write(struct.pack("<hhii3ihh", self.count, self.count2,
            self.size1, self.size2, 0, 0, 0, self.maxlen, 0))
        for n in range(self.maxlen):
            [file.write(struct.pack("<h", self.h1[n][i])) for i in range(256)]
        for n in range(self.maxlen):
            [file.write(struct.pack("<h", self.h2[n][i])) for i in range(256)]
        [file.write(struct.pack("<h", self.h3[i])) for i in range(self.count2)]

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
    
def load_frm(filename,
             context):
    '''Read and import the FRM file.'''
    name, ext= os.path.splitext(os.path.basename(filename))
    file= open(filename, 'rb')

    try:
        magic, version, bones_count = struct.unpack("<4shh", file.read(8))
    except:
        print("Error parsing file header!")
        file.close()
        return
    if magic != b'pf!\x00':
        print("Not a supported file type!")
        file.close()
        return
    if version != 1:
        print("Not a supported version!")
        file.close()
        return

    print("bones count = ", bones_count)

    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.armature_add()
    arm_object= bpy.context.active_object
    arm_object.name= "ARM_" + name
    arm_object.data.name= arm_object.name
    bpy.ops.object.mode_set(mode='EDIT')
    bones = arm_object.data.edit_bones
    for b in bones:
        bones.remove(b)
    
    bone = list()
    for b in range(bones_count):
        bone.append(MabinogiBone())
        bone[b].GlobalToLocal = load_matrix4x4(file)
        bone[b].LocalToGlobal = load_matrix4x4(file)
        bone[b].Link = load_matrix4x4(file)
        bone[b].name, bone[b].boneid, bone[b].parentid, empty = struct.unpack("<32sbbh", file.read(36))
        bone[b].quat1 = load_quaternion(file)
        bone[b].quat2 = load_quaternion(file)
        print(bone[b].boneid, bone[b].parentid, bone[b].name.decode(encoding="ascii"))
        nb = bones.new(bone[b].name.decode(encoding="ascii"))
        #nb.use_inherit_rotation = True
        if(bone[b].parentid == -1):
            nb.head = (0,0,0)
            nb.use_connect = False
        else:
            nb.parent = bone[bone[b].parentid].nb
            nb.head = nb.parent.tail
            nb.use_connect = True
        #use quat2 for bone coordinate
        #nb.tail = bone[b].quat2[0:3]

        #use Link matrix for bone translation and rotation
        #this is used in nciky PMG viewer
        (vector, rot, scale) = bone[b].Link.decompose()
        nb.tail = rot * vector + nb.head

        #use LocalToGlobal for bone coordinate
        #(vector, rot, scale) = bone[b].LocalToGlobal.decompose()
        #nb.tail = vector

        #nb.align_roll( mathutils.Vector(bone[b].quat1[0:3]) )
        bone[b].nb = nb
        #print (vector,rot, scale)

    '''
    bpy.ops.object.mode_set(mode='OBJECT')
    for b in range(bones_count):
        name = bone[b].name.decode(encoding="ascii")
        (vector, rot, scale) = bone[b].LocalToGlobal.decompose()
        arm_object.pose.bones[name].rotation_quaternion = rot
    '''
    
    file.close()

def save_frm(filename,
             context):
    """Export to FRM file.
    Doesn't work at this moment
    """
    name, ext= os.path.splitext(os.path.basename(filename))
    
    arm_object = bpy.context.active_object
    if arm_object.type != 'ARMATURE':
        print("Select armature please")
        return
    try:
        file = open(filename, 'wb')
    except:
        print("Can't create file: " + filename)
        return
    if arm_object.data.bones.find('-com') == -1:
        print("Armature don't have '-com' bone!")
        #return
    bpy.ops.object.mode_set(mode='EDIT')
    bones = arm_object.data.edit_bones[0].children_recursive
    bones[:0] = [arm_object.data.edit_bones[0]]
    bones_count = len(bones)
    
    #write header
    file.write(struct.pack('<4shh',b'pf!\x00',1,bones_count))

    hash = MabinogiHash()

    #write bones
    for b in range(bones_count):
        m1 = mathutils.Matrix.Translation(bones[b].tail)
        m2 = mathutils.Matrix.Translation(bones[b].tail)
        m2.invert()
        save_matrix4x4(file, m1)
        save_matrix4x4(file, m2)
        if bones[b].parent == None:
            parentid = -1
            m3 = bones[b].matrix
        else:
            parentid = bones.index(bones[b].parent)
            m3 = mathutils.Matrix.Translation(bones[b].parent.head - bones[b].tail)
        save_matrix4x4(file, m3)
        file.write(struct.pack("<32sbbh",bones[b].name.encode("utf-8"), b, parentid, 0))
        save_quaternion(file,[0,0,0,1])
        save_quaternion(file,list(bones[b].tail[:]) + [1])
        hash.AddKey(bones[b].name[1:])

    #write hash
    its_good = False
    while not its_good:
        hash.BuildTable()
        i = 0
        for k in hash.keys:
            if i != hash.GetHashValue(k):
                its_good = False
                print("It's not good, recalculate =|")
                break
            else:
                print(i)
                its_good = True
            i += 1
    file.write( struct.pack("<i",hash.ExportQuerySize()) )
    hash.ToFile(file)

    file.close()

from bpy.props import StringProperty

class IMPORT_MABINOGI_frm(bpy.types.Operator):
    '''Import FRM Operator.'''
    bl_idname= "import.frm"
    bl_label= "Import FRM"
    bl_description= "Import a Mabinogi Framework file"
    bl_options= {'REGISTER', 'UNDO'}

    filepath= StringProperty(name="File Path", description="Filepath used for importing the FRM file", maxlen=1024, default="")

    def execute(self, context):
        load_frm(self.filepath,
                 context)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm= context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}

class EXPORT_MABINOGI_frm(bpy.types.Operator):
    '''Export FRM Operator.'''
    bl_idname= "export.frm"
    bl_label= "Export FRM"
    bl_description= "Export a Mabinogi Framework file"
    bl_options= {'REGISTER', 'UNDO'}

    filepath= StringProperty(name="File Path", description="Filepath used for exporting the FRM file", maxlen=1024, default="")

    def execute(self, context):
        save_frm(self.filepath,
                 context)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm= context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
def menu_func(self, context):
    self.layout.operator(IMPORT_MABINOGI_frm.bl_idname, text="Mabinogi Framework (.frm)")
    
def menu_func2(self, context):
    self.layout.operator(EXPORT_MABINOGI_frm.bl_idname, text="Mabinogi Framework (.frm)")
    
def register():
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_import.append(menu_func)
    bpy.types.INFO_MT_file_export.append(menu_func2)


def unregister():
    bpy.utils.unregister_module(__name__)

    bpy.types.INFO_MT_file_import.remove(menu_func)
    bpy.types.INFO_MT_file_export.remove(menu_func2)

if __name__ == "__main__":
    register()
