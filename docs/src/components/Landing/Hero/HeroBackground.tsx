// Source: https://neat.firecms.co/

import React, { useEffect, useRef } from 'react';
import styles from './Hero.module.css';

class Matrix4 {
  elements: Float32Array;
  constructor() {
    this.elements = new Float32Array([
      1, 0, 0, 0,
      0, 1, 0, 0,
      0, 0, 1, 0,
      0, 0, 0, 1
    ]);
  }
  translate(tx: number, ty: number, tz: number) {
    this.elements[12] += this.elements[0] * tx + this.elements[4] * ty + this.elements[8] * tz;
    this.elements[13] += this.elements[1] * tx + this.elements[5] * ty + this.elements[9] * tz;
    this.elements[14] += this.elements[2] * tx + this.elements[6] * ty + this.elements[10] * tz;
    this.elements[15] += this.elements[3] * tx + this.elements[7] * ty + this.elements[11] * tz;
    return this;
  }
  rotateX(angle: number) {
    const c = Math.cos(angle);
    const s = Math.sin(angle);
    const m12 = this.elements[4], m22 = this.elements[5], m32 = this.elements[6], m42 = this.elements[7];
    const m13 = this.elements[8], m23 = this.elements[9], m33 = this.elements[10], m43 = this.elements[11];
    this.elements[4] = c * m12 + s * m13;
    this.elements[5] = c * m22 + s * m23;
    this.elements[6] = c * m32 + s * m33;
    this.elements[7] = c * m42 + s * m43;
    this.elements[8] = c * m13 - s * m12;
    this.elements[9] = c * m23 - s * m22;
    this.elements[10] = c * m33 - s * m32;
    this.elements[11] = c * m43 - s * m42;
    return this;
  }
  rotateY(angle: number) {
    const c = Math.cos(angle);
    const s = Math.sin(angle);
    const m11 = this.elements[0], m21 = this.elements[1], m31 = this.elements[2], m41 = this.elements[3];
    const m13 = this.elements[8], m23 = this.elements[9], m33 = this.elements[10], m43 = this.elements[11];
    this.elements[0] = c * m11 - s * m13;
    this.elements[1] = c * m21 - s * m23;
    this.elements[2] = c * m31 - s * m33;
    this.elements[3] = c * m41 - s * m43;
    this.elements[8] = s * m11 + c * m13;
    this.elements[9] = s * m21 + c * m23;
    this.elements[10] = s * m31 + c * m33;
    this.elements[11] = s * m41 + c * m43;
    return this;
  }
  rotateZ(angle: number) {
    const c = Math.cos(angle);
    const s = Math.sin(angle);
    const m11 = this.elements[0], m21 = this.elements[1], m31 = this.elements[2], m41 = this.elements[3];
    const m12 = this.elements[4], m22 = this.elements[5], m32 = this.elements[6], m42 = this.elements[7];
    this.elements[0] = c * m11 + s * m12;
    this.elements[1] = c * m21 + s * m22;
    this.elements[2] = c * m31 + s * m32;
    this.elements[3] = c * m41 + s * m42;
    this.elements[4] = -s * m11 + c * m12;
    this.elements[5] = -s * m21 + c * m22;
    this.elements[6] = -s * m31 + c * m32;
    this.elements[7] = -s * m41 + c * m42;
    return this;
  }
}

class OrthographicCamera {
  left: number = 0;
  right: number = 0;
  top: number = 0;
  bottom: number = 0;
  near: number = 0;
  far: number = 0;
  position: [number, number, number] = [0, 0, 0];
  projectionMatrix: Matrix4 = new Matrix4();
  zoom: number = 1.0;

  constructor(left: number, right: number, top: number, bottom: number, near: number, far: number) {
    this.left = left;
    this.right = right;
    this.top = top;
    this.bottom = bottom;
    this.near = near;
    this.far = far;
    this.updateProjectionMatrix();
  }

  updateProjectionMatrix() {
    const w = 1.0 / (this.right - this.left);
    const h = 1.0 / (this.top - this.bottom);
    const p = 1.0 / (this.far - this.near);
    const x = (this.right + this.left) * w;
    const y = (this.top + this.bottom) * h;
    const z = (this.far + this.near) * p;
    this.projectionMatrix.elements = new Float32Array([
      2 * w, 0, 0, 0,
      0, 2 * h, 0, 0,
      0, 0, -2 * p, 0,
      -x, -y, -z, 1
    ]);
  }
}

