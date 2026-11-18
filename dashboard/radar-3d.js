/* Radar 3D da tela de abertura e do topo do painel.

   O mesmo desenho do SVG, num prato em perspectiva: tampo de papel, anéis de fio, a
   varredura azul e cada vaga como um pino cuja altura é a nota de fit. A vaga certa é a
   esfera amarela, com o selo "FIT 86".

   O desenho continua chapado (papel, tinta, azul, amarelo). Por cima dele, um pouco de luz:
   - uma luz fixa EM RELAÇÃO A QUEM OLHA, de cima e um pouco da esquerda: em qualquer giro
     as sombras caem para trás e para a direita, curtas, e a lateral do prato escurece do
     lado oposto. O prato tem espessura e uma sombra macia na página;
   - os pinos são esferas de verdade, com brilho, e deixam sombra no tampo;
   - a varredura é uma lanterna que sai do centro: nítida no ponteiro e cada vez mais difusa
     para trás e para a borda, até sumir. O pino que ela alcança fica azul do lado que dá
     para o centro, com o mesmo azul e a mesma força do facho naquele ponto: acende quando o
     facho chega e apaga junto com ele.

   O SVG fica no HTML como reserva: sem WebGL, sem módulo (aberto por file://) ou com erro,
   ele continua lá. Com movimento reduzido, um quadro parado; girar arrastando continua
   valendo, porque aí o movimento é seu.

   Quem corta o prato na borda da tela é o CSS (a abertura deixa 25% dele para fora). O
   selo sabe onde a tela acaba e troca de lado para nunca sair do que aparece. */

import * as THREE from "three";

const figura = document.querySelector(".radar");
const REDUZIDO = matchMedia("(prefers-reduced-motion: reduce)").matches;

// cores lidas dos tokens: o radar muda junto se o :root mudar
const css = getComputedStyle(document.documentElement);
const cor = nome => new THREE.Color(css.getPropertyValue(nome).trim());
const TINTA = cor("--ink");
const AMARELO = cor("--primary");
const AZUL = cor("--azul");
const PAPEL = cor("--paper");
const CINZA = cor("--g300");
const LATERAL = cor("--g100");
const LATERAL_SOMBRA = cor("--g300");
const CLARO = AZUL.clone().lerp(PAPEL, 0.45);   // o miolo do brilho onde o facho bate de frente

const R = 1.96;             // raio do prato (o SVG tem 196px: 100px = 1 unidade)
const ESPESSURA = 0.16;
const FIO = 0.007;          // meia largura dos anéis: perto de 1px na tela
const VOLTA = 7;            // segundos por volta da varredura, como no SVG
const ELEVACAO = 0.74;      // altura da câmera, em radianos acima do tampo
const INCLINA = 0.1;        // quanto o arrasto vertical sobe ou desce a câmera
const PARALLAX = { az: 0.22, el: 0.08 };  // quanto o ponteiro do mouse mexe a câmera
// a luz fixa anda com a câmera: um pouco à esquerda de quem olha (radianos de azimute) e
// alta (radianos acima do tampo), para a sombra ser curta
const LUZ = { az: -0.7, el: 1.15, distancia: 8 };
// o facho: a faixa de azul cheio colada no ponteiro e o quanto ele esmaece para trás, perto
// do centro e na borda. O shader e o brilho dos pinos usam os mesmos números
const FACHO = { cheio: 0.18, kCentro: 5.5, kBorda: 3.2 };

// posições do SVG (centro em 200,200), com uma nota de fit para cada pino. A vaga certa
// fica a 0,7 do centro: em qualquer giro ela cai nos 75% do prato que a abertura mostra
const doSvg = (x, y) => ({ x: (x - 200) / 100, z: (y - 200) / 100 });
const VAGAS = [[140, 122, 62], [112, 248, 48], [296, 262, 71], [182, 324, 55], [322, 184, 66], [234, 236, 58]]
  .map(([x, y, fit]) => ({ ...doSvg(x, y), fit }));
