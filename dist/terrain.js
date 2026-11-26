const terrainTileSize = 604;
const terrainTileCount = 112;
const terrainLayers = 16;
const terrainGrid = atlasUS ? {west:-188,north:72,rate:30,cols:3720,rows:1650} :
  atlasUK ? {west:-9,north:62,rate:120,cols:1440,rows:1560} :
  {west:60,north:60,rate:30,cols:2700,rows:1800};
const mapPaper = '#e3dbc4';
const elevationColors = [
  [244,236,213],[230,210,171],[208,175,127],[181,137,93],[148,99,67],[100,62,48]
];
const elevationBands = (atlasUK ? [100,250,500,750,1000,Infinity] : [200,500,1000,2000,4000,Infinity]).map(
  (below,i) => ({below,color:elevationColors[i]})
);
const elevationWater = [155,183,187];
const cssColor = rgb => `rgb(${rgb.join(',')})`;

const elevationShader = `
precision highp int;
precision highp isampler2D;
precision highp isampler2DArray;
uniform isampler2D uOverview;
uniform isampler2DArray uDetail;
uniform int uTileLayers[112];
vec3 unpackHeight(int n) {
  if (n <= -16000) return vec3(float(n + 16000),1,0);
  if (n >= 14000) return vec3(float(n - 16000),0,1);
  return vec3(float(n),0,0);
}
vec3 blendGrid(vec2 f,vec3 a,vec3 b,vec3 c,vec3 d) {
  return mix(mix(a,b,f.x),mix(c,d,f.x),f.y);
}
vec3 elevation(vec2 p) {
  ivec2 tile = ivec2(floor((p-vec2(70,15))/5.0));
  if (all(greaterThanEqual(tile,ivec2(0))) && all(lessThan(tile,ivec2(14,8)))) {
    int layer = uTileLayers[tile.y*14+tile.x];
    if (layer >= 0) {
      vec2 q = (vec2(p.x,-p.y)-vec2(70+tile.x*5,-20-tile.y*5))*120.0+1.5;
      ivec3 i = ivec3(floor(q),layer);
      return blendGrid(fract(q),unpackHeight(texelFetch(uDetail,i,0).r),
        unpackHeight(texelFetch(uDetail,i+ivec3(1,0,0),0).r),
        unpackHeight(texelFetch(uDetail,i+ivec3(0,1,0),0).r),
        unpackHeight(texelFetch(uDetail,i+ivec3(1,1,0),0).r));
    }
  }
  vec2 q = clamp((vec2(p.x,-p.y)-vec2(${terrainGrid.west},${-terrainGrid.north}))*${terrainGrid.rate}.0-0.5,
    vec2(0),vec2(${terrainGrid.cols-2}.999,${terrainGrid.rows-2}.999));
  ivec2 i = ivec2(floor(q));
  return blendGrid(fract(q),unpackHeight(texelFetch(uOverview,i,0).r),
    unpackHeight(texelFetch(uOverview,i+ivec2(1,0),0).r),
    unpackHeight(texelFetch(uOverview,i+ivec2(0,1),0).r),
    unpackHeight(texelFetch(uOverview,i+ivec2(1,1),0).r));
}`;

