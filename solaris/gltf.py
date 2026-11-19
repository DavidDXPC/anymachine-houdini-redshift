"""Import static glTF 2 meshes into Solaris. Preserve node instances and texture coordinates."""
import base64
from hashlib import sha256
import json
import os
from pathlib import Path
import struct
import tempfile
from urllib.parse import unquote

import numpy as np
from pxr import Gf, Sdf, UsdGeom, UsdShade, Vt
from . import looks


DTYPES={5120:"i1",5121:"u1",5122:"<i2",5123:"<u2",5125:"<u4",5126:"<f4"}
WIDTHS={"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4}
MIME={"image/jpeg":".jpg","image/png":".png","image/webp":".webp"}


def _resource(uri,folder):
    if uri.startswith("data:"):
        head,data=uri.split(",",1)
        if not head.endswith(";base64"):raise ValueError("Only base64 data URIs are supported")
        return base64.b64decode(data,validate=True)
    if "://" in uri:raise ValueError("Use a local glTF with local resources")
    return (folder/unquote(uri)).read_bytes()


class Document:
    def __init__(self,path):
        self.path=path
        raw=path.read_bytes()
        binary=None
        if raw[:4]==b"glTF":
            _,version,total=struct.unpack_from("<4sII",raw)
            if version!=2 or total!=len(raw):raise ValueError("Invalid GLB header")
            cursor=12
            chunks={}
            while cursor<total:
                length,kind=struct.unpack_from("<I4s",raw,cursor);cursor+=8
                if cursor+length>total:raise ValueError("Truncated GLB chunk")
                chunks[kind]=raw[cursor:cursor+length];cursor+=length
            self.doc=json.loads(chunks[b"JSON"])
            binary=chunks.get(b"BIN\0")
        else:self.doc=json.loads(raw)
        if self.doc["asset"]["version"]!="2.0":raise ValueError("Expected glTF 2.0")
        self.buffers=[]
        for info in self.doc.get("buffers",[]):
            data=_resource(info["uri"],path.parent) if "uri" in info else binary
            if data is None or len(data)<info["byteLength"]:raise ValueError("Incomplete buffer")
            self.buffers.append(data)

    def view(self,index):
        view=self.doc["bufferViews"][index];start=view.get("byteOffset",0)
        return memoryview(self.buffers[view["buffer"]])[start:start+view["byteLength"]]

    def accessor(self,i):
        a=self.doc["accessors"][i];dtype=np.dtype(DTYPES[a["componentType"]]);n=a["count"];w=WIDTHS[a["type"]]
        if "bufferView" in a:
            view=self.doc["bufferViews"][a["bufferView"]]
            arr=np.ndarray((n,w),dtype,self.view(a["bufferView"]),a.get("byteOffset",0),
                           strides=(view.get("byteStride",dtype.itemsize*w),dtype.itemsize))
        else:arr=np.zeros((n,w),dtype)
        if "sparse" in a:
            sparse=a["sparse"];count=sparse["count"];idx=sparse["indices"];val=sparse["values"]
            indices=np.frombuffer(self.view(idx["bufferView"]),DTYPES[idx["componentType"]],count,idx.get("byteOffset",0))
            arr=arr.copy()
            arr[indices]=np.frombuffer(self.view(val["bufferView"]),dtype,count*w,val.get("byteOffset",0)).reshape(-1,w)
        if a.get("normalized") and np.issubdtype(dtype,np.integer):
            arr=np.maximum(arr.astype("float32")/np.iinfo(dtype).max,-1.)
        return arr

    def texture(self,info):
        if info.get("texCoord",0)!=0 or info.get("extensions"):
            raise ValueError("Texture transforms and auxiliary UV sets need a prepared USD asset")
        tex=self.doc["textures"][info["index"]];img=self.doc["images"][tex["source"]]
        if "bufferView" in img:data=self.view(img["bufferView"])
        else:data=_resource(img["uri"],self.path.parent)
        mime=img.get("mimeType")
        if not mime and img.get("uri","").startswith("data:"):mime=img["uri"][5:].split(";")[0]
        ext=MIME.get(mime,Path(img.get("uri","")).suffix.lower())
        if ext not in MIME.values():raise ValueError("Prepare image textures in PNG, JPEG or WebP")
        folder=Path(tempfile.gettempdir())/"anykit-textures";folder.mkdir(exist_ok=True)
        path=folder/(sha256(data).hexdigest()+ext)
        if not path.is_file():
            with tempfile.NamedTemporaryFile(dir=folder,delete=False) as f:
                f.write(data);staged=f.name
            os.replace(staged,path)
        return path.as_posix()


def matrix(node):
    if "matrix" in node:return Gf.Matrix4d(*node["matrix"])
    x,y,z,w=node.get("rotation",[0,0,0,1])
    rot=Gf.Matrix4d().SetRotate(Gf.Quatd(w,Gf.Vec3d(x,y,z)))
    scale=Gf.Matrix4d().SetScale(Gf.Vec3d(*node.get("scale",[1,1,1])))
    return scale*rot*Gf.Matrix4d().SetTranslate(Gf.Vec3d(*node.get("translation",[0,0,0])))


def load(stage,path,file,strip_root_rotation=False):
    src=Document(file);d=src.doc
    root=UsdGeom.Xform.Define(stage,path)
    materials=[]
    indices=[None]+d.get("materials",[])
    for i,mat in enumerate(indices):
        mat=mat or {};pbr=mat.get("pbrMetallicRoughness",{})
        colors=pbr.get("baseColorFactor",[1,1,1,1])
        textures={}
        for key,texture in (("base",pbr.get("baseColorTexture")),("orm",pbr.get("metallicRoughnessTexture")),("normal",mat.get("normalTexture"))):
            if texture:textures[key]=src.texture(texture)
        emit=looks.ap1(mat.get("emissiveFactor",[0,0,0]))
        strength=mat.get("extensions",{}).get("KHR_materials_emissive_strength",{}).get("emissiveStrength",1)
        materials.append(looks.material(stage,f"{path}/Looks/Finish_{i}",looks.ap1(colors[:3]),
                     float(pbr.get("metallicFactor",1)),float(pbr.get("roughnessFactor",1)),
                     [e*strength for e in emit],mat.get("extensions",{}).get("KHR_materials_transmission",{}).get("transmissionFactor",0),
                     textures,colors[3],mat.get("alphaMode","OPAQUE"),mat.get("alphaCutoff",.5)))
    nodes=d["nodes"]
    selected=d["scenes"][d.get("scene",0)]["nodes"] if d.get("scenes") else sorted(set(range(len(nodes)))-{idx for n in nodes for idx in n.get("children",[])})
    def visit(index,parent,ancestry):
        if index in ancestry:raise ValueError("Cyclic glTF scene graph")
        node=nodes[index]
        if "skin" in node:raise ValueError("Bake skinned input to a static prop before importing")
        local=UsdGeom.Xform.Define(stage,f"{parent}/Node_{index}")
        transform=matrix(node)
        if strip_root_rotation and not ancestry:
            xf=Gf.Transform(transform);xf.SetRotation(Gf.Rotation());transform=xf.GetMatrix()
        local.AddTransformOp().Set(transform)
        local.GetPrim().SetDisplayName(node.get("name",f"Node {index}"))
        if "mesh" in node:
            for j,prim in enumerate(d["meshes"][node["mesh"]]["primitives"]):
                if prim.get("mode",4)!=4 or "targets" in prim:raise ValueError("Expected a static triangle list")
                if "KHR_draco_mesh_compression" in prim.get("extensions",{}):raise ValueError("Decode Draco before importing the mesh")
                attrs=prim["attributes"];points=src.accessor(attrs["POSITION"])
                faces=src.accessor(prim["indices"]).ravel() if "indices" in prim else np.arange(len(points))
                if len(faces)%3 or not len(faces) or faces.min()<0 or faces.max()>=len(points):raise ValueError("Invalid glTF triangle indices")
                mesh=UsdGeom.Mesh.Define(stage,local.GetPath().AppendChild(f"Surface_{j}"))
                mesh.CreateSubdivisionSchemeAttr("none")
                mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.ascontiguousarray(points,dtype="float32")))
                mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.asarray(faces,dtype="int32")))
                mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(faces)//3,3,dtype="int32")))
                if "NORMAL" in attrs:
                    ns=np.ascontiguousarray(src.accessor(attrs["NORMAL"]),dtype="float32")
                    mesh.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(ns));mesh.SetNormalsInterpolation("vertex")
                if "TEXCOORD_0" in attrs:
                    uv=np.array(src.accessor(attrs["TEXCOORD_0"]),dtype="float32",copy=True);uv[:,1]=1-uv[:,1]
                    UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st",Sdf.ValueTypeNames.TexCoord2fArray,"vertex").Set(Vt.Vec2fArray.FromNumpy(uv))
                UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(materials[prim.get("material",-1)+1])
        for child in node.get("children",[]):visit(child,local.GetPath(),ancestry|{index})
    for idx in selected:visit(idx,path,set())
    return root