const ALVO = { ...doSvg(250, 150), fit: 86, alvo: true };
const altura = fit => Math.max(0.12, ((fit - 40) / 60) * 1.4);

function plano(geometria, material, y, ordem) {
  const m = new THREE.Mesh(geometria, material);
  m.rotation.x = -Math.PI / 2;
  m.position.y = y;
  m.renderOrder = ordem;
  return m;
}

function chapado(c, extra = {}) {
  return new THREE.MeshBasicMaterial({ color: c, ...extra });
}

// força do facho a d radianos atrás do ponteiro, a r do centro (a mesma conta do shader)
function forcaDoFacho(d, r) {
  const k = FACHO.kCentro + (FACHO.kBorda - FACHO.kCentro) * Math.min(1, r / (R - 0.02));
  return d < FACHO.cheio ? 1 : Math.exp(-(d - FACHO.cheio) * k);
}

// a lateral do prato sombreada sem luz de verdade: clara do lado da luz e no alto, mais
// escura do lado oposto e embaixo. Continua cor chapada, só que em degradê, repintada
// quando a luz muda de lado (ela anda com a câmera)
function lateralSombreada() {
  const g = new THREE.CylinderGeometry(R, R, ESPESSURA, 192, 1, true);
  g.setAttribute("color", new THREE.Float32BufferAttribute(new Float32Array(g.attributes.position.count * 3), 3));
  return new THREE.Mesh(g, new THREE.MeshBasicMaterial({ vertexColors: true }));
}

function pintarLateral(lateral, luzX, luzZ) {
  const pos = lateral.geometry.attributes.position;
  const cores = lateral.geometry.attributes.color;
  const c = new THREE.Color();
  for (let i = 0; i < pos.count; i++) {
    const frente = (pos.getX(i) * luzX + pos.getZ(i) * luzZ) / R;   // 1 de frente para a luz
    const baixo = pos.getY(i) < 0 ? 1 : 0;
    c.copy(LATERAL).lerp(LATERAL_SOMBRA, THREE.MathUtils.clamp(0.55 - 0.45 * frente + 0.35 * baixo, 0, 1));
    cores.setXYZ(i, c.r, c.g, c.b);
  }
  cores.needsUpdate = true;
}

// o brilho do facho num pino: uma casca colada na esfera (e na haste) que pinta de azul o
// lado virado para o eixo do radar, de onde a lanterna sai, na força do facho ali
const BRILHO_VERT = /* glsl */ `
  varying vec3 vN;
  varying vec3 vW;
  void main() {
    vW = (modelMatrix * vec4(position, 1.0)).xyz;
    vN = normalize(mat3(modelMatrix) * normal);
    gl_Position = projectionMatrix * viewMatrix * vec4(vW, 1.0);
  }`;
const BRILHO_FRAG = /* glsl */ `
  uniform vec3 uAzul;
  uniform vec3 uClaro;
  uniform float uForca;
  varying vec3 vN;
  varying vec3 vW;
  void main() {
    vec3 N = normalize(vN);
    vec3 L = normalize(vec3(-vW.x, 0.0, -vW.z));             // do pino para o eixo, na altura dele
    float lambert = max(dot(N, L), 0.0);
    // a lanterna é larga: a luz dobra um pouco além da metade virada para o centro
    float direta = smoothstep(-0.35, 0.6, dot(N, L));
    // e o tampo azul embaixo devolve luz: a parte de baixo da esfera pega a mesma cor
    float rebate = 0.75 * smoothstep(0.0, 0.85, -N.y);
    float a = uForca * max(direta, rebate);
    gl_FragColor = vec4(mix(uAzul, uClaro, pow(lambert, 6.0) * 0.3), a);
    #include <colorspace_fragment>
  }`;

// a varredura: d = quanto atrás do ponteiro (0 no ponteiro). Colada nele, azul cheio e
// nítido; para trás e para a borda ela se abre e esmaece até sumir
const FACHO_VERT = /* glsl */ `
  varying vec2 vP;
  void main() {
    vP = position.xy;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }`;