const reliefShader = `
uniform bool uRelief;
uniform bool uElevationColors;
vec3 elevationColor(float height) {
${elevationBands.map(({below,color}) =>
  `  ${Number.isFinite(below) ? `if (height < ${below}.0) ` : ''}return vec3(${color.join(',')})/255.0;`).join('\n')}
}
vec3 surface(vec2 geo) {
  vec3 sampleValue = elevation(geo);
  if (uElevationColors) {
    float water = smoothstep(.10,.90,max(sampleValue.y,sampleValue.z));
    return mix(elevationColor(sampleValue.x),vec3(${elevationWater.join(',')})/255.0,water);
  }
  float h = max(0.0,sampleValue.x);
  vec3 water = mix(vec3(.65,.75,.74),vec3(.43,.58,.61),smoothstep(0.0,6000.0,-sampleValue.x));
  vec3 land = vec3(.88,.84,.71);
  if (uRelief) {
    land = mix(land,vec3(.81,.75,.61),smoothstep(500.0,4600.0,h));
    land = mix(land,vec3(.94,.90,.80),smoothstep(4300.0,6700.0,h));
  }
  vec2 stepSize = clamp(max(abs(dFdx(geo)),abs(dFdy(geo))),vec2(.013),vec2(.07));
  if (uRelief && max(sampleValue.y,sampleValue.z) < .94) {
    vec2 dx = vec2(stepSize.x,0), dy = vec2(0,stepSize.y);
    float east = (max(0.0,elevation(geo+dx).x)-max(0.0,elevation(geo-dx).x))
      /(222400.0*stepSize.x*max(.45,cos(radians(geo.y))));
    float north = (max(0.0,elevation(geo+dy).x)-max(0.0,elevation(geo-dy).x))/(222400.0*stepSize.y);
    vec3 normal = normalize(vec3(-east*3.6,-north*3.6,1));
    float light = dot(normal,normalize(vec3(-.55,.52,.65)));
    land *= .87+.20*light;
  }
  land = mix(land,vec3(.48,.66,.69),smoothstep(.10,.90,sampleValue.z));
  return mix(land,water,smoothstep(.10,.90,sampleValue.y));
}`;

const mapTerrainVertex = `#version 300 es
out vec2 vUV;
void main() {
  vec2 p = vec2(gl_VertexID == 1 ? 2 : 0,gl_VertexID == 2 ? 2 : 0);
  vUV = p;
  gl_Position = vec4(p*2.0-1.0,0,1);
}`;

const mapTerrainFragment = `#version 300 es
precision highp float;
in vec2 vUV;
uniform vec4 uExtent;
out vec4 color;
${elevationShader}
${reliefShader}
void main() {
  vec2 geo = mix(uExtent.xy,uExtent.zw,vUV);
  color = vec4(surface(geo),1);
}`;

class AtlasTerrain {
  constructor(canvas,onChange) {
    this.canvas = canvas;
    this.onChange = onChange;
    this.tileMap = new Int32Array(terrainTileCount).fill(-1);
    this.overviewOnly = this.tileMap.slice();
    this.detailRevision = 0;
    this.tiles = new Map();
    this.tileElevation = new Map();
    this.pending = new Set();
    this.failed = new Set();
    this.wanted = [];
    try {
      this.gl = canvas.getContext('webgl2',{antialias:false,alpha:false});
      if (this.gl) this.initializeGPU();
    } catch (error) {
      this.gl = null;
      this.canvas = canvas.cloneNode();
      canvas.replaceWith(this.canvas);
      console.error(error);
    }
    if (!this.gl) this.flatContext = this.canvas.getContext('2d');
    this.load();
  }

  async loadGrid(name,cols,rows) {
    const response = await fetch(atlasData(`terrain/${name}.hgt.gz?v=1`));
    if (!response.ok) throw new Error(`高程数据 ${name} (${response.status})`);
    let buffer = await response.arrayBuffer();
    if (buffer.byteLength !== cols*rows*2) {
      const stream = new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'));
      buffer = await new Response(stream).arrayBuffer();
    }
    if (buffer.byteLength !== cols*rows*2) throw new Error(`高程数据尺寸错误 (${name})`);
    const bytes = new DataView(buffer);
    const heights = new Int16Array(cols*rows);
    for (let i=0; i<heights.length; i++) {
      heights[i] = bytes.getInt16(2*i,true)+(i%cols ? heights[i-1] : 0);
    }
    return heights;
  }

