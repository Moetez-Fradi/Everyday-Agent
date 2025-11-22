// static/script.js
import * as THREE from "https://esm.sh/three@0.155.0";
import { GLTFLoader } from "https://esm.sh/three@0.155.0/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "https://esm.sh/three@0.155.0/examples/jsm/controls/OrbitControls.js";

/* ---------- Three.js scene (kept minimal) ---------- */
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, window.innerWidth/window.innerHeight, 0.1, 100);
camera.position.set(0, 1.5, 3);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setClearColor(0x000000, 0);
document.body.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0,0.8,0); controls.update();
controls.enableRotate = false; controls.enableZoom = false; controls.enablePan = false;

const hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 1.0);
hemi.position.set(0,20,0); scene.add(hemi);

/* ---------- Load character ---------- */
let character = null;
let morphTargets = {};
let lipData = null;
const phonemeToViseme = {
  "X": "viseme_sil",
  "A": "viseme_PP",
  "B": "viseme_kk",
  "C": "viseme_I",
  "D": "viseme_aa",
  "E": "viseme_O",
  "F": "viseme_U",
  "G": "viseme_FF",
  "H": "viseme_TH"
};


const loader = new GLTFLoader();
loader.load('/static/characters/my_character.glb', (gltf) => {
  character = gltf.scene;
  character.position.set(0, -7.3, 0);
  character.scale.set(5,5,5);
  scene.add(character);

  // gather morph target dictionary from first mesh that has it
  character.traverse((o) => {
    if (o.isMesh && o.morphTargetDictionary) {
      morphTargets = o.morphTargetDictionary;
      console.log("[Three] Found morph targets:", morphTargets);
    }
  });

  // optional camera framing
  camera.position.set(-0.01, 0.78, 2.7);
  camera.lookAt(character.position);
}, undefined, (err) => {
  console.error("[Three] Character load failed:", err);
});

/* ---------- Resize handling ---------- */
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth/window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

/* ---------- apply viseme helper ---------- */
function applyViseme(visemeName) {
  if (!character) return;
  character.traverse((o) => {
    if (o.isMesh && o.morphTargetDictionary && o.morphTargetInfluences) {
      const dict = o.morphTargetDictionary;
      for (const key in dict) {
        const idx = dict[key];
        o.morphTargetInfluences[idx] = (key === visemeName) ? 1 : 0;
      }
    }
  });
}

/* ---------- Animation loop mapping lipData to morph targets ---------- */
let audioEl = null;
function animate() {
  requestAnimationFrame(animate);

  if (lipData && audioEl && !isNaN(audioEl.currentTime)) {
    const t = audioEl.currentTime;
    // find cue that contains current time
    const cue = (lipData.mouthCues || []).find(c => t >= c.start && t <= c.end);
    if (cue) {
      const viseme = phonemeToViseme[cue.value] || null;
      if (viseme) applyViseme(viseme);
    }
  }

  controls.update();
  renderer.render(scene, camera);
}
animate();

/* ---------- Chat UI logic (HTTP POST) ---------- */
const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('promptInput');
const sendBtn = document.getElementById('sendBtn');
const loadingOverlay = document.getElementById('loadingOverlay');

function addMsg(text, role='assistant') {
  const d = document.createElement('div');
  d.className = 'msg ' + (role === 'user' ? 'user' : 'assistant');
  // simple newline -> <br>
  d.innerHTML = text.replace(/\n/g, '<br/>');
  messagesEl.appendChild(d);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function sendPrompt(prompt) {
  loadingOverlay.style.display = 'block';
  console.log('[Client] Sending prompt:', prompt);
  try {
    const res = await fetch('http://localhost:8000/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ prompt })
    });
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`Server ${res.status}: ${txt}`);
    }
    const data = await res.json();
    loadingOverlay.style.display = 'none';
    console.log('[Client] Response:', data);
    const assistant = data.assistant || {};
    addMsg(assistant.text || '(no text)', 'assistant');

    if (assistant.lipsync) {
      lipData = assistant.lipsync;
      console.log('[Client] Loaded lipsync with', (lipData.mouthCues||[]).length, 'cues');
    } else {
      lipData = null;
    }

    if (assistant.audio) {
      if (!audioEl) audioEl = new Audio();
      audioEl.src = assistant.audio + '?v=' + Date.now();
      audioEl.crossOrigin = 'anonymous';
      audioEl.play().catch(e => console.warn('[Client] Audio play failed:', e));
    }
  } catch (err) {
    loadingOverlay.style.display = 'none';
    console.error('[Client] Error:', err);
    addMsg('Error contacting server: ' + err.message, 'assistant');
  }
}

// UI: send on click or Enter
sendBtn.addEventListener('click', () => {
  const txt = inputEl.value.trim();
  if (!txt) return;
  addMsg(txt, 'user');
  inputEl.value = '';
  sendPrompt(txt);
});
inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendBtn.click();
  }
});
