/*
 * Author: Nicolaj 'Eastvillage', @NicEastvillage
 */

using System;
using System.Collections;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Numerics;
using RedUtils.Math;
using RLBotDotNet.Renderer;

namespace RedUtils
{
    /// <summary>An extension of the default Renderer to draw debug lines in-game.
    /// <para>Use `page+up` and `page+down` to enable/disable RLBot's rendering.</para>
    /// </summary>
    public class ExtendedRenderer
    {
        /// <summary>Default color.
        /// When a draw function is called without a specific color, this color will be used. 
        /// Useful when you want to draw multiple things in a row using the same color.
        /// </summary>
        public Color Color = Color.White;
        /// <summary>Reference to the default renderer</summary>
        private readonly Renderer _renderer;

        /// <summary>Initialize an ExtendedRenderer using the given Renderer</summary>
        public ExtendedRenderer(Renderer renderer)
        {
            _renderer = renderer;
        }

        /// <summary>Draws text in screenspace</summary>
        public void Text2D(string text, Vec3 upperLeft, int scale = 1, Color? color = null)
        {
            _renderer.DrawString2D(text, color ?? Color, NumVec2(upperLeft), scale, scale);
        }

        /// <summary>Draws text at a point in world space</summary>
        public void Text3D(string text, Vec3 pos, int scale = 1, Color? color = null)
        {
            _renderer.DrawString3D(text, color ?? Color, NumVec(pos), scale, scale);
        }

        /// <summary>Draws a rectangle at a point in world space</summary>
        public void Rect3D(Vec3 pos, int width, int height, bool fill = true, Color? color = null)
        {
            _renderer.DrawRectangle3D(color ?? Color, NumVec(pos), width, height, fill);
        }

        /// <summary>Draws a line in world space</summary>
        public void Line3D(Vec3 start, Vec3 end, Color? color = null)
        {
            _renderer.DrawLine3D(color ?? Color, NumVec(start), NumVec(end));
        }

        /// <summary>Draws a line in screenspace</summary>
        public void Line2D(Vec3 start, Vec3 end, Color? color = null)
        {
            _renderer.DrawLine2D(color ?? Color, NumVec2(start), NumVec2(end));
        }

        /// <summary>Draws a line in world space consisting between each pair of points in the given array</summary>
        public void Polyline3D(IEnumerable<Vec3> points, Color? color = null)
        {
            _renderer.DrawPolyLine3D(color ?? Color, points.Select(NumVec).ToArray());
        }

        /// <summary>Draws a line in screen space consisting between each pair of points in the given array</summary>
        public void Polyline2D(IEnumerable<Vec3> points, Color? color = null)
        {
            _renderer.DrawPolyLine2D(color ?? Color, points.Select(NumVec2).ToArray());
        }

        /// <summary>Draws a circle</summary>
        public void Circle(Vec3 pos, Vec3 normal, float radius, Color? color = null)
        {
            Vec3 offset = normal.Cross(pos).Normalize() * radius;
            int segments = (int)MathF.Pow(radius, 0.69f) + 4;
            float angle = 2 * MathF.PI / segments;
            Mat3x3 rotMat = Mat3x3.RotationFromAxis(normal.Normalize(), angle);

            Vec3[] points = new Vec3[segments + 1];
            for (int i = 0; i <= segments; i++) {
                offset = rotMat.Dot(offset);
                points[i] = pos + offset;
            }

            Polyline3D(points, color);
        }

        /// <summary>Draws a cross</summary>
        public void Cross(Vec3 pos, float size, Color? color = null)
        {
            float half = size / 2;
            Line3D(pos + half * Vec3.X, pos - half * Vec3.X, color);
            Line3D(pos + half * Vec3.Y, pos - half * Vec3.Y, color);
            Line3D(pos + half * Vec3.Z, pos - half * Vec3.Z, color);
        }

        /// <summary>Draws an angled cross</summary>
        public void CrossAngled(Vec3 pos, float size, Color? color = null)
        {
            float r = 0.5f * size / MathF.Sqrt(2);;
            Line3D(pos + new Vec3(r, r, r), pos + new Vec3(-r, -r, -r), color);
            Line3D(pos + new Vec3(r, r, -r), pos + new Vec3(-r, -r, r), color);
            Line3D(pos + new Vec3(r, -r, -r), pos + new Vec3(-r, r, r), color);
            Line3D(pos + new Vec3(r, -r, r), pos + new Vec3(-r, r, -r), color);
        }

        /// <summary>Draws a cube</summary>
        public void Cube(Vec3 pos, float size, Color? color = null)
        {
            Cube(pos, new Vec3(size, size, size), color);
        }

