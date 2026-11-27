// 편집팀 대시보드 가운데 화면 — "로봇 편집 스튜디오" 공용 무대와 소품.
// 아트고메 로봇 작업반(crew) 가족: 검정 바탕 + 종이색 로봇 + 금색 포인트, Canvas 2D, 화면 = 시간 t의 순수 함수.
// 편집 대시보드에는 사람(DAVID·HARA 커서)이 나오지 않는다 — 로봇들이 알아서 받아쓰고·자르고·고치고·편집한다.
// 무대(모든 단계 공통): 매달린 단계 간판(왼쪽 위) · 카운터 보드(오른쪽 위) · 천장에 매단 편집 모니터(가운데)
//                     · 감독 의자(오른쪽) · 바닥선 · 맨 아래 금색 필름 띠(경고 테이프 대신 편집실 표식).

import { TAU, FONT_DISPLAY, FONT_BODY, FONT_MONO, font, clamp, ease, roundRectPath } from './core.js';
import { GOLD, GOLD_RGB, PAPER, INK, STEEL, STEEL_LINE, METAL, GRAY, rad, mix, limb, plate, dot, glow, label } from './crew.js';

export const VW = 960;
export const VH = 540;
export const F = 446; // 바닥
export const MON = { x: 318, y: 92, w: 324, h: 190 };
export const SCR = { x: MON.x + 12, y: MON.y + 12, w: MON.w - 24, h: MON.h - 34 };
export const CHAIR = { x: 800 }; // 바닥 무대 1.25배 확대 후 화면 x ≈ 880
export const SEAT = F - 36;

// ───────── 무대 ─────────
export function drawBackdrop(ctx) {
  ctx.fillStyle = '#050505';
  ctx.fillRect(0, 0, VW, VH);
  // 아주 옅은 바닥 반사
  const g = ctx.createLinearGradient(0, F - 120, 0, F);
  g.addColorStop(0, 'rgba(255,255,255,0)');
  g.addColorStop(1, 'rgba(255,255,255,0.025)');
  ctx.fillStyle = g;
  ctx.fillRect(0, F - 120, VW, 120);
  ctx.strokeStyle = '#2a2a2a';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(18, F + 1);
  ctx.lineTo(VW - 18, F + 1);
  ctx.stroke();
}

/** 매달린 단계 간판: no(1~13) · 영문 태그 · 한국어 이름 */
export function drawSign(ctx, t, no, tag, ko) {
  const x = 40, y = 30, w = 312, h = 64;
  const sway = Math.sin(t * 1.1) * 0.006;
  ctx.save();
  ctx.translate(x + w / 2, 0);
  ctx.rotate(sway);
  ctx.translate(-(x + w / 2), 0);
  ctx.strokeStyle = STEEL_LINE;
  ctx.lineWidth = 1.4;
  for (const cx of [x + 30, x + w - 30]) {
    ctx.beginPath();
    ctx.moveTo(cx, 0);
    ctx.lineTo(cx, y);
    ctx.stroke();
  }
  plate(ctx, x, y, w, h, 8, '#0d0d0d', `rgba(${GOLD_RGB},0.85)`, 1.6);
  // 단계 번호 칩
  plate(ctx, x + 12, y + 12, 40, 40, 7, GOLD, null);
  label(ctx, no ? String(no).padStart(2, '0') : 'AI', x + 32, y + 33, { size: 19, weight: 800, family: FONT_DISPLAY, color: INK, align: 'center' });
  label(ctx, tag, x + 66, y + 24, { size: 15, weight: 800, family: FONT_DISPLAY, color: '#fff', tracking: 0.14 });
  label(ctx, ko, x + 66, y + 46, { size: 13.5, weight: 600, family: FONT_BODY, color: GRAY });
  ctx.restore();
}

/** 오른쪽 위 카운터 보드 */
export function drawBoard(ctx, t, name, value) {
  const x = 762, y = 36, w = 158, h = 56;
  plate(ctx, x, y, w, h, 8, '#0d0d0d', STEEL_LINE, 1.2);
  label(ctx, name, x + w / 2, y + 16, { size: 9, weight: 700, color: GRAY, align: 'center', tracking: 0.22 });
  label(ctx, value, x + w / 2, y + 37, { size: 22, weight: 700, family: FONT_DISPLAY, color: GOLD, align: 'center', tracking: 0.08 });
  dot(ctx, x + w - 12, y + 12, 2.6, `rgba(${GOLD_RGB},${0.4 + 0.6 * (0.5 + 0.5 * Math.sin(t * 4))})`);
}

