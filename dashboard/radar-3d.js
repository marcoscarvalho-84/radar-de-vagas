/* Radar 3D da tela de abertura.

   O mesmo desenho do SVG, agora num prato em perspectiva: anéis de fio, uma cunha azul
   varrendo e cada vaga como um pino cuja altura é a nota de fit. A vaga certa é a esfera
   amarela, com o selo "FIT 86"; as cortadas na triagem ficam deitadas no prato, em cinza.

   Continua chapado como o resto do sistema: só MeshBasicMaterial, sem luz e sem sombra.
   A profundidade vem da perspectiva, da espessura do prato e do fio.

   O SVG fica no HTML como reserva: sem WebGL, sem módulo (aberto por file://) ou com erro,
   ele continua lá. Com movimento reduzido, um quadro parado; girar arrastando continua
   valendo, porque aí o movimento é seu. */

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

const R = 1.96;             // raio do prato (o SVG tem 196px: 100px = 1 unidade)
const ESPESSURA = 0.09;
const FIO = 0.007;          // meia largura dos anéis: perto de 1px na tela
const VOLTA = 7;            // segundos por volta da varredura, como no SVG

// posições do SVG (centro em 200,200), com uma nota de fit para cada pino
const doSvg = (x, y) => ({ x: (x - 200) / 100, z: (y - 200) / 100 });
const VAGAS = [[140, 122, 62], [112, 248, 48], [296, 262, 71], [182, 324, 55], [322, 184, 66], [234, 236, 58]]
  .map(([x, y, fit]) => ({ ...doSvg(x, y), fit }));
const CORTADAS = [[64, 296], [338, 292], [96, 96]].map(([x, y]) => doSvg(x, y));
const ALVO = { ...doSvg(266, 140), fit: 86, alvo: true };
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