function updateCamera(camera: OrthographicCamera, width: number, height: number, planeWidth: number, planeHeight: number, zoom: number) {
  camera.zoom = zoom;
  const ratio = width / height;

  const viewPortAreaRatio = 1000000;
  const areaViewPort = width * height;
  const targetPlaneArea = areaViewPort / viewPortAreaRatio * planeWidth * planeHeight / 1.5;

  const targetWidth = Math.sqrt(targetPlaneArea * ratio);
  const targetHeight = targetPlaneArea / targetWidth;

  let left = -planeWidth / 2;
  let right = Math.min((left + targetWidth) / 1.5, planeWidth / 2);
  let top = planeHeight / 4;
  let bottom = Math.max((top - targetHeight) / 2, -planeHeight / 4);

  if (ratio < 1) {
    const horizontalScale = ratio;
    left = left * horizontalScale;
    right = right * horizontalScale;
    const mobileZoomFactor = 1.05;
    left = left * mobileZoomFactor;
    right = right * mobileZoomFactor;
    top = top * mobileZoomFactor;
    bottom = bottom * mobileZoomFactor;
  }

  camera.left = left / zoom;
  camera.right = right / zoom;
  camera.top = top / zoom;
  camera.bottom = bottom / zoom;

  camera.near = -100;
  camera.far = 1000;
  camera.updateProjectionMatrix();
}

function generatePlaneGeometry(width: number, height: number, widthSegments: number, heightSegments: number) {
  const width_half = width / 2;
  const height_half = height / 2;
  const gridX = Math.floor(widthSegments);
  const gridY = Math.floor(heightSegments);
  const gridX1 = gridX + 1;
  const gridY1 = gridY + 1;
  const segment_width = width / gridX;
  const segment_height = height / gridY;

  const indices = [];
  const vertices = [];
  const normals = [];
  const uvs = [];

  for (let iy = 0; iy < gridY1; iy++) {
    const y = iy * segment_height - height_half;
    for (let ix = 0; ix < gridX1; ix++) {
      const x = ix * segment_width - width_half;
      vertices.push(x, -y, 0);
      normals.push(0, 0, 1);
      uvs.push(ix / gridX);
      uvs.push(1 - (iy / gridY));
    }
  }

  for (let iy = 0; iy < gridY; iy++) {
    for (let ix = 0; ix < gridX; ix++) {
      const a = ix + gridX1 * iy;
      const b = ix + gridX1 * (iy + 1);
      const c = (ix + 1) + gridX1 * (iy + 1);
      const d = (ix + 1) + gridX1 * iy;
      indices.push(a, b, d);
      indices.push(b, c, d);
    }
  }

  return {
    position: new Float32Array(vertices),
    normal: new Float32Array(normals),
    uv: new Float32Array(uvs),
    index: new Uint16Array(indices)
  };
}

const VERTEX_SHADER_UNIFORMS = `
precision highp float;

attribute vec3 position;
attribute vec3 normal;
attribute vec2 uv;

uniform mat4 modelViewMatrix;
uniform mat4 projectionMatrix;

varying vec2 vUv;
varying vec2 vFlowUv;
varying vec4 v_new_position;
varying vec3 v_color;
varying float v_displacement_amount;
varying vec3 vViewPosition;
varying vec3 vNormal;
varying vec3 vPosition;

uniform float u_time;
uniform vec2 u_resolution;
uniform vec2 u_color_pressure;
uniform float u_wave_frequency_x;
uniform float u_wave_frequency_y;
uniform float u_wave_amplitude;
uniform float u_plane_width;
uniform float u_plane_height;
uniform float u_color_blending;

uniform int u_colors_count;
struct ColorStop {
    float is_active;
    vec3 color;
    float influence;
};
uniform ColorStop u_colors[6];

uniform float u_y_offset;
uniform float u_y_offset_wave_multiplier;
uniform float u_y_offset_color_multiplier;
uniform float u_y_offset_flow_multiplier;

uniform float u_flow_distortion_a;
uniform float u_flow_distortion_b;
uniform float u_flow_scale;
uniform float u_flow_ease;
uniform float u_flow_enabled;

uniform float u_fresnel_enabled;
uniform float u_fresnel_power;
uniform float u_fresnel_intensity;
uniform vec3 u_fresnel_color;

uniform float u_shape_type;
`;

const FRAGMENT_SHADER_UNIFORMS = `
precision highp float;

varying vec2 vUv;
varying vec2 vFlowUv;
varying vec4 v_new_position;
varying vec3 v_color;
varying float v_displacement_amount;
varying vec3 vViewPosition;
varying vec3 vNormal;
varying vec3 vPosition;

uniform float u_time;
uniform vec2 u_resolution;
uniform float u_plane_height;

uniform float u_shadows;
uniform float u_highlights;
uniform float u_saturation;
uniform float u_brightness;
uniform float u_grain_intensity;
uniform float u_grain_sparsity;
uniform float u_grain_scale;
uniform float u_grain_speed;

uniform float u_y_offset;
uniform float u_y_offset_color_multiplier;

uniform float u_flow_distortion_a;
uniform float u_flow_distortion_b;
uniform float u_flow_scale;

uniform sampler2D u_procedural_texture;
uniform float u_enable_procedural_texture;
uniform float u_texture_ease;

uniform float u_domain_warp_enabled;
uniform float u_domain_warp_intensity;
uniform float u_domain_warp_scale;

uniform float u_vignette_intensity;
uniform float u_vignette_radius;

uniform float u_fresnel_enabled;
uniform float u_fresnel_power;
uniform float u_fresnel_intensity;
uniform vec3 u_fresnel_color;

uniform float u_iridescence_enabled;
uniform float u_iridescence_intensity;
uniform float u_iridescence_speed;

uniform float u_bloom_intensity;
uniform float u_bloom_threshold;

uniform float u_chromatic_aberration;
uniform float u_shape_type;
uniform float u_transparent_texture_void;
uniform float u_silhouette_fade;
uniform float u_cylinder_fade;
uniform float u_ribbon_fade;
`;

