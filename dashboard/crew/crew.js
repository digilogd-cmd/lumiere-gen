// 로봇 작업반(crew) 공용 부품 — "SYSTEM UPGRADE" 장면에서 떼어 낸 것(2026-10-06).
// 같은 콘셉트의 다른 모션 그래픽(점검 중·준비 중·오류 화면 등)을 만들 때 이 부품을 그대로 가져다 쓴다.
// 그리는 원칙: 외부 라이브러리 없이 Canvas 2D, 화면은 "시간 t의 순수 함수"(같은 t면 같은 그림).
// 색: 검정 배경 위에 종이색(PAPER) 로봇 + 금색(GOLD) 포인트 + 회색/강철색 기계. 사람은 커서(DAVID 금색·HARA 흰색)로만 등장.
//
//  로봇: drawRobot(ctx, p) — 원점은 두 발 사이 바닥(앉은 로봇은 엉덩이). p: { x, y, s, face, crouch, hop, lean, walk, sit, legsOut,
//        look:[lx,ly], eyes:'normal'|'happy'|'sad'|'sleep', blink, wide, headTilt, headDy, ant, hat:'hard'|'phones'|'band'|'mask', maskUp, maskGlow,
//        armA/armB: { w:[화면x,y] } 또는 { l:[어깨에서 dx,dy] }, stretch:true(안 닿으면 팔이 늘어남), bendA/bendB, led }
//  자세 계산 도우미: shoulderOf(p, side) · headOf(p) · lookAt(p, x, y)
//  소품: drawWrench · drawBolt · drawLadder · drawCandle · drawCone · drawBug · drawVacuum · drawSticky · drawCursor
//  시간 도우미: win(t,a,b,fade) 구간 봉투 · pulse(t,t0,d) 봉우리 · wobble(t,t0,freq,decay) 흔들림 · keyed([[t,v],…],t) 키프레임
//  그리기 도우미: limb(팔다리 선) · plate(둥근 판) · dot · glow · label(글자, tracking 지원) · joint(두 마디 관절)

import { TAU, BRAND, FONT_MONO, font, clamp, ease, roundRectPath } from './core.js';

export const GOLD = BRAND.gold;
export const GOLD_RGB = '243,156,18';
export const PAPER = '#f2f0ea';
export const INK = '#0a0a0a';
export const STEEL = '#151515';
export const STEEL_LINE = '#3f3f3f';
export const METAL = '#bdbdbd';
export const GRAY = '#8c8c8c';

// ───────── 작은 도구 ─────────
export const rad = (d) => (d * Math.PI) / 180;
export const mix = (a, b, u) => a + (b - a) * u;
export const mixPt = (a, b, u) => [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u];
export const sm = (x) => {
  const u = clamp(x);
  return u * u * (3 - 2 * u);
};
/** a~b 구간에서만 1 (양 끝은 f초 동안 부드럽게) */
export const win = (t, a, b, f = 0.2) => (t <= a || t >= b ? 0 : sm(Math.min(1, (t - a) / f, (b - t) / f)));
/** t0에 시작해 한 번 솟았다 꺼지는 봉우리 */
export const pulse = (t, t0, d) => {
  const u = (t - t0) / d;
  return u > 0 && u < 1 ? Math.sin(Math.PI * u) : 0;
};
/** t0에 한 번 치면 흔들리다 잦아든다 */
export const wobble = (t, t0, freq, decay) => (t > t0 ? Math.sin((t - t0) * TAU * freq) * Math.exp(-(t - t0) * decay) : 0);
/** [시각, 값] 표를 따라 부드럽게 잇는다 */
export function keyed(keys, t, fn = ease.inOutSine) {
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    if (t <= keys[i][0]) {
      const u = (t - keys[i - 1][0]) / (keys[i][0] - keys[i - 1][0]);
      return mix(keys[i - 1][1], keys[i][1], fn(u));
    }
  }
  return keys[keys.length - 1][1];
}

export function limb(ctx, x1, y1, x2, y2, w, color) {
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.strokeStyle = INK;
  ctx.lineWidth = w + 2.6;
  ctx.stroke();
  ctx.strokeStyle = color;
  ctx.lineWidth = w;
  ctx.stroke();
}

export function plate(ctx, x, y, w, h, r, fill, stroke = INK, lw = 1.5) {
  roundRectPath(ctx, x, y, w, h, r);
  ctx.fillStyle = fill;
  ctx.fill();
  if (stroke) {
    ctx.strokeStyle = stroke;
    ctx.lineWidth = lw;
    ctx.stroke();
  }
}