function iniciar() {
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch {
    return; // sem WebGL: o SVG fica
  }
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setClearColor(0x000000, 0);
  const canvas = renderer.domElement;
  canvas.setAttribute("aria-hidden", "true");

  const cena = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 50);
  const radar = new THREE.Group();
  cena.add(radar);

  // ---- o prato: tampo de papel, lateral em cinza quente, fio em cima e embaixo ----
  radar.add(plano(new THREE.CircleGeometry(R, 160), chapado(PAPEL), 0, 0));
  const lateral = new THREE.Mesh(new THREE.CylinderGeometry(R, R, ESPESSURA, 160, 1, true), chapado(LATERAL));
  lateral.position.y = -ESPESSURA / 2;
  radar.add(lateral);
  const sobreposto = { depthWrite: false };
  radar.add(plano(new THREE.RingGeometry(R - 0.018, R, 160), chapado(TINTA, sobreposto), 0.004, 3));
  radar.add(plano(new THREE.RingGeometry(R - 0.004, R + 0.012, 160), chapado(TINTA), -ESPESSURA, 0));

  // ---- eixos e anéis ----
  for (const giro of [0, Math.PI / 2]) {
    const eixo = plano(new THREE.PlaneGeometry(2 * R - 0.04, 0.012), chapado(CINZA, sobreposto), 0.002, 1);
    eixo.rotation.z = giro;
    radar.add(eixo);
  }
  for (const r of [0.5, 1, 1.5]) {
    radar.add(plano(new THREE.RingGeometry(r - FIO, r + FIO, 128), chapado(TINTA, sobreposto), 0.004, 3));
  }

  // ---- a varredura: cunha azul atrás de um ponteiro de tinta ----
  const varredura = new THREE.Group();
  varredura.position.y = 0.001;
  const cunha = plano(new THREE.CircleGeometry(R - 0.02, 48, 0, THREE.MathUtils.degToRad(40)), chapado(AZUL, sobreposto), 0, 1);
  const ponteiro = plano(new THREE.PlaneGeometry(R - 0.02, 0.016), chapado(TINTA, sobreposto), 0.002, 4);
  ponteiro.position.x = (R - 0.02) / 2;
  varredura.add(cunha, ponteiro);
  radar.add(varredura);

  // ---- vagas cortadas: deitadas no prato ----
  for (const v of CORTADAS) {
    const ponto = plano(new THREE.CircleGeometry(0.045, 24), chapado(CINZA, sobreposto), 0.005, 5);
    ponto.position.x = v.x;
    ponto.position.z = v.z;
    radar.add(ponto);
  }
  const centro = plano(new THREE.CircleGeometry(0.035, 24), chapado(TINTA, sobreposto), 0.005, 5);
  radar.add(centro);

  // ---- vagas vivas: pino com altura = fit ----
  const pinos = [...VAGAS, ALVO].map(v => {
    const h = altura(v.fit);
    const grupo = new THREE.Group();
    grupo.position.set(v.x, 0, v.z);

    const pe = plano(new THREE.CircleGeometry(0.034, 24), chapado(TINTA, sobreposto), 0.005, 5);
    const haste = new THREE.Mesh(new THREE.CylinderGeometry(0.01, 0.01, h, 8), chapado(TINTA));
    haste.position.y = h / 2;
    const cabeca = new THREE.Group();
    cabeca.position.y = h;
    if (v.alvo) {
      // contorno de tinta = esfera maior com a face de dentro: é fio, não sombra
      cabeca.add(new THREE.Mesh(new THREE.SphereGeometry(0.125, 40, 24), chapado(TINTA, { side: THREE.BackSide })));
      cabeca.add(new THREE.Mesh(new THREE.SphereGeometry(0.105, 40, 24), chapado(AMARELO)));
    } else {
      cabeca.add(new THREE.Mesh(new THREE.SphereGeometry(0.06, 24, 16), chapado(TINTA)));
    }
    // onda que abre no prato quando a varredura passa
    const onda = plano(new THREE.RingGeometry(0.07, 0.085, 48),
      chapado(TINTA, { transparent: true, opacity: 0, depthWrite: false }), 0.006, 6);

    grupo.add(pe, haste, cabeca, onda);
    radar.add(grupo);
    return { ...v, h, cabeca, onda, angulo: Math.atan2(-v.z, v.x), pingou: -10 };
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
  const DIST = 7.3;
  const olhar = new THREE.Vector3(0, 0.22, 0);
  const orbita = { az: -0.35, el: 0.86 };          // onde está
  const destino = { az: -0.35, el: 0.86 };         // para onde vai
  const arrasto = { ativo: false, x: 0, y: 0, az: 0, el: 0 };
  let parallax = { x: 0, y: 0 };

  function posicionarCamera() {
    const el = orbita.el + parallax.y * 0.08;
    const az = orbita.az + parallax.x * 0.22;
    camera.position.set(DIST * Math.cos(el) * Math.sin(az), DIST * Math.sin(el), DIST * Math.cos(el) * Math.cos(az));
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
      destino.el = THREE.MathUtils.clamp(arrasto.el + ((e.clientY - arrasto.y) / caixa.height) * 1.2, 0.32, 1.35);
    } else if (!REDUZIDO && e.pointerType === "mouse") {
      parallax = { x: (e.clientX - caixa.left) / caixa.width - 0.5, y: (e.clientY - caixa.top) / caixa.height - 0.5 };
    }
    pedirQuadro();
  });
  const soltar = () => { arrasto.ativo = false; };
  canvas.addEventListener("pointerup", soltar);
  canvas.addEventListener("pointercancel", soltar);
  canvas.addEventListener("pointerleave", () => { parallax = { x: 0, y: 0 }; pedirQuadro(); });

  // ---- tamanho: quadrado na largura da figura ----
  let lado = 0;
  function medir() {
    const novo = Math.round(figura.clientWidth);
    if (!novo || novo === lado) return;
    lado = novo;
    renderer.setSize(lado, lado);
    camera.aspect = 1;
    camera.updateProjectionMatrix();
    pedirQuadro();
  }
  new ResizeObserver(medir).observe(figura);

  // ---- laço: só roda com a figura na tela e a aba à vista ----
  const relogio = new THREE.Clock();
  const v3 = new THREE.Vector3();
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
      varredura.rotation.y = angulo;
      // o pino "acende" quando o ponteiro passa por ele
      for (const p of pinos) {
        if (normal(angulo - p.angulo) > normal(anterior - p.angulo)) p.pingou = t;
        const idade = t - p.pingou;
        const pulso = idade < 0.6 ? 1 + 0.5 * Math.sin((idade / 0.6) * Math.PI) : 1;
        p.cabeca.scale.setScalar(pulso);
        const onda = Math.min(idade / 1.1, 1);
        p.onda.scale.setScalar(1 + onda * 3.5);
        p.onda.material.opacity = idade < 1.1 ? 0.9 * (1 - onda) : 0;
      }
      anterior = angulo;
      if (!arrasto.ativo) destino.az += dt * 0.04; // a órbita anda devagar sozinha
    }

    orbita.az += (destino.az - orbita.az) * (REDUZIDO ? 1 : 0.08);
    orbita.el += (destino.el - orbita.el) * (REDUZIDO ? 1 : 0.08);
    posicionarCamera();
    renderer.render(cena, camera);

    // selo acompanha a esfera amarela, um pouco acima e à direita
    alvo.cabeca.getWorldPosition(v3).project(camera);
    const x = (v3.x * 0.5 + 0.5) * lado;
    const y = (-v3.y * 0.5 + 0.5) * lado;
    selo.style.transform = `translate(${Math.round(x + 14)}px, ${Math.round(y - 40)}px)`;

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

  if (REDUZIDO) varredura.rotation.y = angulo = -0.6;
  figura.append(canvas, selo, dica);
  figura.classList.add("radar--3d");
  medir();
  pedirQuadro();
}

if (figura) iniciar();