/** 천장에 매단 편집 모니터. inner(ctx, rect)로 화면 속을 그린다. img가 있으면 실제 편집 화면을 흐리게 깐다 */
export function drawMonitor(ctx, t, inner, img, onAir = 1) {
  const { x, y, w, h } = MON;
  ctx.strokeStyle = STEEL_LINE;
  ctx.lineWidth = 2;
  for (const cx of [x + 46, x + w - 46]) {
    ctx.beginPath();
    ctx.moveTo(cx, 0);
    ctx.lineTo(cx, y);
    ctx.stroke();
  }
  glow(ctx, x + w / 2, y + h / 2, w * 0.62, GOLD_RGB, 0.05 * onAir);
  plate(ctx, x, y, w, h, 12, STEEL, STEEL_LINE, 1.6);
  const r = SCR;
  ctx.save();
  roundRectPath(ctx, r.x, r.y, r.w, r.h, 6);
  ctx.clip();
  ctx.fillStyle = '#020202';
  ctx.fillRect(r.x, r.y, r.w, r.h);
  if (img && img.complete && img.naturalWidth) {
    ctx.globalAlpha = 0.28;
    const k = Math.max(r.w / img.naturalWidth, r.h / img.naturalHeight);
    const iw = img.naturalWidth * k, ih = img.naturalHeight * k;
    ctx.drawImage(img, r.x + (r.w - iw) / 2, r.y + (r.h - ih) / 2, iw, ih);
    ctx.globalAlpha = 1;
  }
  inner(ctx, r);
  // 주사선
  ctx.fillStyle = 'rgba(255,255,255,0.025)';
  for (let yy = r.y; yy < r.y + r.h; yy += 3) ctx.fillRect(r.x, yy, r.w, 1);
  ctx.restore();
  // 아래 턱: REC 점 + 라벨
  const blink = (Math.floor(t * 2) % 2) * onAir;
  dot(ctx, x + 22, y + h - 11, 3, blink ? '#ff3b30' : '#3a1210');
  label(ctx, 'GEN · PGM', x + 32, y + h - 11, { size: 8.5, weight: 700, color: GRAY, tracking: 0.2 });
  label(ctx, 'LUMIÈRE GEN', x + w - 16, y + h - 11, { size: 8.5, weight: 700, color: '#555', align: 'right', tracking: 0.2 });
}

/** 감독 의자(등판에 DIRECTOR) */
export function drawChair(ctx, x = CHAIR.x) {
  ctx.lineCap = 'round';
  const leg = (ax, ay, bx, by) => limb(ctx, ax, ay, bx, by, 3, '#6a5330');
  leg(x - 24, SEAT, x + 22, F - 2);
  leg(x + 24, SEAT, x - 22, F - 2);
  plate(ctx, x - 30, SEAT - 4, 60, 8, 3, '#3a2c16', INK, 1.2);
  limb(ctx, x + 24, SEAT, x + 24, SEAT - 52, 3, '#6a5330');
  limb(ctx, x - 24, SEAT, x - 24, SEAT - 52, 3, '#6a5330');
  plate(ctx, x - 30, SEAT - 58, 60, 18, 3, '#1a1a1a', GOLD, 1.2);
  label(ctx, 'DIRECTOR', x, SEAT - 49, { size: 8.5, weight: 800, color: GOLD, align: 'center', tracking: 0.2 });
}

/** 맨 아래 금색 필름 띠(천천히 흐른다) */
export function drawFilmStrip(ctx, t, speed = 18) {
  const y = 500, h = 26;
  ctx.fillStyle = '#0f0c06';
  ctx.fillRect(0, y, VW, h);
  ctx.strokeStyle = `rgba(${GOLD_RGB},0.55)`;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, y + 0.5);
  ctx.lineTo(VW, y + 0.5);
  ctx.moveTo(0, y + h - 0.5);
  ctx.lineTo(VW, y + h - 0.5);
  ctx.stroke();
  const step = 22;
  const off = (t * speed) % step;
  ctx.fillStyle = `rgba(${GOLD_RGB},0.75)`;
  for (let xx = -step + off; xx < VW + step; xx += step) {
    roundRectPath(ctx, xx, y + 4, 9, 5, 1.5);
    ctx.fill();
    roundRectPath(ctx, xx, y + h - 9, 9, 5, 1.5);
    ctx.fill();
  }
  // 프레임 구분선
  ctx.strokeStyle = `rgba(${GOLD_RGB},0.18)`;
  const fs = 110;
  for (let xx = -fs + ((t * speed) % fs); xx < VW + fs; xx += fs) {
    ctx.beginPath();
    ctx.moveTo(xx, y + 11);
    ctx.lineTo(xx, y + h - 11);
    ctx.stroke();
  }
}