export function dot(ctx, x, y, r, fill) {
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fillStyle = fill;
  ctx.fill();
}

export function glow(ctx, x, y, r, rgb, a) {
  if (a <= 0.004) return;
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, `rgba(${rgb},${a})`);
  g.addColorStop(1, `rgba(${rgb},0)`);
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fill();
}

export function label(ctx, str, x, y, o = {}) {
  const { size = 10, weight = 600, family = FONT_MONO, color = '#fff', align = 'left', tracking = 0, alpha = 1 } = o;
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.font = font(weight, size, family);
  ctx.fillStyle = color;
  ctx.textBaseline = 'middle';
  if (!tracking) {
    ctx.textAlign = align;
    ctx.fillText(str, x, y);
    ctx.restore();
    return;
  }
  const chars = Array.from(str);
  const sp = tracking * size;
  const ws = chars.map((c) => ctx.measureText(c).width);
  const total = ws.reduce((a, b) => a + b, 0) + sp * (chars.length - 1);
  let cx = align === 'center' ? x - total / 2 : align === 'right' ? x - total : x;
  ctx.textAlign = 'left';
  chars.forEach((c, i) => {
    ctx.fillText(c, cx, y);
    cx += ws[i] + sp;
  });
  ctx.restore();
}

/** 두 마디 팔·다리의 관절 위치 */
export function joint(sx, sy, tx, ty, l1, l2, bend) {
  const dx = tx - sx;
  const dy = ty - sy;
  const d = Math.max(0.001, Math.hypot(dx, dy));
  const a = (l1 * l1 - l2 * l2 + d * d) / (2 * d);
  const h = Math.sqrt(Math.max(0, l1 * l1 - a * a));
  return [sx + (dx * a) / d - (bend * h * dy) / d, sy + (dy * a) / d + (bend * h * dx) / d];
}

// ───────── 로봇 ─────────
export const RB = { bodyW: 34, bodyH: 30, headW: 30, headH: 22, leg: 19, arm1: 15, arm2: 15 };

export const hipOf = (p) => (p.sit ? 0 : -(RB.leg - (p.crouch || 0) * 9));

/** 어깨의 화면 위치 (side: 1 = 바라보는 쪽, -1 = 반대쪽) */
export function shoulderOf(p, side) {
  const face = p.face || 1;
  return [p.x + 14 * side * p.s * face, p.y - (p.hop || 0) * p.s + (hipOf(p) - RB.bodyH + 9) * p.s];
}
/** 머리 가운데의 화면 위치(대략) */
export const headOf = (p) => [p.x, p.y - (p.hop || 0) * p.s + (hipOf(p) - RB.bodyH - 3 - RB.headH / 2) * p.s];

/** 로봇 눈이 (wx,wy)를 보게 하는 값 */
export function lookAt(p, wx, wy) {
  const h = headOf(p);
  const dx = (wx - h[0]) * (p.face || 1);
  const dy = wy - h[1];
  const d = Math.max(30, Math.hypot(dx, dy));
  return [clamp(dx / d, -1, 1), clamp(dy / d, -1, 1)];
}

/**
 * 로봇 한 대. 원점 = 두 발 사이의 바닥(앉은 로봇은 엉덩이).
 * 팔 목표: { w: [화면 x, y] } 또는 { l: [어깨에서 dx, dy] }, stretch: true면 닿지 않을 때 팔이 늘어난다.
 */
