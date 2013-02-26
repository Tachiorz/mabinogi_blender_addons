bl_info= {
    "name": "Import Mabinogi Pleione Animation",
    "author": "Tachiorz",
    "version": (0, 1),
    "blender": (2, 5, 7),
    "location": "File > Import > Mabinogi Animation (.ani)",
    "description": "Imports a Mabinogi Animation file",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import"
}

import os, struct

import bpy
import mathutils

class MabinogiFrame():
    mTime = 0
    move = (0.0, ) * 4
    roto = (0.0, ) * 4

class MabinogiAniData():
    mDataCount = 0
    mTime = 0
    mSize = 0
    frames = list() # of MabinogiFrame()

class MabinogiAnimation:
    frameCount = 0
    baseTime = 0
    boneCount = 0
    bone = list() # of MabinogiData()
    unknown_ani = list()

def load_ani(filename, context):
    name, ext= os.path.splitext(os.path.basename(filename))
    file= open(filename, 'rb')
    ani = MabinogiAnimation()
    try:
        magic, version, ani.frameCount, _, ani.baseTime, _, ani.boneCount  = struct.unpack("<4sihhhii", file.read(22))
    except:
        print("Error parsing file header!")
        file.close()
        return
    if magic != b'pa!\x00':
        print("Not a supported file type!")
        file.close()
        return
    file.seek(9*4,1)
    for b in range(ani.boneCount):
        ani.bone += [MabinogiAniData(),]
        _, ani.bone[b].mDataCount, _, ani.bone[b].mTime, ani.bone[b].mSize = struct.unpack("<ihhii", file.read(16))
        file.seek(2*4,1)
        ani.bone[b].frames = list()
        print ("bone %d" % b)
        for f in range(ani.bone[b].mDataCount):
            ani.bone[b].frames += [MabinogiFrame(),]
            ani.bone[b].frames[f].mTime = struct.unpack("<i", file.read(4))[0]
            ani.bone[b].frames[f].move = struct.unpack("<4f", file.read(16))
            ani.bone[b].frames[f].roto = struct.unpack("<4f", file.read(16))
            print (ani.bone[b].frames[f].mTime)
            print ("%.2f %.2f %.2f %.2f" % ani.bone[b].frames[f].move)
            print ("%.2f %.2f %.2f %.2f" % ani.bone[b].frames[f].roto)


    #find if the selected object is a an armature
    armature = None
    sel_ob = None
    if len(context.selected_objects) > 0:
        sel_ob = context.selected_objects[0]
        if type(sel_ob.data) == bpy.types.Armature : armature = sel_ob.data
        else :
            print("No armature selected")
            return
    if len(armature.bones) != ani.boneCount:
        print("Bone count doesn't match")
    sel_ob.animation_data_create()
    action = bpy.data.actions.new(name=name)
    sel_ob.animation_data.action = action
    pose_bones = sel_ob.pose.bones
    for b in range(ani.boneCount):
        for f in range(ani.bone[b].mDataCount):
            context.scene.frame_set(f+1)
            pos = ani.bone[b].frames[f].move
            quat = mathutils.Quaternion(ani.bone[b].frames[f].roto)
            mat = mathutils.Matrix.Translation(pos) * quat.to_matrix().to_4x4()
            print (pose_bones[b].matrix)
            if pose_bones[b].parent is None:
                pose_bones[b].matrix = mat
            else:
                pose_bones[b].matrix = pose_bones[b].parent.matrix * mat
            pose_bones[b].keyframe_insert("rotation_quaternion")
            pose_bones[b].keyframe_insert("location")


from bpy.props import StringProperty

class IMPORT_MABINOGI_pmg(bpy.types.Operator):
    '''Import PMG Operator.'''
    bl_idname= "import.ani"
    bl_label= "Import ANI"
    bl_description= "Import a Mabinogi Animation file"
    bl_options= {'REGISTER', 'UNDO'}

    filepath= StringProperty(name="File Path", description="Filepath used for importing the ANI file", maxlen=1024, default="")

    filter_glob = StringProperty(
        default = "*.ani",
        options = {'HIDDEN'},
    )

    def execute(self, context):
        load_ani(self.filepath,
            context)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm= context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}

def menu_func_mabinogi_ani(self, context):
    self.layout.operator(IMPORT_MABINOGI_pmg.bl_idname, text="Mabinogi Animation (.ani)")

def register():
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_import.append(menu_func_mabinogi_ani)


def unregister():
    bpy.utils.unregister_module(__name__)

    bpy.types.INFO_MT_file_import.remove(menu_func_mabinogi_ani)

if __name__ == "__main__":
    register()