/** 말풍선(가운데 아래 꼬리). a: 0~1 */
export function bubble(ctx, x, y, text, a, tailX = 0, size = 14) {
  if (a <= 0.01) return;
  ctx.save();
  ctx.globalAlpha *= a;
  ctx.font = font(700, size, FONT_BODY);
  const w = ctx.measureText(text).width + 26;
  const h = size + 18;
  const bx = x - w / 2, by = y - h - 9;
  const sc = 0.85 + 0.15 * ease.outCubic(clamp(a));
  ctx.translate(x, y);
  ctx.scale(sc, sc);
  ctx.translate(-x, -y);
  plate(ctx, bx, by, w, h, h / 2, PAPER, INK, 1.4);
  ctx.beginPath();
  ctx.moveTo(x + tailX - 6, by + h - 1);
  ctx.lineTo(x + tailX, y);
  ctx.lineTo(x + tailX + 6, by + h - 1);
  ctx.closePath();
  ctx.fillStyle = PAPER;
  ctx.fill();
  label(ctx, text, x, by + h / 2 + 0.5, { size, weight: 700, family: FONT_BODY, color: INK, align: 'center' });
  ctx.restore();
}

export function zzz(ctx, x, y, t) {
  for (let i = 0; i < 3; i++) {
    const u = (t * 0.5 + i / 3) % 1;
    label(ctx, 'z', x + u * 16, y - u * 26, { size: 9 + u * 7, weight: 700, family: FONT_DISPLAY, color: GRAY, alpha: 1 - u });
  }
}

/** 반짝(불꽃·완료 표시) */
export function sparkle(ctx, x, y, r, a, rot = 0) {
  if (a <= 0.01) return;
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rot);
  ctx.strokeStyle = `rgba(${GOLD_RGB},${a})`;
  ctx.lineWidth = 2;
  ctx.lineCap = 'round';
  for (let i = 0; i < 4; i++) {
    const an = (i / 4) * TAU;
    ctx.beginPath();
    ctx.moveTo(Math.cos(an) * r * 0.35, Math.sin(an) * r * 0.35);
    ctx.lineTo(Math.cos(an) * r, Math.sin(an) * r);
    ctx.stroke();
  }
  ctx.restore();
  glow(ctx, x, y, r * 1.6, GOLD_RGB, 0.35 * a);
}

// ───────── 소품 ─────────
/** 슬레이트(딱따구리). 손잡이 = (hx,hy), open: 0 닫힘 ~ 1 열림 */
export function drawClapper(ctx, hx, hy, ang, open, k = 1) {
  ctx.save();
  ctx.translate(hx, hy);
  ctx.rotate(ang);
  ctx.scale(k, k);
  plate(ctx, -2, -4, 40, 26, 3, '#161616', PAPER, 1.4);
  label(ctx, 'SCENE', 4, 6, { size: 6.5, weight: 700, color: GRAY, tracking: 0.15 });
  label(ctx, 'TAKE 1', 4, 14, { size: 6.5, weight: 700, color: GRAY, tracking: 0.1 });
  // 윗막대(힌지 = 왼쪽 위)
  ctx.save();
  ctx.translate(-2, -4);
  ctx.rotate(-open * 0.7);
  plate(ctx, 0, -7, 40, 7, 1.5, PAPER, INK, 1.2);
  ctx.fillStyle = INK;
  for (let i = 0; i < 4; i++) {
    ctx.beginPath();
    ctx.moveTo(4 + i * 10, -7);
    ctx.lineTo(9 + i * 10, -7);
    ctx.lineTo(5 + i * 10, 0);
    ctx.lineTo(0 + i * 10, 0);
    ctx.closePath();
    ctx.fill();
  }
  ctx.restore();
  ctx.restore();
}