const NOISE_FUNCTIONS = `
vec4 permute(vec4 x) {
    return floor(fract(sin(x) * 43758.5453123) * 289.0);
}

vec4 taylorInvSqrt(vec4 r) {
  return 1.79284291400159 - 0.85373472095314 * r;
}

vec3 fade(vec3 t) {
  return t*t*t*(t*(t*6.0-15.0)+10.0);
}

float snoise(vec3 v) {
  const vec2  C = vec2(1.0/6.0, 1.0/3.0) ;
  const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);

  vec3 i  = floor(v + dot(v, C.yyy) );
  vec3 x0 =   v - i + dot(i, C.xxx) ;

  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min( g.xyz, l.zxy );
  vec3 i2 = max( g.xyz, l.zxy );

  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;

  vec4 p = permute( permute( permute(
            i.z + vec4(0.0, i1.z, i2.z, 1.0 ))
          + i.y + vec4(0.0, i1.y, i2.y, 1.0 ))
          + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));

  float n_ = 0.142857142857;
  vec3  ns = n_ * D.wyz - D.xzx;

  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);

  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_ );

  vec4 x = x_ *ns.x + ns.yyyy;
  vec4 y = y_ *ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);

  vec4 b0 = vec4( x.xy, y.xy );
  vec4 b1 = vec4( x.zw, y.zw );

  vec4 s0 = floor(b0)*2.0 + 1.0;
  vec4 s1 = floor(b1)*2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));

  vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy ;
  vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww ;

  vec3 p0 = vec3(a0.xy,h.x);
  vec3 p1 = vec3(a0.zw,h.y);
  vec3 p2 = vec3(a1.xy,h.z);
  vec3 p3 = vec3(a1.zw,h.w);

  vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
  p0 *= norm.x;
  p1 *= norm.y;
  p2 *= norm.z;
  p3 *= norm.w;

  vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
  m = m * m;
  return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1),
                                dot(p2,x2), dot(p3,x3) ) );
}

float cnoise(vec3 P)
{
  vec3 Pi0 = floor(P);
  vec3 Pi1 = Pi0 + vec3(1.0);

  vec3 Pf0 = fract(P);
  vec3 Pf1 = Pf0 - vec3(1.0);
  vec4 ix = vec4(Pi0.x, Pi1.x, Pi0.x, Pi1.x);
  vec4 iy = vec4(Pi0.yy, Pi1.yy);
  vec4 iz0 = Pi0.zzzz;
  vec4 iz1 = Pi1.zzzz;

  vec4 ixy = permute(permute(ix) + iy);
  vec4 ixy0 = permute(ixy + iz0);
  vec4 ixy1 = permute(ixy + iz1);

  vec4 gx0 = ixy0 * (1.0 / 7.0);
  vec4 gy0 = fract(floor(gx0) * (1.0 / 7.0)) - 0.5;
  gx0 = fract(gx0);
  vec4 gz0 = vec4(0.5) - abs(gx0) - abs(gy0);
  vec4 sz0 = step(gz0, vec4(0.0));
  gx0 -= sz0 * (step(0.0, gx0) - 0.5);
  gy0 -= sz0 * (step(0.0, gy0) - 0.5);

  vec4 gx1 = ixy1 * (1.0 / 7.0);
  vec4 gy1 = fract(floor(gx1) * (1.0 / 7.0)) - 0.5;
  gx1 = fract(gx1);
  vec4 gz1 = vec4(0.5) - abs(gx1) - abs(gy1);
  vec4 sz1 = step(gz1, vec4(0.0));
  gx1 -= sz1 * (step(0.0, gx1) - 0.5);
  gy1 -= sz1 * (step(0.0, gy1) - 0.5);

  vec3 g000 = vec3(gx0.x,gy0.x,gz0.x);
  vec3 g100 = vec3(gx0.y,gy0.y,gz0.y);
  vec3 g010 = vec3(gx0.z,gy0.z,gz0.z);
  vec3 g110 = vec3(gx0.w,gy0.w,gz0.w);
  vec3 g001 = vec3(gx1.x,gy1.x,gz1.x);
  vec3 g101 = vec3(gx1.y,gy1.y,gz1.y);
  vec3 g011 = vec3(gx1.z,gy1.z,gz1.z);
  vec3 g111 = vec3(gx1.w,gy1.w,gz1.w);

  vec4 norm0 = taylorInvSqrt(vec4(dot(g000, g000), dot(g010, g010), dot(g100, g100), dot(g110, g110)));
  g000 *= norm0.x;
  g010 *= norm0.y;
  g100 *= norm0.z;
  g110 *= norm0.w;
  vec4 norm1 = taylorInvSqrt(vec4(dot(g001, g001), dot(g011, g011), dot(g101, g101), dot(g111, g111)));
  g001 *= norm1.x;
  g011 *= norm1.y;
  g101 *= norm1.z;
  g111 *= norm1.w;

  float n000 = dot(g000, Pf0);
  float n100 = dot(g100, vec3(Pf1.x, Pf0.yz));
  float n010 = dot(g010, vec3(Pf0.x, Pf1.y, Pf0.z));
  float n110 = dot(g110, vec3(Pf1.xy, Pf0.z));
  float n001 = dot(g001, vec3(Pf0.xy, Pf1.z));
  float n101 = dot(g101, vec3(Pf1.x, Pf0.y, Pf1.z));
  float n011 = dot(g011, vec3(Pf0.x, Pf1.yz));
  float n111 = dot(g111, Pf1);

  vec3 fade_xyz = fade(Pf0);
  vec4 n_z = mix(vec4(n000, n100, n010, n110), vec4(n001, n101, n011, n111), fade_xyz.z);
  vec2 n_yz = mix(n_z.xy, n_z.zw, fade_xyz.y);
  float n_xyz = mix(n_yz.x, n_yz.y, fade_xyz.x);
  return 2.2 * n_xyz;
}
`;