export function drawRobot(ctx, p) {
  const s = p.s || 1;
  const face = p.face || 1;
  const hipY = hipOf(p);
  const lean = p.lean || 0;
  const ox = p.x;
  const oy = p.y - (p.hop || 0) * s;

  ctx.save();
  ctx.translate(ox, oy);
  ctx.scale(s * face, s);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  const toBody = (wx, wy) => {
    const x = (wx - ox) / (s * face);
    const y = (wy - oy) / s - hipY;
    const c = Math.cos(-lean);
    const sn = Math.sin(-lean);
    return [x * c - y * sn, hipY + x * sn + y * c];
  };

  const foot = (fx, fy) => plate(ctx, fx - 6.5, fy - 5.5, 13, 5.5, 2.6, PAPER);

  // 다리
  if (p.sit) {
    for (const hx of [-6, 6]) {
      if (p.legsOut) {
        // 바닥에 앉아 다리를 뻗음
        limb(ctx, hx, hipY - 2, hx + 21, hipY - 2, 5.2, PAPER);
        plate(ctx, hx + 20, hipY - 9.5, 5.5, 10, 2.4, PAPER);
      } else {
        const sw = (p.kick || 0) * (hx > 0 ? 1 : -1);
        const kx = hx + 12;
        limb(ctx, hx, hipY - 2, kx, hipY - 0.5, 5.2, PAPER);
        limb(ctx, kx, hipY - 0.5, kx + sw * 3, hipY + 12, 5.2, PAPER);
        foot(kx + sw * 3 + 2.5, hipY + 15);
      }
    }
  } else {
    [-1, 1].forEach((sd, i) => {
      let fx = sd * 8;
      let fy = 0;
      if (p.walk !== undefined) {
        const ph = p.walk + (i ? Math.PI : 0);
        fx = sd * 3 + Math.cos(ph) * 7.5;
        fy = -Math.max(0, Math.sin(ph)) * 4.5;
      }
      const hx = sd * 6;
      const k = joint(hx, hipY, fx, fy - 4, 10.6, 10.6, -1);
      limb(ctx, hx, hipY, k[0], k[1], 5.2, PAPER);
      limb(ctx, k[0], k[1], fx, fy - 4, 5.2, PAPER);
      foot(fx + 1.5, fy);
    });
  }

  // 윗몸(엉덩이를 축으로 기운다)
  ctx.translate(0, hipY);
  ctx.rotate(lean);
  ctx.translate(0, -hipY);
  const bodyTop = hipY - RB.bodyH;
  const shY = bodyTop + 9;

  const arm = (sx, spec, bend) => {
    let tx;
    let ty;
    if (spec.w) [tx, ty] = toBody(spec.w[0], spec.w[1]);
    else {
      tx = sx + spec.l[0];
      ty = shY + spec.l[1];
    }
    const d = Math.max(0.001, Math.hypot(tx - sx, ty - shY));
    const reach = RB.arm1 + RB.arm2 - 0.6;
    let hx = tx;
    let hy = ty;
    if (d > reach) {
      const ux = (tx - sx) / d;
      const uy = (ty - shY) / d;
      const ex = sx + ux * RB.arm1;
      const ey = shY + uy * RB.arm1;
      limb(ctx, sx, shY, ex, ey, 5.4, PAPER);
      if (spec.stretch) {
        // 닿지 않으면 팔이 늘어난다(피스톤)
        const mx = sx + ux * reach * 0.9;
        const my = shY + uy * reach * 0.9;
        limb(ctx, mx, my, hx, hy, 2.4, METAL);
        limb(ctx, ex, ey, mx, my, 5.4, PAPER);
      } else {
        hx = sx + ux * reach;
        hy = shY + uy * reach;
        limb(ctx, ex, ey, hx, hy, 5.4, PAPER);
      }
    } else {
      const e = joint(sx, shY, tx, ty, RB.arm1, RB.arm2, bend);
      limb(ctx, sx, shY, e[0], e[1], 5.4, PAPER);
      limb(ctx, e[0], e[1], hx, hy, 5.4, PAPER);
    }
    dot(ctx, hx, hy, 4.1, PAPER);
    dot(ctx, hx, hy, 2.5, INK);
  };

  if (p.armB) arm(-14, p.armB, p.bendB || 1);

  // 몸통
  plate(ctx, -RB.bodyW / 2, bodyTop, RB.bodyW, RB.bodyH, 9, PAPER);
  roundRectPath(ctx, -8.5, bodyTop + 11, 17, 9.5, 3.2);
  ctx.fillStyle = INK;
  ctx.fill();
  dot(ctx, -4, bodyTop + 15.75, 1.7, p.led === undefined ? GOLD : p.led);
  ctx.strokeStyle = '#5a5a5a';
  ctx.lineWidth = 1.3;
  ctx.beginPath();
  ctx.moveTo(0.5, bodyTop + 15.75);
  ctx.lineTo(5.5, bodyTop + 15.75);
  ctx.stroke();

  // 머리
  ctx.save();
  ctx.translate(0, bodyTop - 2.5);
  ctx.rotate(p.headTilt || 0);
  ctx.translate(0, p.headDy || 0);
  ctx.fillStyle = INK;
  ctx.fillRect(-4.5, -2, 9, 6);
  const hy0 = -RB.headH - 0.5;
  // 안테나
  const aw = p.ant || 0;
  const ax = Math.sin(aw) * 9;
  const ay = hy0 - Math.cos(aw) * 9;
  ctx.strokeStyle = PAPER;
  ctx.lineWidth = 1.7;
  ctx.beginPath();
  ctx.moveTo(0, hy0 + 1);
  ctx.lineTo(ax, ay);
  ctx.stroke();
  dot(ctx, ax, ay, 2.7, GOLD);
  plate(ctx, -RB.headW / 2, hy0, RB.headW, RB.headH, 8, PAPER);
  // 얼굴창
  roundRectPath(ctx, -11.5, hy0 + 5, 23, 12, 5.2);
  ctx.fillStyle = INK;
  ctx.fill();
  // 눈
  const lk = p.look || [0, 0];
  const mood = p.eyes || 'normal';
  for (const sd of [-1, 1]) {
    const ex = sd * 5.2 + lk[0] * 2.3;
    const ey = hy0 + 11 + lk[1] * 1.7;
    ctx.strokeStyle = GOLD;
    ctx.fillStyle = GOLD;
    ctx.lineWidth = 1.7;
    if (mood === 'happy') {
      ctx.beginPath();
      ctx.arc(ex, ey + 1.6, 2.7, Math.PI * 1.12, Math.PI * 1.88);
      ctx.stroke();
    } else if (mood === 'sad') {
      ctx.beginPath();
      ctx.moveTo(ex - sd * 2.5, ey - 0.9);
      ctx.lineTo(ex + sd * 2.5, ey + 1.1);
      ctx.stroke();
    } else if (mood === 'sleep') {
      ctx.beginPath();
      ctx.arc(ex, ey - 0.6, 2.5, Math.PI * 0.15, Math.PI * 0.85);
      ctx.stroke();
    } else {
      const open = 1 - (p.blink || 0);
      const r = 2.3 * (1 + 0.38 * (p.wide || 0));
      ctx.beginPath();
      ctx.ellipse(ex, ey, r, Math.max(0.35, r * open), 0, 0, TAU);
      ctx.fill();
    }
  }
  // 머리에 쓴 것
  if (p.hat === 'hard') {
    ctx.fillStyle = GOLD;
    ctx.beginPath();
    ctx.ellipse(0, hy0 + 4.5, 15.6, 11.5, 0, Math.PI, 0);
    ctx.closePath();
    ctx.fill();
    roundRectPath(ctx, -18.5, hy0 + 2.6, 37, 3.6, 1.8);
    ctx.fill();
    ctx.strokeStyle = 'rgba(0,0,0,0.28)';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(0, hy0 - 6.5);
    ctx.lineTo(0, hy0 + 2.6);
    ctx.stroke();
  } else if (p.hat === 'phones') {
    ctx.strokeStyle = METAL;
    ctx.lineWidth = 2.4;
    ctx.beginPath();
    ctx.arc(0, hy0 + 10, 17.6, Math.PI * 1.1, Math.PI * 1.9);
    ctx.stroke();
    for (const sd of [-1, 1]) plate(ctx, sd * 17 - 3, hy0 + 5.5, 6, 11, 2.6, GOLD);
  } else if (p.hat === 'band') {
    ctx.fillStyle = GOLD;
    ctx.fillRect(-RB.headW / 2 + 0.8, hy0 + 1.6, RB.headW - 1.6, 2.8);
  } else if (p.hat === 'mask') {
    // 용접면: 내리면 얼굴을 덮고, 올리면 이마 위로 젖혀져 납작하게 보인다
    const up = p.maskUp || 0;
    ctx.save();
    ctx.translate(0, hy0 + 3 - 13.5 * up);
    ctx.rotate(-0.16 * up);
    ctx.scale(1, 1 - 0.5 * up);
    plate(ctx, -14, -3, 28, 21, 6.5, '#1b1b1b', METAL, 1.2);
    ctx.fillStyle = `rgba(${GOLD_RGB},${0.35 + 0.65 * (p.maskGlow || 0)})`;
    roundRectPath(ctx, -8.5, 4.5, 17, 4, 1.6);
    ctx.fill();
    ctx.restore();
  }
  ctx.restore();

  if (p.armA) arm(14, p.armA, p.bendA || -1);
  ctx.restore();
}