/** 메가폰: 손잡이(hx,hy)에서 ang 방향 */
export function drawMegaphone(ctx, hx, hy, ang, k = 1) {
  ctx.save();
  ctx.translate(hx, hy);
  ctx.rotate(ang);
  ctx.scale(k, k);
  ctx.beginPath();
  ctx.moveTo(0, -4);
  ctx.lineTo(24, -11);
  ctx.lineTo(24, 11);
  ctx.lineTo(0, 4);
  ctx.closePath();
  ctx.fillStyle = GOLD;
  ctx.fill();
  ctx.strokeStyle = INK;
  ctx.lineWidth = 1.4;
  ctx.stroke();
  plate(ctx, 22, -12, 4, 24, 1.5, PAPER, INK, 1);
  ctx.restore();
}

/** 책상(+ 노트북) */
export function drawDesk(ctx, x, w, top = F - 40) {
  limb(ctx, x + 6, top + 4, x + 6, F - 1, 3, '#3a3a3a');
  limb(ctx, x + w - 6, top + 4, x + w - 6, F - 1, 3, '#3a3a3a');
  plate(ctx, x, top - 4, w, 8, 3, '#2a2a2a', INK, 1.2);
}

export function drawLaptop(ctx, x, y, k, glowA = 0.8, lines = 0) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(k, k);
  plate(ctx, -18, -3, 36, 4, 1.5, METAL, INK, 1);
  ctx.save();
  ctx.translate(-14, -3);
  ctx.rotate(-0.22);
  plate(ctx, 0, -22, 28, 22, 2.5, '#1a1a1a', METAL, 1);
  ctx.fillStyle = `rgba(${GOLD_RGB},${0.25 * glowA})`;
  ctx.fillRect(3, -19, 22, 16);
  ctx.fillStyle = `rgba(242,240,234,${0.7 * glowA})`;
  for (let i = 0; i < Math.min(4, lines); i++) ctx.fillRect(5, -16 + i * 3.6, 8 + ((i * 7) % 11), 1.6);
  ctx.restore();
  ctx.restore();
}

export function drawSpeaker(ctx, x, y, k, beat) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(k, k);
  plate(ctx, -15, -44, 30, 44, 5, '#141414', STEEL_LINE, 1.3);
  dot(ctx, 0, -30, 8 + beat * 1.5, '#2a2a2a');
  dot(ctx, 0, -30, 3.5, GOLD);
  dot(ctx, 0, -12, 5, '#2a2a2a');
  ctx.restore();
  // 소리 물결
  for (let i = 0; i < 3; i++) {
    const a = 0.5 * beat * (1 - i / 3);
    if (a < 0.02) continue;
    ctx.strokeStyle = `rgba(${GOLD_RGB},${a})`;
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.arc(x + 4 * k, y - 30 * k, (18 + i * 9 + beat * 4) * k, -0.6, 0.6);
    ctx.stroke();
  }
}

/** 큰 돋보기: 손(hx,hy)에서 ang 방향으로 손잡이, 끝에 렌즈 */
export function drawMagnifier(ctx, hx, hy, ang, k = 1, shine = 0) {
  ctx.save();
  ctx.translate(hx, hy);
  ctx.rotate(ang);
  ctx.scale(k, k);
  limb(ctx, -2, 0, 22, 0, 4.2, '#6a5330');
  const lx = 38;
  glow(ctx, lx, 0, 22, GOLD_RGB, 0.12 + 0.3 * shine);
  ctx.beginPath();
  ctx.arc(lx, 0, 15, 0, TAU);
  ctx.fillStyle = `rgba(242,240,234,${0.08 + 0.1 * shine})`;
  ctx.fill();
  ctx.lineWidth = 5.4;
  ctx.strokeStyle = INK;
  ctx.stroke();
  ctx.lineWidth = 3.4;
  ctx.strokeStyle = METAL;
  ctx.stroke();
  ctx.strokeStyle = 'rgba(255,255,255,0.6)';
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.arc(lx, 0, 9, rad(200), rad(250));
  ctx.stroke();
  ctx.restore();
}

