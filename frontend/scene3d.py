"""Three.js hero scene (rotating wireframe core, orbit rings, floating document cards, particles)."""

HERO_3D = r"""
<!doctype html><html><head><meta charset="utf-8">
<style>html,body{margin:0;height:100%;background:transparent;overflow:hidden}#c{width:100%;height:100%}</style></head>
<body><div id="c"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
try{
const el=document.getElementById('c');
const W=()=>el.clientWidth, H=()=>el.clientHeight;
const scene=new THREE.Scene();
const camera=new THREE.PerspectiveCamera(48,W()/H(),0.1,100); camera.position.z=7.2;
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});
renderer.setPixelRatio(Math.min(window.devicePixelRatio,2)); renderer.setSize(W(),H()); el.appendChild(renderer.domElement);

const group=new THREE.Group(); scene.add(group);
const mk=(geo,color,op)=>new THREE.Mesh(geo,new THREE.MeshBasicMaterial({color,wireframe:true,transparent:true,opacity:op}));
const core=mk(new THREE.IcosahedronGeometry(1.5,1),0x7c5cff,.95);
const inner=mk(new THREE.IcosahedronGeometry(0.95,0),0x22d3ee,.85);
const glow=new THREE.Mesh(new THREE.SphereGeometry(0.55,24,24),new THREE.MeshBasicMaterial({color:0xf472b6,transparent:true,opacity:.55}));
group.add(core,inner,glow);

const ringMat=c=>new THREE.MeshBasicMaterial({color:c,transparent:true,opacity:.8});
const r1=new THREE.Mesh(new THREE.TorusGeometry(2.5,0.014,8,200),ringMat(0xf472b6)); r1.rotation.x=1.2;
const r2=new THREE.Mesh(new THREE.TorusGeometry(3.0,0.014,8,200),ringMat(0x22d3ee)); r2.rotation.y=1.1; r2.rotation.x=.4;
group.add(r1,r2);

const cardColors=[0x7c5cff,0x22d3ee,0xf472b6,0x34d399,0xfbbf24];
const cards=[];
for(let i=0;i<5;i++){
  const m=new THREE.Mesh(new THREE.BoxGeometry(0.85,1.15,0.04),new THREE.MeshBasicMaterial({color:cardColors[i],transparent:true,opacity:.35}));
  const edge=new THREE.LineSegments(new THREE.EdgesGeometry(m.geometry),new THREE.LineBasicMaterial({color:cardColors[i]}));
  m.add(edge); m.userData={a:i/5*Math.PI*2,r:3.4+(i%2)*.5,s:.25+i*.04,y:(i-2)*.45};
  cards.push(m); group.add(m);
}
const N=500,pos=new Float32Array(N*3);
for(let i=0;i<N;i++){const r=4+Math.random()*3.5,t=Math.random()*6.283,p=Math.acos(2*Math.random()-1);
  pos[i*3]=r*Math.sin(p)*Math.cos(t);pos[i*3+1]=r*Math.sin(p)*Math.sin(t);pos[i*3+2]=r*Math.cos(p);}
const pg=new THREE.BufferGeometry(); pg.setAttribute('position',new THREE.BufferAttribute(pos,3));
const pts=new THREE.Points(pg,new THREE.PointsMaterial({color:0xa78bfa,size:.035,transparent:true,opacity:.8}));
scene.add(pts);

let mx=0,my=0; window.addEventListener('pointermove',e=>{mx=(e.clientX/W()-.5);my=(e.clientY/H()-.5);});
window.addEventListener('resize',()=>{camera.aspect=W()/H();camera.updateProjectionMatrix();renderer.setSize(W(),H());});
const clock=new THREE.Clock();
(function tick(){
  const t=clock.getElapsedTime();
  core.rotation.y=t*.35; core.rotation.x=t*.2; inner.rotation.y=-t*.6; inner.rotation.z=t*.3;
  glow.scale.setScalar(1+Math.sin(t*2)*.12);
  r1.rotation.z=t*.3; r2.rotation.z=-t*.22;
  cards.forEach(c=>{const d=c.userData,a=d.a+t*d.s;c.position.set(Math.cos(a)*d.r,d.y+Math.sin(t+d.a)*.25,Math.sin(a)*d.r);c.rotation.y=-a+Math.PI/2;c.rotation.x=Math.sin(t*.7+d.a)*.2;});
  pts.rotation.y=t*.03;
  group.rotation.y+=(mx*1.1-group.rotation.y)*.05; group.rotation.x+=(my*.7-group.rotation.x)*.05;
  renderer.render(scene,camera); requestAnimationFrame(tick);
})();
}catch(e){document.body.innerHTML='<div style="color:#9aa3c7;font:14px sans-serif;padding:2rem">3D preview unavailable in this browser.</div>';}
</script></body></html>
"""
