// script.js (ES module)
import * as THREE from "https://esm.sh/three@0.155.0";
import { GLTFLoader } from "https://esm.sh/three@0.155.0/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "https://esm.sh/three@0.155.0/examples/jsm/controls/OrbitControls.js";

/* ---------- Scene / Camera / Renderer ---------- */
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 1.5, 3);

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); // alpha:true lets CSS background show through
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(window.innerWidth, window.innerHeight);
// make canvas transparent so CSS background is visible
renderer.setClearColor(0x000000, 0);
document.body.appendChild(renderer.domElement);

/* ---------- Controls / Lighting ---------- */
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0.8, 0);
controls.update();

controls.enableRotate = false;
controls.enableZoom = false;
controls.enablePan = false;


const hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 1.0);
hemi.position.set(0, 20, 0);
scene.add(hemi);

/* ---------- Optional: Use the image as a Three.js background (Option B) ---------- */
/* 
// Uncomment to use the image as a scene background instead of CSS background.
// Note: if you use this, you can change renderer alpha to false if desired.
const loaderTex = new THREE.TextureLoader();
loaderTex.load('background.jpg', (tex) => {
  // For equirectangular panoramas you might want: tex.mapping = THREE.EquirectangularReflectionMapping;
  scene.background = tex;
});
*/

/* ---------- Resize handling ---------- */
window.addEventListener('resize', onWindowResize);
function onWindowResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}

/* ---------- Character + Lipsync ---------- */
let character;
let morphTargets = {};
let lipData;
const audio = new Audio('./audio/assistant_output.wav?v=' + Date.now());

window.camera = camera;

const phonemeToViseme = {
  "A": "viseme_PP",
  "B": "viseme_SS",
  "C": "viseme_E",
  "D": "viseme_aa",
  "E": "viseme_O",
  "F": "viseme_U",
  "G": "viseme_FF",
  "H": "viseme_RR",
  "X": "viseme_sil"
};

// Load lipsync data
fetch('lipsync.json')
  .then(res => res.json())
  .then(data => lipData = data)
  .catch(err => console.warn('Failed to load lipsync.json:', err));

// Load character
const loader = new GLTFLoader();
loader.load('/characters/my_character.glb', (gltf) => {
  character = gltf.scene;
  window.character = character;

  // adjust the model transform to taste
  character.position.set(0, -7.3, 0);
  character.scale.set(5,5,5);

  scene.add(character);

    camera.position.set(-0.013933265713259615, 0.7787288174461275, 2.7027064851812876);
    camera.lookAt(character.position);

  // Find morph targets on the mesh (first mesh with morphTargetDictionary)
  character.traverse((o) => {
    if (o.isMesh && o.morphTargetDictionary) {
      morphTargets = o.morphTargetDictionary;
      console.log("Morph Targets:", morphTargets);
    }
  });

  animate();
}, undefined, (err) => {
  console.error('Failed to load GLB:', err);
});

/* ---------- Animation / Lipsync application ---------- */
function animate() {
  requestAnimationFrame(animate);

  if (character && lipData && !isNaN(audio.currentTime)) {
    const t = audio.currentTime;
    // find the cue that contains current time (simple linear search; fine for small arrays)
    const currentCue = lipData.mouthCues.find(c => t >= c.start && t <= c.end);
    if (currentCue) {
      const visemeName = phonemeToViseme[currentCue.value];
      character.traverse((o) => {
        if (o.isMesh && o.morphTargetDictionary && o.morphTargetInfluences) {
          const dict = o.morphTargetDictionary;
          // zero out all influences then set the chosen one to 1
          for (const key in dict) {
            const idx = dict[key];
            o.morphTargetInfluences[idx] = (key === visemeName) ? 1 : 0;
          }
        }
      });
    }
  }

  controls.update();
  renderer.render(scene, camera);
}

window.addEventListener('click', () => {
  audio.play().catch(e => console.warn('Audio play failed:', e));
});