/** 가위: 손잡이 끝(hx,hy), open 0~1 */
export function drawScissors(ctx, hx, hy, ang, open, k = 1) {
  ctx.save();
  ctx.translate(hx, hy);
  ctx.rotate(ang);
  ctx.scale(k, k);
  for (const sd of [-1, 1]) {
    ctx.save();
    ctx.translate(12, 0);
    ctx.rotate(sd * open * 0.35);
    limb(ctx, 0, 0, 22, 0, 3, METAL);
    ctx.restore();
    ctx.beginPath();
    ctx.ellipse(2, sd * 4, 5, 3.4, 0, 0, TAU);
    ctx.strokeStyle = INK;
    ctx.lineWidth = 4.2;
    ctx.stroke();
    ctx.strokeStyle = GOLD;
    ctx.lineWidth = 2.4;
    ctx.stroke();
  }
  dot(ctx, 12, 0, 1.8, INK);
  ctx.restore();
}

/** 종이 한 장(대본·초안) */
export function drawPaper(ctx, x, y, rot, k = 1, word = '', crumple = 0) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rot);
  ctx.scale(k, k);
  if (crumple > 0.5) {
    ctx.beginPath();
    for (let i = 0; i < 9; i++) {
      const a = (i / 9) * TAU;
      const r = 7 + ((i * 37) % 5) * 0.6;
      if (i) ctx.lineTo(Math.cos(a) * r, Math.sin(a) * r);
      else ctx.moveTo(r, 0);
    }
    ctx.closePath();
    ctx.fillStyle = PAPER;
    ctx.fill();
    ctx.strokeStyle = INK;
    ctx.lineWidth = 1.2;
    ctx.stroke();
    ctx.strokeStyle = 'rgba(0,0,0,0.35)';
    ctx.beginPath();
    ctx.moveTo(-4, -2);
    ctx.lineTo(2, 3);
    ctx.moveTo(1, -4);
    ctx.lineTo(4, 1);
    ctx.stroke();
  } else {
    plate(ctx, -13, -17, 26, 34, 2, PAPER, INK, 1.1);
    ctx.fillStyle = 'rgba(0,0,0,0.42)';
    for (let i = 0; i < 5; i++) ctx.fillRect(-8, -10 + i * 5, 10 + ((i * 5) % 7), 1.6);
    if (word) label(ctx, word, 0, -13 + 0, { size: 6.5, weight: 800, color: GOLD, align: 'center' });
  }
  ctx.restore();
}

export function drawBin(ctx, x, y, k, word) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(k, k);
  ctx.beginPath();
  ctx.moveTo(-17, -34);
  ctx.lineTo(17, -34);
  ctx.lineTo(13, 0);
  ctx.lineTo(-13, 0);
  ctx.closePath();
  ctx.fillStyle = '#1c1c1c';
  ctx.fill();
  ctx.strokeStyle = STEEL_LINE;
  ctx.lineWidth = 1.4;
  ctx.stroke();
  plate(ctx, -19, -38, 38, 5, 2, '#2a2a2a', INK, 1);
  if (word) label(ctx, word, 0, -17, { size: 8, weight: 800, color: GOLD, align: 'center', tracking: 0.12 });
  ctx.restore();
}

/** 스프레이 캔: 손(hx,hy), 노즐이 ang 방향 */
export function drawSpray(ctx, hx, hy, ang, k = 1) {
  ctx.save();
  ctx.translate(hx, hy);
  ctx.rotate(ang);
  ctx.scale(k, k);
  plate(ctx, -6, -6, 22, 12, 4, METAL, INK, 1.2);
  plate(ctx, 16, -3, 5, 6, 1.5, GOLD, INK, 1);
  ctx.fillStyle = GOLD;
  ctx.fillRect(0, -6, 3, 12);
  ctx.restore();
}

/** 필름 조각(가편 구간 하나) */
export function drawChunk(ctx, x, y, w, h, rot = 0, lit = 0) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rot);
  plate(ctx, -w / 2, -h / 2, w, h, 3, '#1a1408', `rgba(${GOLD_RGB},${0.55 + 0.45 * lit})`, 1.3);
  ctx.fillStyle = `rgba(${GOLD_RGB},0.7)`;
  for (let i = 0; i < Math.floor(w / 9); i++) {
    ctx.fillRect(-w / 2 + 3 + i * 9, -h / 2 + 2, 4, 3);
    ctx.fillRect(-w / 2 + 3 + i * 9, h / 2 - 5, 4, 3);
  }
  ctx.fillStyle = `rgba(242,240,234,${0.18 + 0.4 * lit})`;
  ctx.fillRect(-w / 2 + 4, -h / 2 + 7, w - 8, h - 14);
  ctx.restore();
}