// ───────── 소품 ─────────
/** 렌치: 손(hx,hy)에서 ang 방향으로 len */
export function drawWrench(ctx, hx, hy, ang, len, k) {
  ctx.save();
  ctx.translate(hx, hy);
  ctx.rotate(ang);
  limb(ctx, -3 * k, 0, len - 5.5 * k, 0, 3.6 * k, METAL);
  ctx.lineCap = 'butt';
  ctx.beginPath();
  ctx.arc(len, 0, 5.6 * k, rad(42), rad(318));
  ctx.strokeStyle = INK;
  ctx.lineWidth = 5.8 * k;
  ctx.stroke();
  ctx.strokeStyle = METAL;
  ctx.lineWidth = 3.4 * k;
  ctx.stroke();
  ctx.restore();
}

export function drawBolt(ctx, x, y, rot, k) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rot);
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * TAU;
    if (i) ctx.lineTo(Math.cos(a) * 5.2 * k, Math.sin(a) * 5.2 * k);
    else ctx.moveTo(5.2 * k, 0);
  }
  ctx.closePath();
  ctx.fillStyle = METAL;
  ctx.fill();
  ctx.strokeStyle = INK;
  ctx.lineWidth = 1.2;
  ctx.stroke();
  dot(ctx, 0, 0, 1.8 * k, '#6b6b6b');
  ctx.restore();
}