const FACHO_FRAG = /* glsl */ `
  uniform float uAng;
  uniform float uR;
  uniform vec3 uAzul;
  varying vec2 vP;
  const float VOLTA = 6.28318530718;
  void main() {
    float r = length(vP);
    float d = mod(atan(vP.y, vP.x) - uAng, VOLTA);
    float px = length(fwidth(vP)) / max(r, 1e-3);           // um pixel, em ângulo
    float cheio = ${FACHO.cheio.toFixed(3)};                 // a faixa de azul cheio colada no ponteiro
    float k = mix(${FACHO.kCentro.toFixed(3)}, ${FACHO.kBorda.toFixed(3)}, r / uR);  // mais longe do centro, mais espalhado
    float a = d < cheio ? 1.0 : exp(-(d - cheio) * k);
    a *= smoothstep(0.0, 1.5 * px, d);                       // a borda da frente, sem serrilhado
    a *= smoothstep(uR, uR - 0.04, r);
    gl_FragColor = vec4(uAzul, a);
    #include <colorspace_fragment>
  }`;

function iniciar() {
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch {
    return; // sem WebGL: o SVG fica
  }
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const canvas = renderer.domElement;
  canvas.setAttribute("aria-hidden", "true");

  const cena = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 60);
  const radar = new THREE.Group();
  cena.add(radar);

  // ---- luz: só os pinos e a sombra deles usam. O resto é cor chapada ----
  cena.add(new THREE.HemisphereLight(0xffffff, PAPEL, 2.2));
  const sol = new THREE.DirectionalLight(0xffffff, 2.2);
  sol.castShadow = true;
  sol.shadow.mapSize.set(2048, 2048);
  Object.assign(sol.shadow.camera, { left: -2.6, right: 2.6, top: 2.6, bottom: -2.6, near: 1, far: 16 });
  sol.shadow.bias = -0.0005;
  cena.add(sol);

  // ---- o prato: tampo de papel, lateral sombreada, fio em cima e embaixo ----
  radar.add(plano(new THREE.CircleGeometry(R, 192), chapado(PAPEL), 0, 0));
  const lateral = lateralSombreada();
  lateral.position.y = -ESPESSURA / 2;
  radar.add(lateral);
  const sobreposto = { depthWrite: false };
  radar.add(plano(new THREE.RingGeometry(R - 0.018, R, 192), chapado(TINTA, sobreposto), 0.004, 3));
  radar.add(plano(new THREE.RingGeometry(R - 0.004, R + 0.012, 192), chapado(TINTA), -ESPESSURA, 0));

  // a sombra dos pinos no tampo: uma película que só mostra sombra, por cima do papel
  const pelicula = plano(new THREE.CircleGeometry(R - 0.02, 192), new THREE.ShadowMaterial({ opacity: 0.16, depthWrite: false }), 0.0015, 2);
  pelicula.receiveShadow = true;
  radar.add(pelicula);

  // a sombra do prato na página: uma mancha macia embaixo, puxada para longe da luz
  const mancha = document.createElement("canvas");
  mancha.width = mancha.height = 256;
  const g = mancha.getContext("2d");
  const degrade = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  degrade.addColorStop(0, "rgba(5,5,5,0.16)");
  degrade.addColorStop(0.8, "rgba(5,5,5,0.1)");
  degrade.addColorStop(1, "rgba(5,5,5,0)");
  g.fillStyle = degrade;
  g.fillRect(0, 0, 256, 256);
  const textura = new THREE.CanvasTexture(mancha);
  textura.colorSpace = THREE.SRGBColorSpace;
  const SOMBRA = R * 1.1;
  const sombra = plano(new THREE.PlaneGeometry(2 * SOMBRA, 2 * SOMBRA),
    new THREE.MeshBasicMaterial({ map: textura, transparent: true, depthWrite: false }), -ESPESSURA - 0.004, -1);
  radar.add(sombra);

  // a luz anda com a câmera: a cada giro, reposiciona o sol, repinta a lateral e puxa a
  // mancha de sombra para o lado oposto à luz
  let azDaLuz = null;
  function acompanharLuz(azCamera) {
    if (azDaLuz !== null && Math.abs(azCamera - azDaLuz) < 0.002) return;
    azDaLuz = azCamera;
    const az = azCamera + LUZ.az;
    const x = Math.sin(az), z = Math.cos(az);
    sol.position.set(LUZ.distancia * Math.cos(LUZ.el) * x, LUZ.distancia * Math.sin(LUZ.el), LUZ.distancia * Math.cos(LUZ.el) * z);
    pintarLateral(lateral, x, z);
    sombra.position.x = -0.24 * x;
    sombra.position.z = -0.24 * z;
  }

  // ---- eixos e anéis ----
  for (const giro of [0, Math.PI / 2]) {
    const eixo = plano(new THREE.PlaneGeometry(2 * R - 0.04, 0.012), chapado(CINZA, sobreposto), 0.002, 1);
    eixo.rotation.z = giro;
    radar.add(eixo);
  }
  for (const r of [0.5, 1, 1.5]) {
    radar.add(plano(new THREE.RingGeometry(r - FIO, r + FIO, 160), chapado(TINTA, sobreposto), 0.004, 3));
  }

  // ---- a varredura: o facho azul atrás de um ponteiro de tinta ----
  const varredura = new THREE.Group();
  varredura.position.y = 0.001;
  const facho = plano(new THREE.CircleGeometry(R - 0.02, 192), new THREE.ShaderMaterial({
    uniforms: { uAng: { value: 0 }, uR: { value: R - 0.02 }, uAzul: { value: AZUL } },
    vertexShader: FACHO_VERT,
    fragmentShader: FACHO_FRAG,
    transparent: true,
    depthWrite: false,
  }), 0.001, 1);
  radar.add(facho);
  const ponteiro = plano(new THREE.PlaneGeometry(R - 0.02, 0.016), chapado(TINTA, sobreposto), 0.003, 4);
  ponteiro.position.x = (R - 0.02) / 2;
  varredura.add(ponteiro);
  radar.add(varredura);

  const centro = plano(new THREE.CircleGeometry(0.035, 24), chapado(TINTA, sobreposto), 0.005, 5);
  radar.add(centro);

  // ---- vagas vivas: pino com altura = fit, esfera com brilho ----
  const pinos = [...VAGAS, ALVO].map(v => {
    const h = altura(v.fit);
    const grupo = new THREE.Group();
    grupo.position.set(v.x, 0, v.z);

    const pe = plano(new THREE.CircleGeometry(0.034, 24), chapado(TINTA, sobreposto), 0.005, 5);
    const haste = new THREE.Mesh(new THREE.CylinderGeometry(0.01, 0.01, h, 12), chapado(TINTA));
    haste.position.y = h / 2;
    haste.castShadow = true;
    // o brilho do facho, na haste e na cabeça (a vaga certa continua amarela)
    const brilho = new THREE.ShaderMaterial({
      uniforms: { uAzul: { value: AZUL }, uClaro: { value: CLARO }, uForca: { value: 0 } },
      vertexShader: BRILHO_VERT,
      fragmentShader: BRILHO_FRAG,
      transparent: true,
      depthWrite: false,
    });
    const casca = new THREE.Mesh(new THREE.CylinderGeometry(0.0115, 0.0115, h, 12), brilho);
    casca.position.y = h / 2;
    casca.renderOrder = 7;
    const cabeca = new THREE.Group();
    cabeca.position.y = h;
    let material;
    if (v.alvo) {
      // contorno de tinta = esfera maior com a face de dentro: é fio, como no SVG
      cabeca.add(new THREE.Mesh(new THREE.SphereGeometry(0.125, 48, 24), chapado(TINTA, { side: THREE.BackSide })));
      material = new THREE.MeshStandardMaterial({ color: AMARELO, roughness: 0.38, emissive: AMARELO, emissiveIntensity: 0.35 });
    } else {
      material = new THREE.MeshStandardMaterial({ color: TINTA, roughness: 0.32, metalness: 0.1 });
    }
    const esfera = new THREE.Mesh(new THREE.SphereGeometry(v.alvo ? 0.105 : 0.06, 48, 24), material);
    esfera.castShadow = true;
    cabeca.add(esfera);
    if (!v.alvo) {
      const cascaCabeca = new THREE.Mesh(new THREE.SphereGeometry(0.0615, 48, 24), brilho);
      cascaCabeca.renderOrder = 7;
      cabeca.add(cascaCabeca);
    }
    // onda que abre no tampo quando a varredura passa: azul nos pinos, tinta na vaga certa
    const onda = plano(new THREE.RingGeometry(0.075, 0.085, 64),
      chapado(v.alvo ? TINTA : AZUL, { transparent: true, opacity: 0, depthWrite: false }), 0.006, 6);

    grupo.add(pe, haste, casca, cabeca, onda);
    radar.add(grupo);
    return { ...v, h, cabeca, onda, brilho, raio: Math.hypot(v.x, v.z), angulo: Math.atan2(-v.z, v.x), pingou: -10 };
  });
  const alvo = pinos.find(p => p.alvo);

  // ---- o selo FIT 86 é HTML: texto nítido, mesma pílula do sistema ----
  const selo = document.createElement("span");
  selo.className = "radar__selo3d";
  selo.textContent = `FIT ${ALVO.fit}`;
  selo.setAttribute("aria-hidden", "true");
  const dica = document.createElement("figcaption");
  dica.className = "radar__dica meta";
  dica.textContent = "Arraste para girar";
  dica.setAttribute("aria-hidden", "true");

  // ---- câmera: órbita em volta do prato, com parallax do ponteiro e arrasto ----
  let distancia = 7.3;
  const v3 = new THREE.Vector3();
  const olhar = new THREE.Vector3(0, 0.12, 0);
  const orbita = { az: -0.35, el: ELEVACAO };       // onde está
  const destino = { az: -0.35, el: ELEVACAO };      // para onde vai
  const arrasto = { ativo: false, x: 0, y: 0, az: 0, el: 0 };
  let parallax = { x: 0, y: 0 };

  function posicionarCamera() {
    const el = orbita.el + parallax.y * PARALLAX.el;
    const az = orbita.az + parallax.x * PARALLAX.az;
    camera.position.set(
      olhar.x + distancia * Math.cos(el) * Math.sin(az),
      olhar.y + distancia * Math.sin(el),
      olhar.z + distancia * Math.cos(el) * Math.cos(az),
    );
    camera.lookAt(olhar);
  }

  canvas.addEventListener("pointerdown", e => {
    arrasto.ativo = true;
    arrasto.x = e.clientX;
    arrasto.y = e.clientY;
    arrasto.az = destino.az;
    arrasto.el = destino.el;
    canvas.setPointerCapture(e.pointerId);
    dica.classList.add("usada");
    pedirQuadro();
  });
  canvas.addEventListener("pointermove", e => {
    const caixa = canvas.getBoundingClientRect();
    if (arrasto.ativo) {
      destino.az = arrasto.az - ((e.clientX - arrasto.x) / caixa.width) * Math.PI * 1.2;
      destino.el = THREE.MathUtils.clamp(arrasto.el + ((e.clientY - arrasto.y) / caixa.height) * 1.2, ELEVACAO - INCLINA, ELEVACAO + INCLINA);
    } else if (!REDUZIDO && e.pointerType === "mouse") {
      parallax = { x: (e.clientX - caixa.left) / caixa.width - 0.5, y: (e.clientY - caixa.top) / caixa.height - 0.5 };
    }
    pedirQuadro();
  });
  const soltar = () => { arrasto.ativo = false; };
  canvas.addEventListener("pointerup", soltar);
  canvas.addEventListener("pointercancel", soltar);
  canvas.addEventListener("pointerleave", () => { parallax = { x: 0, y: 0 }; pedirQuadro(); });

  // ---- tamanho: a largura vem da figura; a altura, do que o prato ocupa ----
  let largura = 0;
  let alturaTela = 0;
  let visivelAte = 0;   // até onde o canvas aparece na tela: a abertura corta o lado direito
  let seloLargura = 0;

  // o enquadramento sai da projeção de verdade: a borda do prato em cima e embaixo, a
  // sombra, o topo de cada pino e um respiro para o selo, em TODAS as posições que a câmera
  // alcança. A órbita gira sozinha e o arrasto sobe e desce: a sombra (que fica do lado
  // oposto à luz) e os pinos mudam de lugar na tela, e nada pode sair do quadro em nenhuma
  // delas. O prato encosta nas laterais do canvas (o corte de 25% da abertura é 25% dele)
  const amostras = [];
  for (let i = 0; i < 64; i++) {
    const a = (i / 64) * Math.PI * 2;
    amostras.push(new THREE.Vector3(R * Math.cos(a), 0, R * Math.sin(a)), new THREE.Vector3(R * Math.cos(a), -ESPESSURA, R * Math.sin(a)));
    amostras.push(new THREE.Vector3(0.18 + 0.96 * SOMBRA * Math.cos(a), -ESPESSURA, -0.16 + 0.96 * SOMBRA * Math.sin(a)));
  }
  for (const p of pinos) amostras.push(new THREE.Vector3(p.x, p.h + (p.alvo ? 0.34 : 0.08), p.z));

  const poses = [];
  const folga = INCLINA + PARALLAX.el / 2;
  for (let i = 0; i < 16; i++) {
    for (const el of [ELEVACAO - folga, ELEVACAO, ELEVACAO + folga]) poses.push({ az: (i / 16) * Math.PI * 2, el });
  }

  function caixaProjetada(d) {
    distancia = d;
    camera.clearViewOffset();
    const c = { x0: 1e9, x1: -1e9, y0: 1e9, y1: -1e9 };
    const guardada = { ...orbita }, semParallax = parallax;
    parallax = { x: 0, y: 0 };
    for (const pose of poses) {
      Object.assign(orbita, pose);
      posicionarCamera();
      camera.updateMatrixWorld();
      for (const a of amostras) {
        v3.copy(a).project(camera);
        c.x0 = Math.min(c.x0, v3.x); c.x1 = Math.max(c.x1, v3.x);
        c.y0 = Math.min(c.y0, v3.y); c.y1 = Math.max(c.y1, v3.y);
      }
    }
    Object.assign(orbita, guardada);
    parallax = semParallax;
    posicionarCamera();
    return c;
  }

  // primeiro a distância em que a altura cabe, depois a altura do canvas que faz o prato
  // encostar nas laterais
  function enquadrar() {
    camera.aspect = 1;
    const cabe = c => (c.y1 - c.y0) / 2 <= 0.94;
    let perto = 2, longe = 40;
    for (let i = 0; i < 32; i++) {
      const meio = (perto + longe) / 2;
      if (cabe(caixaProjetada(meio))) longe = meio; else perto = meio;
    }
    const lado = caixaProjetada(longe);
    alturaTela = Math.round(largura / (Math.max(-lado.x0, lado.x1) / 0.98));
    renderer.setSize(largura, alturaTela);
    camera.aspect = largura / alturaTela;
    const c = caixaProjetada(longe);
    camera.setViewOffset(largura, alturaTela, 0, Math.round((-(c.y1 + c.y0) / 2) * (alturaTela / 2)), largura, alturaTela);
  }

  function medirVisivel() {
    const caixa = canvas.getBoundingClientRect();
    visivelAte = Math.min(largura, document.documentElement.clientWidth - caixa.left);
  }

  function medir() {
    const novaLargura = Math.round(figura.clientWidth);
    if (!novaLargura || novaLargura === largura) return;
    largura = novaLargura;
    enquadrar();
    medirVisivel();
    seloLargura = selo.offsetWidth;
    pedirQuadro();
  }
  new ResizeObserver(medir).observe(figura);
  addEventListener("resize", medirVisivel);

  // ---- laço: só roda com a figura na tela e a aba à vista ----
  const relogio = new THREE.Clock();
  let visivel = true;
  let pedido = 0;
  let angulo = 0;
  let anterior = 0;

  function pedirQuadro() {
    if (!pedido && visivel && !document.hidden) pedido = requestAnimationFrame(quadro);
  }

  function normal(a) {
    const volta = Math.PI * 2;
    return ((a % volta) + volta) % volta;
  }

  function quadro() {
    pedido = 0;
    const dt = Math.min(relogio.getDelta(), 0.1);
    const t = relogio.elapsedTime;

    if (!REDUZIDO) {
      angulo -= (dt / VOLTA) * Math.PI * 2;
      // a onda abre no tampo quando o ponteiro passa pelo pino
      for (const p of pinos) {
        if (normal(angulo - p.angulo) > normal(anterior - p.angulo)) p.pingou = t;
        const idade = t - p.pingou;
        const onda = Math.min(idade / 1.1, 1);
        p.onda.scale.setScalar(1 + onda * 3.5);
        p.onda.material.opacity = idade < 1.1 ? 0.8 * (1 - onda) : 0;
      }
      anterior = angulo;
      if (!arrasto.ativo) destino.az += dt * 0.04; // a órbita anda devagar sozinha
    }
    varredura.rotation.y = angulo;
    facho.material.uniforms.uAng.value = angulo;
    // o pino acende na força do facho onde ele está: o mesmo azul, a mesma hora de apagar.
    // O tamanho não muda
    for (const p of pinos) p.brilho.uniforms.uForca.value = forcaDoFacho(normal(p.angulo - angulo), p.raio);

    orbita.az += (destino.az - orbita.az) * (REDUZIDO ? 1 : 0.08);
    orbita.el += (destino.el - orbita.el) * (REDUZIDO ? 1 : 0.08);
    posicionarCamera();
    acompanharLuz(orbita.az + parallax.x * PARALLAX.az);
    renderer.render(cena, camera);

    // selo acompanha a esfera amarela, um pouco acima; à direita dela, ou à esquerda
    // quando a direita já está fora da tela
    alvo.cabeca.getWorldPosition(v3).project(camera);
    const x = (v3.x * 0.5 + 0.5) * largura;
    const y = (-v3.y * 0.5 + 0.5) * alturaTela;
    const cabeDireita = x + 16 + seloLargura <= visivelAte - 16;
    const sx = cabeDireita ? x + 16 : x - 16 - seloLargura;
    selo.style.transform = `translate(${Math.round(sx)}px, ${Math.round(Math.max(0, y - 44))}px)`;

    const parado = Math.abs(destino.az - orbita.az) < 1e-4 && Math.abs(destino.el - orbita.el) < 1e-4;
    if (!REDUZIDO || !parado) pedirQuadro();
  }

  new IntersectionObserver(([e]) => {
    visivel = e.isIntersecting;
    if (visivel) { relogio.getDelta(); pedirQuadro(); }
  }).observe(figura);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) { relogio.getDelta(); pedirQuadro(); }
  });

  // perdeu o contexto do WebGL (driver, aba em segundo plano): volta para o SVG
  canvas.addEventListener("webglcontextlost", e => {
    e.preventDefault();
    figura.classList.remove("radar--3d");
  });

  // movimento reduzido: um quadro parado, com o facho já passado pela vaga certa
  if (REDUZIDO) angulo = alvo.angulo - 0.35;
  figura.append(canvas, selo, dica);
  figura.classList.add("radar--3d");
  medir();
  pedirQuadro();
}

if (figura) iniciar();