  async load() {
    try {
      const {cols,rows} = terrainGrid;
      this.overview = await this.loadGrid('overview',cols,rows);
      if (this.gl) {
        const gl = this.gl;
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D,this.overviewTexture);
        gl.texImage2D(gl.TEXTURE_2D,0,gl.R16I,cols,rows,0,gl.RED_INTEGER,gl.SHORT,this.overview);
      }
    } catch (error) {
      this.error = error;
      console.error(error);
    }
    this.onChange();
  }

  compile(vertex,fragment) {
    const gl = this.gl;
    const program = gl.createProgram();
    for (const [type,source] of [[gl.VERTEX_SHADER,vertex],[gl.FRAGMENT_SHADER,fragment]]) {
      const shader = gl.createShader(type);
      gl.shaderSource(shader,source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
      gl.attachShader(program,shader);
      gl.deleteShader(shader);
    }
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);
    gl.uniform1i(gl.getUniformLocation(program,'uOverview'),0);
    gl.uniform1i(gl.getUniformLocation(program,'uDetail'),1);
    const locations = Object.fromEntries(['uTileLayers[0]','uExtent','uRelief','uElevationColors'].map(name =>
      [name,gl.getUniformLocation(program,name)]));
    return {program,locations};
  }

  initializeGPU() {
    const gl = this.gl;
    this.map = this.compile(mapTerrainVertex,mapTerrainFragment);
    const texture = (target,unit) => {
      const handle = gl.createTexture();
      gl.activeTexture(unit);
      gl.bindTexture(target,handle);
      gl.texParameteri(target,gl.TEXTURE_MIN_FILTER,gl.NEAREST);
      gl.texParameteri(target,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
      gl.texParameteri(target,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);
      gl.texParameteri(target,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
      return handle;
    };
    this.overviewTexture = texture(gl.TEXTURE_2D,gl.TEXTURE0);
    this.detailTexture = texture(gl.TEXTURE_2D_ARRAY,gl.TEXTURE1);
    gl.texStorage3D(gl.TEXTURE_2D_ARRAY,1,gl.R16I,terrainTileSize,terrainTileSize,terrainLayers);
  }

  scheduleTiles(bounds) {
    this.wanted = [];
    if (!atlasCN) return;
    const [west,south,east,north] = bounds;
    if (east-west > 25 || north-south > 20) return;
    const lon = (west+east)/2, lat = (south+north)/2;
    for (let row=0; row<8; row++) {
      for (let column=0; column<14; column++) {
        const x = 70+column*5, y = 15+row*5;
        if (x > east || x+5 < west || y > north || y+5 < south) continue;
        this.wanted.push({id:row*14+column,x,y,distance:Math.hypot(x+2.5-lon,y+2.5-lat)});
      }
    }
    this.wanted.sort((a,b) => a.distance-b.distance);
    this.wanted.length = Math.min(this.wanted.length,terrainLayers);
    for (const tile of this.wanted) {
      if (this.pending.size >= 5) break;
      if (this.tiles.has(tile.id) || this.pending.has(tile.id) || this.failed.has(tile.id)) continue;
      this.loadTile(tile);
    }
  }

  async loadTile(tile) {
    this.pending.add(tile.id);
    try {
      const pixels = await this.loadGrid(`${tile.x}-${tile.y}`,terrainTileSize,terrainTileSize);
      if (!this.wanted.some(entry => entry.id === tile.id)) return;
      const used = new Set(this.tiles.values());
      let layer = 0;
      while (used.has(layer)) layer++;
      if (layer === terrainLayers) {
        const [drop,slot] = [...this.tiles].find(([id]) => !this.wanted.some(entry => entry.id === id));
        this.tiles.delete(drop);
        this.tileElevation.delete(drop);
        this.tileMap[drop] = -1;
        layer = slot;
      }
      if (this.gl) {
        const gl = this.gl;
        gl.activeTexture(gl.TEXTURE1);
        gl.bindTexture(gl.TEXTURE_2D_ARRAY,this.detailTexture);
        gl.texSubImage3D(gl.TEXTURE_2D_ARRAY,0,0,0,layer,terrainTileSize,terrainTileSize,1,gl.RED_INTEGER,gl.SHORT,pixels);
      } else {
        this.tileElevation.set(tile.id,pixels);
      }
      this.tiles.set(tile.id,layer);
      this.tileMap[tile.id] = layer;
      this.detailRevision++;
    } catch (error) {
      this.failed.add(tile.id);
      console.warn(error);
    } finally {
      this.pending.delete(tile.id);
      this.onChange();
    }
  }

  render(bounds,relief,useElevationColors) {
    if (!this.overview || (!this.gl && !this.flatContext)) return false;
    const {width,height} = this.canvas;
    this.scheduleTiles(bounds);
    const useDetail = this.wanted.length > 0;
    const frame = [width,height,relief,useElevationColors,...bounds,useDetail ? this.detailRevision : -1].join(':');
    if (this.lastFrame === frame) return true;
    this.lastFrame = frame;
    if (this.gl) {
      const gl = this.gl;
      const {program,locations:u} = this.map;
      gl.viewport(0,0,width,height);
      gl.useProgram(program);
      gl.uniform1iv(u['uTileLayers[0]'],useDetail ? this.tileMap : this.overviewOnly);
      gl.uniform4fv(u.uExtent,bounds);
      gl.uniform1i(u.uRelief,relief ? 1 : 0);
      gl.uniform1i(u.uElevationColors,useElevationColors ? 1 : 0);
      gl.drawArrays(gl.TRIANGLES,0,3);
    } else this.renderFlat(bounds,relief,useElevationColors,useDetail);
    return true;
  }

  renderFlat(bounds,relief,useElevationColors,useDetail) {
    const {width,height} = this.canvas;
    this.flatBuffer ??= document.createElement('canvas');
    const scratch = this.flatBuffer;
    const resolution = Math.min(1,620/width,420/height);
    const cols = Math.max(1,Math.round(width*resolution));
    const rows = Math.max(1,Math.round(height*resolution));
    scratch.width = cols;
    scratch.height = rows;
    const buffer = scratch.getContext('2d');
    const image = buffer.createImageData(cols,rows);
    const [west,south,east,north] = bounds;
    const clear = value => (value <= -16000 ? value+16000 : value >= 14000 ? value-16000 : value);
    const bandPixels = elevationBands.map(({color}) => [...color,255]);
    const waterPixel = useElevationColors ? [...elevationWater,255] : [158,187,190,255];
    const columns = Array.from({length:cols},(_,x) => {
      const lon = west+(x+.5)*(east-west)/cols;
      const tileCol = Math.floor((lon-70)/5);
      return {
        overview:Math.max(1,Math.min(terrainGrid.cols-2,Math.floor((lon-terrainGrid.west)*terrainGrid.rate))),
        tileCol,
        detail:Math.floor((lon-70-tileCol*5)*120)+2
      };
    });
    for (let y=0,p=0; y<rows; y++) {
      const lat = north-(y+.5)*(north-south)/rows;
      const row = Math.max(1,Math.min(terrainGrid.rows-2,Math.floor((terrainGrid.north-lat)*terrainGrid.rate)));
      const tileRow = Math.floor((lat-15)/5);
      const detailRow = Math.floor((20+tileRow*5-lat)*120)+2;
      for (let x=0; x<cols; x++,p+=4) {
        const column = columns[x];
        const tile = useDetail && tileRow >= 0 && tileRow < 8 && column.tileCol >= 0 && column.tileCol < 14 &&
          this.tileElevation.get(tileRow*14+column.tileCol);
        const samples = tile || this.overview;
        const stride = tile ? terrainTileSize : terrainGrid.cols;
        const i = tile ? detailRow*stride+column.detail : row*stride+column.overview;
        const sample = samples[i];
        if (sample <= -16000 || sample >= 14000) {
          image.data.set(waterPixel,p);
          continue;
        }
        if (useElevationColors) {
          const band = elevationBands.findIndex(({below}) => sample < below);
          image.data.set(bandPixels[band],p);
          continue;
        }
        const slope = clear(samples[i-1])-clear(samples[i+1])+clear(samples[i-stride])-clear(samples[i+stride]);
        const tone = relief ? Math.min(28,Math.max(-28,slope*.018-sample*.002)) : 0;
        image.data.set([222+tone,211+tone,180+tone,255],p);
      }
    }
    buffer.putImageData(image,0,0);
    this.flatContext.drawImage(scratch,0,0,width,height);
  }

}
