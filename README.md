# Blender Add-on: CrashXform

This is a Blender add-on designed for working with models from the original Crash Bandicoot video game trilogy.

It allows you to create custom models for the games and work with models exported from them using [CrashEdit](https://github.com/airumu/CrashEdit).

## Features

* Export models to JSON for creating custom models for Crash Bandicoot 2
* Tools for optimizing models (removing unnecessary data and reducing color count)
* Convert multiple models exported from CrashEdit into shape keys
* PSX-style shader node setup

## Requirements

* Blender 4.2 or newer

## Installation

1. Download the add-on as a `.zip` file
2. Open Blender
3. Go to **Edit > Preferences > Add-ons**
4. Click **Install from Disk...** and select the downloaded `.zip`
5. Enable the add-on

## Usage

1. Create your model in Blender
2. Use the export option to generate a JSON file
3. Open the JSON file in the model converter in CrashEdit

## Guide

### 🔸Basis

* EIDs must be 5 characters long and use only the following characters:\
`0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_!`

* EIDs must end with a specific character:
  * Models: `G`
  * Animations: `V`

* Texture images must be PNG files and use either 4bpp or 8bpp color depth.\
  Black pixels (RGB 0,0,0) are treated as transparent unless the STP bit is set in CrashEdit.

### 🔹Collections

If multiple animations reference the same model, they must be placed in the same collection.\
In other words, objects in the same collection are assumed to share the same mesh, except for the root collection (Scene Collection).

A collection’s suffix or name can be used as its model EID\
(e.g. `Collection_1234G` - or just `1234G`).

### 🔹Objects

When creating animation objects, make sure to use **linked duplicates (Alt + D)** so the original mesh data is shared.

Also, don't forget to apply Location, Rotation, and Scale (**Select all (Ctrl + A) > Apply Transforms**)!

An object’s suffix or name can be used as its animation EID\
(e.g. `Object_1234V` - or just `1234V`).

### 🔹Materials

Faces without a texture must use a material named `notex`.\
Of course, the `notex` material shouldn't have any linked textures.

The following suffixes can be used for materials:
* `a` = Animation Count (HxV)
* `d` = Animation Delay
* `s` = Animation Speed
* `r=` = Animation Repeats
* `m` = Blend Mode (0=transparency, 1=additive, 2=subtractive, 3=solid)
* `f` = Face Orientation (2=double-sided)

🔻About animation textures (e.g. `Material_a3x1_r=A56,B2,C4,B2`)

The `a` parameter specifies how the texture is divided into segments.\
In this case, the texture is split into 3 columns and 1 row, producing 3 segments labeled A, B, and C from left to right.

The `r=` parameter specifies the playback sequence and duration.\
Each entry consists of a segment label followed by the number of frames it should be displayed.\
In this case, `segment A` is displayed for 56 frames, followed by `segment B` for 2 frames, `segment C` for 4 frames, and then `segment B` again for 2 frames, for a total of 64 frames per cycle.

Without `r=`, each segment is added once and played at a uniform speed.\
With `r=`, segments are duplicated in the texture list according to their specified frame counts, enabling variable playback duration per segment at the expense of increased list size.

### 🔹UVs

For regular textures, the UVs must be snapped to either 0.000 or 1.000 (you can use **UV Mapping (U) > Reset**).

If the texture is animated, the UVs must be set to the first segment (top-left aligned).

It's recommended to do the following step after editing UVs.
1. In 3D Viewport (Edit Mode), **Select all faces (A)**
2. In UV Editor, **Select all (A) > Snap (Shift + S) > Selected to Pixels**

### 🔹Animation

If keyframes exist on the mesh object, multiple frames will be exported for animation.\
Make sure that the **animation object** you want to export has keyframes, not the armature or collision objects!

### 🔹Collision

Mesh objects whose names start with `collision` are considered frame collisions.\
They must be children of the animation object.

It's an Axis-Aligned Bounding Box (AABB), so it's recommended to use a cube with no faces and no rotations.

### 🔹Special Vertex

Vertices in the vertex group named `special_{index}` are considered special vertices\
(e.g. `special_0`, `special_1`).

If vertex order doesn't matter, you can assign multiple vertices to the same vertex group.