        /// <summary>Draws a cube</summary>
        public void Cube(Vec3 pos, Vec3 size, Color? color = null)
        {
            Vec3 half = size / 2;
            Line3D(pos + new Vec3(-half.x, -half.y, -half.z), pos + new Vec3(-half.x, -half.y, half.z), color);
            Line3D(pos + new Vec3(half.x, -half.y, -half.z), pos + new Vec3(half.x, -half.y, half.z), color);
            Line3D(pos + new Vec3(-half.x, half.y, -half.z), pos + new Vec3(-half.x, half.y, half.z), color);
            Line3D(pos + new Vec3(half.x, half.y, -half.z), pos + new Vec3(half.x, half.y, half.z), color);
            
            Line3D(pos + new Vec3(-half.x, -half.y, -half.z), pos + new Vec3(-half.x, half.y, -half.z), color);
            Line3D(pos + new Vec3(half.x, -half.y, -half.z), pos + new Vec3(half.x, half.y, -half.z), color);
            Line3D(pos + new Vec3(-half.x, -half.y, half.z), pos + new Vec3(-half.x, half.y, half.z), color);
            Line3D(pos + new Vec3(half.x, -half.y, half.z), pos + new Vec3(half.x, half.y, half.z), color);
            
            Line3D(pos + new Vec3(-half.x, -half.y, -half.z), pos + new Vec3(half.x, -half.y, -half.z), color);
            Line3D(pos + new Vec3(-half.x, -half.y, half.z), pos + new Vec3(half.x, -half.y, half.z), color);
            Line3D(pos + new Vec3(-half.x, half.y, -half.z), pos + new Vec3(half.x, half.y, -half.z), color);
            Line3D(pos + new Vec3(-half.x, half.y, half.z), pos + new Vec3(half.x, half.y, half.z), color);
        }

        /// <summary>Draws a cube with the given rotation. Ideal to draw hit boxes.</summary>
        public void OrientatedCube(Vec3 pos, Mat3x3 orientation, Vec3 size, Color? color = null)
        {
            Vec3 half = size / 2;
            Mat3x3 rotT = orientation.Transpose();
            Line3D(pos + rotT.Dot(new Vec3(-half.x, -half.y, -half.z)), pos + rotT.Dot(new Vec3(-half.x, -half.y, half.z)), color);
            Line3D(pos + rotT.Dot(new Vec3(half.x, -half.y, -half.z)), pos + rotT.Dot(new Vec3(half.x, -half.y, half.z)), color);
            Line3D(pos + rotT.Dot(new Vec3(-half.x, half.y, -half.z)), pos + rotT.Dot(new Vec3(-half.x, half.y, half.z)), color);
            Line3D(pos + rotT.Dot(new Vec3(half.x, half.y, -half.z)), pos + rotT.Dot(new Vec3(half.x, half.y, half.z)), color);
            
            Line3D(pos + rotT.Dot(new Vec3(-half.x, -half.y, -half.z)), pos + rotT.Dot(new Vec3(-half.x, half.y, -half.z)), color);
            Line3D(pos + rotT.Dot(new Vec3(half.x, -half.y, -half.z)), pos + rotT.Dot(new Vec3(half.x, half.y, -half.z)), color);
            Line3D(pos + rotT.Dot(new Vec3(-half.x, -half.y, half.z)), pos + rotT.Dot(new Vec3(-half.x, half.y, half.z)), color);
            Line3D(pos + rotT.Dot(new Vec3(half.x, -half.y, half.z)), pos + rotT.Dot(new Vec3(half.x, half.y, half.z)), color);
            
            Line3D(pos + rotT.Dot(new Vec3(-half.x, -half.y, -half.z)), pos + rotT.Dot(new Vec3(half.x, -half.y, -half.z)), color);
            Line3D(pos + rotT.Dot(new Vec3(-half.x, -half.y, half.z)), pos + rotT.Dot(new Vec3(half.x, -half.y, half.z)), color);
            Line3D(pos + rotT.Dot(new Vec3(-half.x, half.y, -half.z)), pos + rotT.Dot(new Vec3(half.x, half.y, -half.z)), color);
            Line3D(pos + rotT.Dot(new Vec3(-half.x, half.y, half.z)), pos + rotT.Dot(new Vec3(half.x, half.y, half.z)), color);
        }

        /// <summary>Draws an octahedron</summary>
        public void Octahedron(Vec3 pos, float size, Color? color = null)
        {
            float half = size / 2;
            Line3D(pos + new Vec3(half, 0, 0), pos + new Vec3(0, half, 0), color);
            Line3D(pos + new Vec3(0, half, 0), pos + new Vec3(-half, 0, 0), color);
            Line3D(pos + new Vec3(-half, 0, 0), pos + new Vec3(0, -half, 0), color);
            Line3D(pos + new Vec3(0, -half, 0), pos + new Vec3(half, 0, 0), color);
            
            Line3D(pos + new Vec3(half, 0, 0), pos + new Vec3(0, 0, half), color);
            Line3D(pos + new Vec3(0, 0, half), pos + new Vec3(-half, 0, 0), color);
            Line3D(pos + new Vec3(-half, 0, 0), pos + new Vec3(0, 0, -half), color);
            Line3D(pos + new Vec3(0, 0, -half), pos + new Vec3(half, 0, 0), color);
            
            Line3D(pos + new Vec3(0, half, 0), pos + new Vec3(0, 0, half), color);
            Line3D(pos + new Vec3(0, 0, half), pos + new Vec3(0, -half, 0), color);
            Line3D(pos + new Vec3(0, -half, 0), pos + new Vec3(0, 0, -half), color);
            Line3D(pos + new Vec3(0, 0, -half), pos + new Vec3(0, half, 0), color);
        }

        /// <summary>Helper function to convert a Vec3 to a Vector3</summary>
        private Vector3 NumVec(Vec3 v)
        {
            return new Vector3(v.x, v.y, v.z);
        }
        
        /// <summary>Helper function to convert a Vec3 to a Vector2</summary>
        private Vector2 NumVec2(Vec3 v)
        {
            return new Vector2(v.x, v.y);
        }
    }
}