/** 도장: 손잡이 위(hx,hy) */
export function drawStamp(ctx, hx, hy, k = 1) {
  ctx.save();
  ctx.translate(hx, hy);
  ctx.scale(k, k);
  dot(ctx, 0, 0, 5, '#6a5330');
  limb(ctx, 0, 3, 0, 12, 4, '#6a5330');
  plate(ctx, -10, 12, 20, 7, 2, GOLD, INK, 1.2);
  ctx.restore();
}

/** 들고 있는 팻말: 막대 아래 끝(hx,hy) */
export function drawPlacard(ctx, hx, hy, text, k = 1, rot = 0) {
  ctx.save();
  ctx.translate(hx, hy);
  ctx.rotate(rot);
  ctx.scale(k, k);
  limb(ctx, 0, 0, 0, -46, 3, '#6a5330');
  ctx.font = font(800, 12, FONT_BODY);
  const w = ctx.measureText(text).width + 22;
  plate(ctx, -w / 2, -80, w, 34, 5, PAPER, INK, 1.4);
  label(ctx, text, 0, -63, { size: 12, weight: 800, family: FONT_BODY, color: INK, align: 'center' });
  ctx.restore();
}

export function drawBell(ctx, x, y, k, ring) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(k, k);
  ctx.rotate(Math.sin(ring * 30) * 0.15 * ring);
  plate(ctx, -11, -2, 22, 4, 2, '#3a3a3a', INK, 1);
  ctx.beginPath();
  ctx.arc(0, -2, 9, Math.PI, 0);
  ctx.fillStyle = GOLD;
  ctx.fill();
  ctx.strokeStyle = INK;
  ctx.lineWidth = 1.2;
  ctx.stroke();
  dot(ctx, 0, -12, 2.4, GOLD);
  ctx.restore();
  if (ring > 0.05) {
    for (const sd of [-1, 1]) {
      ctx.strokeStyle = `rgba(${GOLD_RGB},${ring})`;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(x, y - 8 * k, 16 * k, sd > 0 ? -0.9 : Math.PI - 0.4, sd > 0 ? -0.4 : Math.PI + 0.1 + 0.8);
      ctx.stroke();
    }
  }
}

/** 낱글자 타일(받아쓰기·버벅임) */
export function drawTile(ctx, x, y, ch, k = 1, hot = 0, rot = 0) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rot);
  ctx.scale(k, k);
  plate(ctx, -10, -10, 20, 20, 4, hot ? GOLD : PAPER, INK, 1.2);
  label(ctx, ch, 0, 0.5, { size: 12, weight: 800, family: FONT_BODY, color: INK, align: 'center' });
  ctx.restore();
}

/** 음표 */
export function drawNote(ctx, x, y, a, k = 1) {
  if (a <= 0.01) return;
  ctx.save();
  ctx.globalAlpha *= a;
  ctx.translate(x, y);
  ctx.scale(k, k);
  ctx.strokeStyle = GOLD;
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  ctx.moveTo(4, 0);
  ctx.lineTo(4, -14);
  ctx.lineTo(10, -11);
  ctx.stroke();
  ctx.beginPath();
  ctx.ellipse(0, 0, 4.5, 3.4, -0.4, 0, TAU);
  ctx.fillStyle = GOLD;
  ctx.fill();
  ctx.restore();
}

/** 화면 속 파형 한 줄 */
export function wave(ctx, x, y, w, amp, seed, t, off = 0, color = PAPER, spikeAt = -1) {
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  for (let i = 0; i <= w; i += 3) {
    const u = i + off;
    let v = Math.sin(u * 0.21 + seed) * 0.5 + Math.sin(u * 0.057 + seed * 2) * 0.4 + Math.sin(u * 0.9 + seed) * 0.15;
    v *= 0.5 + 0.5 * Math.abs(Math.sin(u * 0.031 + seed));
    if (spikeAt >= 0 && Math.abs(u - spikeAt) < 5) v = (u - spikeAt) % 2 ? 1.6 : -1.6;
    ctx.moveTo(x + i, y - v * amp);
    ctx.lineTo(x + i, y + v * amp);
  }
  ctx.stroke();
}