const COLOR_FUNCTIONS = `
vec3 saturation(vec3 rgb, float adjustment) {
    const vec3 W = vec3(0.2125, 0.7154, 0.0721);
    vec3 intensity = vec3(dot(rgb, W));
    return mix(intensity, rgb, adjustment);
}
`;

const VERTEX_SHADER_MAIN = `
void main() {
    vUv = uv;
    vPosition = position;

    float waveOffset = -u_y_offset * u_y_offset_wave_multiplier;
    float colorOffset = -u_y_offset * u_y_offset_color_multiplier;
    float flowOffset = -u_y_offset * u_y_offset_flow_multiplier;

    v_displacement_amount = cnoise( vec3(
        u_wave_frequency_x * position.x + u_time,
        u_wave_frequency_y * (position.y + waveOffset) + u_time,
        u_time
    ));

    vec2 baseUv = vUv;
    baseUv.y += flowOffset / u_plane_height;
    vec2 flowUv = baseUv;

    if (u_flow_enabled > 0.5) {
        if (u_flow_ease > 0.0 || u_flow_distortion_a > 0.0) {
            vec2 ppp = -1.0 + 2.0 * baseUv;
            ppp += 0.1 * cos((1.5 * u_flow_scale) * ppp.yx + 1.1 * u_time + vec2(0.1, 1.1));
            ppp += 0.1 * cos((2.3 * u_flow_scale) * ppp.yx + 1.3 * u_time + vec2(3.2, 3.4));
            ppp += 0.1 * cos((2.2 * u_flow_scale) * ppp.yx + 1.7 * u_time + vec2(1.8, 5.2));
            ppp += u_flow_distortion_a * cos((u_flow_distortion_b * u_flow_scale) * ppp.yx + 1.4 * u_time + vec2(6.3, 3.9));

            float r = length(ppp);
            flowUv = mix(baseUv, vec2(baseUv.x * (1.0 - u_flow_ease) + r * u_flow_ease, baseUv.y), u_flow_ease);
        }
    }

    vFlowUv = flowUv;

    vec3 color = u_colors[0].color;
    vec3 distortedPos = position;
    if (u_shape_type > 0.5) {
        if (u_flow_enabled > 0.5) {
            if (u_flow_ease > 0.0 || u_flow_distortion_a > 0.0) {
                vec3 ppp = position / 25.0;
                ppp.xyz += 0.1 * cos((1.5 * u_flow_scale) * ppp.yxz + 1.1 * u_time + vec3(0.1, 1.1, 2.1));
                ppp.xyz += 0.1 * cos((2.3 * u_flow_scale) * ppp.zxy + 1.3 * u_time + vec3(3.2, 3.4, 1.2));
                ppp.xyz += 0.1 * cos((2.2 * u_flow_scale) * ppp.yxz + 1.7 * u_time + vec3(1.8, 5.2, 3.1));
                ppp.xyz += u_flow_distortion_a * cos((u_flow_distortion_b * u_flow_scale) * ppp.zxy + 1.4 * u_time + vec3(6.3, 3.9, 4.5));

                float r = length(ppp);
                distortedPos = mix(position, vec3(
                    position.x * (1.0 - u_flow_ease) + r * u_flow_ease * 25.0,
                    position.y,
                    position.z * (1.0 - u_flow_ease) + r * u_flow_ease * 25.0
                ), u_flow_ease);
            }
        }
    }

    vec3 noise_cord;
    if (u_shape_type > 0.5) {
        noise_cord = vec3(distortedPos.x / 50.0, (distortedPos.y + colorOffset) / 50.0, distortedPos.z / 50.0);
    } else {
        vec2 adjustedUv = flowUv;
        adjustedUv.y += colorOffset / u_plane_height;
        noise_cord = vec3(adjustedUv, 0.0);
    }

    const float minNoise = .0;
    const float maxNoise = .9;

    for (int i = 1; i < 6; i++) {
        if (i < u_colors_count) {
            if (u_colors[i].is_active > 0.5) {
                float noiseFlow = (1. + float(i)) / 30.;
                float noiseSpeed = (1. + float(i)) * 0.11;
                float noiseSeed = 13. + float(i) * 7.;

                float noise_z = u_time * noiseSpeed;
                if (u_shape_type > 0.5) {
                    noise_z = noise_cord.z * u_color_pressure.x * u_color_pressure.x + u_time * noiseSpeed;
                }

                float noise = snoise(
                    vec3(
                        noise_cord.x * u_color_pressure.x * u_color_pressure.x + u_time * noiseFlow * 2.,
                        noise_cord.y * u_color_pressure.y * u_color_pressure.y,
                        noise_z
                    ) + noiseSeed
                ) - (.1 * float(i)) + (.5 * u_color_blending);

                noise = clamp(noise, minNoise, maxNoise + float(i) * 0.02);
                color = mix(color, u_colors[i].color, smoothstep(0.0, u_color_blending, noise));
            }
        }
    }

    v_color = color;

    vec3 newPosition = position + normal * v_displacement_amount * u_wave_amplitude;
    vec4 mvPosition = modelViewMatrix * vec4(newPosition, 1.0);
    vViewPosition = mvPosition.xyz;
    vNormal = normalize((modelViewMatrix * vec4(normal, 0.0)).xyz);
    gl_Position = projectionMatrix * mvPosition;
    v_new_position = gl_Position;
}
`;