export function drawLadder(ctx, cx, top, floor, half, spread) {
  const x0 = cx - spread;
  const x1 = cx + spread;
  ctx.lineCap = 'round';
  const rail = (ax, ay, bx, by, w) => {
    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(bx, by);
    ctx.strokeStyle = INK;
    ctx.lineWidth = w + 2.4;
    ctx.stroke();
    ctx.strokeStyle = GRAY;
    ctx.lineWidth = w;
    ctx.stroke();
  };
  rail(cx - half, top, x0, floor, 2.8);
  rail(cx + half, top, x1, floor, 2.8);
  for (const u of [0.36, 0.68]) {
    rail(mix(cx - half, x0, u), mix(top, floor, u), mix(cx + half, x1, u), mix(top, floor, u), 2.2);
  }
  rail(cx - half - 4, top, cx + half + 4, top, 3.6);
}

export function drawCandle(ctx, cx, cy, len, thick, ang) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(ang);
  ctx.strokeStyle = GRAY;
  ctx.lineWidth = 2;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(-len / 2 - len * 0.28, 0);
  ctx.lineTo(len / 2 + len * 0.2, 0);
  ctx.stroke();
  plate(ctx, -len / 2, -thick / 2, len, thick, 3, PAPER);
  ctx.restore();
}

export function drawCone(ctx, x, y, k) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(k, k);
  plate(ctx, -13, -4, 26, 4, 1.5, GOLD);
  ctx.beginPath();
  ctx.moveTo(-8.5, -4);
  ctx.lineTo(-2.6, -27);
  ctx.lineTo(2.6, -27);
  ctx.lineTo(8.5, -4);
  ctx.closePath();
  ctx.fillStyle = GOLD;
  ctx.fill();
  ctx.strokeStyle = INK;
  ctx.lineWidth = 1.4;
  ctx.stroke();
  ctx.fillStyle = PAPER;
  ctx.beginPath();
  ctx.moveTo(-6.3, -12.5);
  ctx.lineTo(-4.9, -18);
  ctx.lineTo(4.9, -18);
  ctx.lineTo(6.3, -12.5);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

export function drawBug(ctx, x, y, k, wig) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(k, k);
  ctx.strokeStyle = GRAY;
  ctx.lineWidth = 1.1;
  ctx.lineCap = 'round';
  for (let i = -1; i <= 1; i++) {
    const w = Math.sin(wig + i * 1.7) * 1.4;
    ctx.beginPath();
    ctx.moveTo(i * 2.6, -2.5);
    ctx.lineTo(i * 3.6 + w, -6.2);
    ctx.moveTo(i * 2.6, -2.5);
    ctx.lineTo(i * 3.6 - w, 0.6);
    ctx.stroke();
  }
  ctx.beginPath();
  ctx.ellipse(0, -2.8, 4.6, 3.1, 0, 0, TAU);
  ctx.fillStyle = GRAY;
  ctx.fill();
  dot(ctx, 4.6, -3.1, 1.9, '#b5b5b5');
  ctx.restore();
}