const FRAGMENT_SHADER_MAIN = `
float random(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898,78.233))) * 43758.5453);
}

float fbm(vec3 x) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;
    for (int i = 0; i < 4; i++) {
        value += amplitude * snoise(x * frequency);
        frequency *= 2.0;
        amplitude *= 0.5;
    }
    return value;
}

vec3 hsl2rgb(float h, float s, float l) {
    vec3 rgb = clamp(abs(mod(h * 6.0 + vec3(0.0, 4.0, 2.0), 6.0) - 3.0) - 1.0, 0.0, 1.0);
    return l + s * (rgb - 0.5) * (1.0 - abs(2.0 * l - 1.0));
}

void main() {
    vec2 finalUv = vFlowUv;
    vec3 baseColor = v_color;
    vec3 color = baseColor;

    if (u_domain_warp_enabled > 0.5) {
        vec3 p = vec3(finalUv * u_domain_warp_scale, u_time * 0.15);
        vec2 q = vec2(fbm(p), fbm(p + vec3(5.2, 1.3, 0.0)));
        float f = fbm(p + vec3(4.0 * q, 0.0));
        vec3 warpColor = color * (1.0 + f * 0.8 * u_domain_warp_intensity);
        float pattern = clamp(f * f * f + 0.6 * f * f + 0.5 * f, 0.0, 1.0);
        color = mix(color, warpColor * (0.6 + pattern * 0.8), u_domain_warp_intensity * 0.7);
    }

    vec3 normal = normalize(vNormal);
    vec3 viewDir = vec3(0.0, 0.0, 1.0);
    float ndotv = dot(normal, viewDir);

    if (ndotv < 0.0) {
        normal = -normal;
        ndotv = -ndotv;
    }

    vec3 lightDir = normalize(vec3(1.0, 1.0, 1.0));
    float diffuse = max(dot(normal, lightDir), 0.0);
    vec3 halfDir = normalize(lightDir + viewDir);
    float specular = pow(max(dot(normal, halfDir), 0.0), 32.0);

    color += v_displacement_amount * u_highlights;
    float heightShadow = 1.0 - v_displacement_amount;
    color -= heightShadow * heightShadow * u_shadows;

    color = saturation(color, 1.0 + u_saturation);
    color = color * u_brightness;

    if (u_iridescence_enabled > 0.5) {
        float hue = fract(v_displacement_amount * 0.5 + 0.5 + u_time * u_iridescence_speed * 0.05);
        vec3 iriColor = hsl2rgb(hue, 0.8, 0.6);
        color = mix(color, iriColor, u_iridescence_intensity * abs(v_displacement_amount) * 0.6);
    }

    if (u_fresnel_enabled > 0.5) {
        float slope = 1.0 - abs(v_displacement_amount);
        float fresnel = pow(max(slope, 0.0), u_fresnel_power);
        color += u_fresnel_color * fresnel * u_fresnel_intensity;
    }

    if (u_vignette_intensity > 0.0) {
        float dist = length(vUv - vec2(0.5));
        float vig = smoothstep(u_vignette_radius, u_vignette_radius * 0.3, dist);
        color *= mix(1.0, vig, u_vignette_intensity);
    }

    if (u_bloom_intensity > 0.0) {
        float luma = dot(color, vec3(0.2126, 0.7152, 0.0722));
        float bloomMask = smoothstep(u_bloom_threshold, 1.0, luma);
        color += color * bloomMask * u_bloom_intensity;
    }

    if (u_chromatic_aberration > 0.0) {
        float caAmount = u_chromatic_aberration * 0.008;
        float dist = length(vUv - vec2(0.5));
        float rShift = v_displacement_amount + caAmount * dist;
        float bShift = v_displacement_amount - caAmount * dist;
        color.r *= 1.0 + rShift * caAmount * 10.0;
        color.b *= 1.0 - bShift * caAmount * 10.0;
    }

    float grain = 0.0;
    if (u_grain_intensity > 0.0) {
        vec2 noiseCoords = gl_FragCoord.xy / u_grain_scale;
        grain = fbm(vec3(noiseCoords, u_time * u_grain_speed));
        grain = grain * 0.5 + 0.5;
        grain -= 0.5;
        grain = (grain > u_grain_sparsity) ? grain : 0.0;
        grain *= u_grain_intensity;
        color += vec3(grain);
    }

    gl_FragColor = vec4(color, 1.0);
}
`;

function getElapsedSecondsInLastHour() {
  const now = new Date();
  const minutes = now.getMinutes();
  const seconds = now.getSeconds();
  return (minutes * 60) + seconds;
}

function hexToRgb(hex: string): [number, number, number] {
  const bigint = parseInt(hex.replace('#', ''), 16);
  return [
    ((bigint >> 16) & 255) / 255.0,
    ((bigint >> 8) & 255) / 255.0,
    (bigint & 255) / 255.0
  ];
}

export default function HeroBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const scrollYRef = useRef<number>(0);

  useEffect(() => {
    const handleScroll = () => {
      scrollYRef.current = window.scrollY;
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const gl = canvas.getContext('webgl2', { alpha: true, preserveDrawingBuffer: true, antialias: true }) ||
      canvas.getContext('webgl', { alpha: true, preserveDrawingBuffer: true, antialias: true }) as WebGLRenderingContext | WebGL2RenderingContext | null;

    if (!gl) {
      console.error('WebGL not supported by browser.');
      return;
    }

    const vertCombined = VERTEX_SHADER_UNIFORMS + '\n' + NOISE_FUNCTIONS + '\n' + COLOR_FUNCTIONS + '\n' + VERTEX_SHADER_MAIN;
    const fragCombined = FRAGMENT_SHADER_UNIFORMS + '\n' + COLOR_FUNCTIONS + '\n' + NOISE_FUNCTIONS + '\n' + FRAGMENT_SHADER_MAIN;

    const compileShader = (source: string, type: number): WebGLShader | null => {
      const shader = gl.createShader(type);
      if (!shader) return null;
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        console.error('Shader compile error:', gl.getShaderInfoLog(shader));
        gl.deleteShader(shader);
        return null;
      }
      return shader;
    };

    const vertShader = compileShader(vertCombined, gl.VERTEX_SHADER);
    const fragShader = compileShader(fragCombined, gl.FRAGMENT_SHADER);
    if (!vertShader || !fragShader) return;

    const program = gl.createProgram();
    if (!program) return;
    gl.attachShader(program, vertShader);
    gl.attachShader(program, fragShader);
    gl.linkProgram(program);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error('Program link error:', gl.getProgramInfoLog(program));
      return;
    }

    gl.useProgram(program);

    const planeWidth = 50;
    const planeHeight = 80;
    const resolution = 0.75;
    const geom = generatePlaneGeometry(planeWidth, planeHeight, 240 * resolution, 240 * resolution);

    const positionBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, geom.position, gl.STATIC_DRAW);

    const normalBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, normalBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, geom.normal, gl.STATIC_DRAW);

    const uvBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, uvBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, geom.uv, gl.STATIC_DRAW);

    const indexBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, geom.index, gl.STATIC_DRAW);

    const aPosition = gl.getAttribLocation(program, 'position');
    const aNormal = gl.getAttribLocation(program, 'normal');
    const aUv = gl.getAttribLocation(program, 'uv');

    gl.enableVertexAttribArray(aPosition);
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.vertexAttribPointer(aPosition, 3, gl.FLOAT, false, 0, 0);

    gl.enableVertexAttribArray(aNormal);
    gl.bindBuffer(gl.ARRAY_BUFFER, normalBuffer);
    gl.vertexAttribPointer(aNormal, 3, gl.FLOAT, false, 0, 0);

    gl.enableVertexAttribArray(aUv);
    gl.bindBuffer(gl.ARRAY_BUFFER, uvBuffer);
    gl.vertexAttribPointer(aUv, 2, gl.FLOAT, false, 0, 0);

    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);

    const uniforms: Record<string, WebGLUniformLocation | null> = {};
    const uniformNames = [
      'projectionMatrix', 'modelViewMatrix',
      'u_time', 'u_resolution', 'u_color_pressure', 'u_wave_frequency_x', 'u_wave_frequency_y',
      'u_wave_amplitude', 'u_colors_count', 'u_plane_width', 'u_plane_height', 'u_shadows',
      'u_highlights', 'u_grain_intensity', 'u_grain_sparsity', 'u_grain_scale', 'u_grain_speed',
      'u_flow_distortion_a', 'u_flow_distortion_b', 'u_flow_scale', 'u_flow_ease', 'u_flow_enabled',
      'u_y_offset', 'u_y_offset_wave_multiplier', 'u_y_offset_color_multiplier', 'u_y_offset_flow_multiplier',
      'u_enable_procedural_texture', 'u_texture_ease', 'u_transparent_texture_void', 'u_saturation', 'u_brightness', 'u_color_blending',
      'u_domain_warp_enabled', 'u_domain_warp_intensity', 'u_domain_warp_scale',
      'u_vignette_intensity', 'u_vignette_radius',
      'u_fresnel_enabled', 'u_fresnel_power', 'u_fresnel_intensity', 'u_fresnel_color',
      'u_iridescence_enabled', 'u_iridescence_intensity', 'u_iridescence_speed',
      'u_bloom_intensity', 'u_bloom_threshold', 'u_chromatic_aberration',
      'u_shape_type', 'u_silhouette_fade', 'u_cylinder_fade', 'u_ribbon_fade'
    ];

    uniformNames.forEach(name => {
      uniforms[name] = gl.getUniformLocation(program, name);
    });

    for (let i = 0; i < 6; i++) {
      uniforms[`u_colors[${i}].is_active`] = gl.getUniformLocation(program, `u_colors[${i}].is_active`);
      uniforms[`u_colors[${i}].color`] = gl.getUniformLocation(program, `u_colors[${i}].color`);
      uniforms[`u_colors[${i}].influence`] = gl.getUniformLocation(program, `u_colors[${i}].influence`);
    }

    gl.uniform1f(uniforms['u_plane_width'], planeWidth);
    gl.uniform1f(uniforms['u_plane_height'], planeHeight);
    gl.uniform2f(uniforms['u_color_pressure'], 1.0, 1.0);
    gl.uniform1f(uniforms['u_wave_frequency_x'], 0.0);
    gl.uniform1f(uniforms['u_wave_frequency_y'], 0.0);
    gl.uniform1f(uniforms['u_wave_amplitude'], 7.5);
    gl.uniform1f(uniforms['u_color_blending'], 0.7);
    gl.uniform1f(uniforms['u_shadows'], 0.02);
    gl.uniform1f(uniforms['u_highlights'], 0.02);
    gl.uniform1f(uniforms['u_saturation'], -0.1);
    gl.uniform1f(uniforms['u_brightness'], 1.0);

    gl.uniform1f(uniforms['u_grain_intensity'], 0.0);
    gl.uniform1f(uniforms['u_grain_sparsity'], 0.0);
    gl.uniform1f(uniforms['u_grain_scale'], 2.0);
    gl.uniform1f(uniforms['u_grain_speed'], 1.0);

    gl.uniform1f(uniforms['u_flow_distortion_a'], 0.4);
    gl.uniform1f(uniforms['u_flow_distortion_b'], 3.0);
    gl.uniform1f(uniforms['u_flow_scale'], 3.3);
    gl.uniform1f(uniforms['u_flow_ease'], 0.53);
    gl.uniform1f(uniforms['u_flow_enabled'], 0.0);

    gl.uniform1f(uniforms['u_enable_procedural_texture'], 0.0);
    gl.uniform1f(uniforms['u_texture_ease'], 0.68);
    gl.uniform1f(uniforms['u_transparent_texture_void'], 0.0);

    gl.uniform1f(uniforms['u_domain_warp_enabled'], 0.0);
    gl.uniform1f(uniforms['u_domain_warp_intensity'], 0.0);
    gl.uniform1f(uniforms['u_domain_warp_scale'], 3.0);

    gl.uniform1f(uniforms['u_vignette_intensity'], 0.0);
    gl.uniform1f(uniforms['u_vignette_radius'], 0.8);

    gl.uniform1f(uniforms['u_fresnel_enabled'], 0.0);
    gl.uniform1f(uniforms['u_fresnel_power'], 2.0);
    gl.uniform1f(uniforms['u_fresnel_intensity'], 0.5);
    gl.uniform3fv(uniforms['u_fresnel_color'], [1.0, 1.0, 1.0]);

    gl.uniform1f(uniforms['u_iridescence_enabled'], 0.0);
    gl.uniform1f(uniforms['u_iridescence_intensity'], 0.5);
    gl.uniform1f(uniforms['u_iridescence_speed'], 1.0);

    gl.uniform1f(uniforms['u_bloom_intensity'], 0.0);
    gl.uniform1f(uniforms['u_bloom_threshold'], 0.7);
    gl.uniform1f(uniforms['u_chromatic_aberration'], 0.0);

    gl.uniform1f(uniforms['u_shape_type'], 0.0);
    gl.uniform1f(uniforms['u_silhouette_fade'], 0.25);
    gl.uniform1f(uniforms['u_cylinder_fade'], 0.08);
    gl.uniform1f(uniforms['u_ribbon_fade'], 0.05);

    const colorConfigs = [
      { color: '#FF0058', enabled: true, influence: 0 },
      { color: '#FF80A9', enabled: true, influence: 0 },
      { color: '#050505', enabled: true, influence: 0 },
      { color: '#050505', enabled: true, influence: 0 },
      { color: '#050505', enabled: true, influence: 0 }
    ];

    for (let i = 0; i < 6; i++) {
      if (i < colorConfigs.length) {
        const c = colorConfigs[i];
        gl.uniform1f(uniforms[`u_colors[${i}].is_active`], c.enabled ? 1.0 : 0.0);
        gl.uniform3fv(uniforms[`u_colors[${i}].color`], hexToRgb(c.color));
        gl.uniform1f(uniforms[`u_colors[${i}].influence`], c.influence);
      } else {
        gl.uniform1f(uniforms[`u_colors[${i}].is_active`], 0.0);
      }
    }
    gl.uniform1i(uniforms['u_colors_count'], 6);

    gl.uniform1f(uniforms['u_y_offset_wave_multiplier'], 0.0022);
    gl.uniform1f(uniforms['u_y_offset_color_multiplier'], 0.0006);
    gl.uniform1f(uniforms['u_y_offset_flow_multiplier'], 0.0028);

    const camera = new OrthographicCamera(0, 0, 0, 0, 0, 1000);
    camera.position = [0, 0, 5];

    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.enable(gl.DEPTH_TEST);

    let tick = getElapsedSecondsInLastHour();
    let lastTime = performance.now();
    let requestRef = -1;

    const render = () => {
      const timeNow = performance.now();
      tick += ((timeNow - lastTime) / 1000) * 0.35;
      lastTime = timeNow;

      gl.useProgram(program);
      gl.uniform1f(uniforms['u_time'], tick);
      gl.uniform1f(uniforms['u_y_offset'], scrollYRef.current);

      const modelViewMatrix = new Matrix4();
      modelViewMatrix.translate(
        -camera.position[0],
        -camera.position[1],
        -camera.position[2]
      );
      modelViewMatrix.translate(0, 0, -1);

      modelViewMatrix.rotateX(-Math.PI / 3.5);

      gl.uniformMatrix4fv(uniforms['modelViewMatrix'], false, modelViewMatrix.elements);

      gl.clearColor(0.00392, 0.00392, 0.00392, 1.0);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.drawElements(gl.TRIANGLES, geom.index.length, gl.UNSIGNED_SHORT, 0);

      requestRef = requestAnimationFrame(render);
    };

    const setSize = () => {
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;

      canvas.width = width;
      canvas.height = height;

      gl.viewport(0, 0, width, height);

      updateCamera(camera, width, height, planeWidth, planeHeight, 1.0);

      gl.uniformMatrix4fv(uniforms['projectionMatrix'], false, camera.projectionMatrix.elements);
      gl.uniform2f(uniforms['u_resolution'], width, height);
    };

    setSize();
    render();

    const resizeObserver = new ResizeObserver(() => {
      setSize();
    });
    resizeObserver.observe(canvas);

    return () => {
      cancelAnimationFrame(requestRef);
      resizeObserver.disconnect();
      gl.deleteProgram(program);
      gl.deleteShader(vertShader);
      gl.deleteShader(fragShader);
      gl.deleteBuffer(positionBuffer);
      gl.deleteBuffer(normalBuffer);
      gl.deleteBuffer(uvBuffer);
      gl.deleteBuffer(indexBuffer);
    };
  }, []);

  return <canvas ref={canvasRef} id="gradient" className={styles.heroGradientCanvas} />;
}