/** 청소 로봇(옆모습 원반). dir: 1 오른쪽 / -1 왼쪽으로 달리는 중 */
export function drawVacuum(ctx, x, y, k, dir, t, o = {}) {
  ctx.save();
  ctx.translate(x, y - (o.hop || 0));
  ctx.scale(k * dir, k);
  ctx.rotate(o.tilt || 0);
  // 빨아들이는 바람
  if (o.suck > 0.02) {
    ctx.strokeStyle = `rgba(255,255,255,${0.35 * o.suck})`;
    ctx.lineWidth = 1.2;
    ctx.lineCap = 'round';
    for (let i = 0; i < 3; i++) {
      const u = (t * 2.6 + i / 3) % 1;
      ctx.beginPath();
      ctx.moveTo(40 - u * 14, -3 - i * 3.2);
      ctx.lineTo(34 - u * 14, -3 - i * 3.2);
      ctx.stroke();
    }
  }
  dot(ctx, -13, -2.2, 2.6, '#2b2b2b');
  dot(ctx, 12, -2.2, 2.6, '#2b2b2b');
  // 눈 달린 윗부분
  plate(ctx, -9, -19, 20, 9, 4.5, '#1c1c1c', METAL, 1.1);
  const bl = o.blink ? 0.3 : 1;
  ctx.fillStyle = GOLD;
  ctx.beginPath();
  ctx.ellipse(3, -14.5, 1.7, 1.7 * bl, 0, 0, TAU);
  ctx.ellipse(8, -14.5, 1.7, 1.7 * bl, 0, 0, TAU);
  ctx.fill();
  plate(ctx, -23, -13, 46, 11, 5.5, PAPER);
  roundRectPath(ctx, 14, -11, 8, 7, 3);
  ctx.fillStyle = INK;
  ctx.fill();
  ctx.fillStyle = GOLD;
  ctx.fillRect(-17, -8.6, 22, 1.8);
  ctx.restore();
}

export function drawSticky(ctx, x, y, rot, k, fill, word) {
  if (k <= 0.01) return;
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rot);
  ctx.scale(k, k);
  ctx.shadowColor = 'rgba(0,0,0,0.5)';
  ctx.shadowBlur = 6;
  ctx.shadowOffsetY = 2;
  ctx.fillStyle = fill;
  ctx.fillRect(-15, -15, 30, 30);
  ctx.shadowColor = 'transparent';
  ctx.fillStyle = 'rgba(0,0,0,0.16)';
  ctx.beginPath();
  ctx.moveTo(15, 6);
  ctx.lineTo(15, 15);
  ctx.lineTo(6, 15);
  ctx.closePath();
  ctx.fill();
  label(ctx, word, 0, -4.5, { size: 8, weight: 700, color: INK, align: 'center', tracking: 0.06 });
  ctx.fillStyle = 'rgba(0,0,0,0.5)';
  ctx.fillRect(-9, 3, 18, 1.4);
  ctx.fillRect(-9, 7, 12, 1.4);
  ctx.restore();
}

/** 사람 커서(홈의 '한 도형'과 같은 모양) */
export function drawCursor(ctx, x, y, who, press, k) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(k * (1 - 0.16 * press), k * (1 - 0.16 * press));
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(0, 17.5);
  ctx.lineTo(4.8, 13.2);
  ctx.lineTo(8, 20.2);
  ctx.lineTo(10.9, 18.9);
  ctx.lineTo(7.8, 12.1);
  ctx.lineTo(13.8, 12.1);
  ctx.closePath();
  ctx.fillStyle = who === 0 ? GOLD : '#ffffff';
  ctx.strokeStyle = INK;
  ctx.lineWidth = 1.4;
  ctx.lineJoin = 'round';
  ctx.shadowColor = 'rgba(0,0,0,0.4)';
  ctx.shadowBlur = 6;
  ctx.shadowOffsetY = 2;
  ctx.fill();
  ctx.shadowColor = 'transparent';
  ctx.stroke();
  const name = who === 0 ? 'DAVID' : 'HARA';
  ctx.font = font(700, 9.5, FONT_MONO);
  const tw = ctx.measureText(name).width + name.length * 0.95;
  roundRectPath(ctx, 12, 20, tw + 14, 17, 8.5);
  ctx.fillStyle = who === 0 ? GOLD : '#ffffff';
  ctx.fill();
  ctx.lineWidth = 1;
  ctx.strokeStyle = 'rgba(0,0,0,0.5)';
  ctx.stroke();
  label(ctx, name, 19, 29, { size: 9.5, weight: 700, color: INK, tracking: 0.1 });
  ctx.restore();
}

