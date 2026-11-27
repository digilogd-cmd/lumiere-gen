// 편집 단계 장면 ⑨~⑬ + 대기·완료: 중간 점검 · 종편 · 제목·설명 · 마무리 보고 · 업로드 · STANDBY · WRAP (각 8초 반복)
import { TAU, FONT_BODY, FONT_DISPLAY, clamp, ease, hash, roundRectPath } from './core.js';
import { GOLD, GOLD_RGB, PAPER, INK, STEEL, STEEL_LINE, METAL, GRAY, rad, mix, mixPt, sm, win, pulse, wobble, keyed, limb, plate, dot, glow, label, drawRobot, drawLadder, drawVacuum, drawSticky } from './crew.js';
import { F, SCR, CHAIR, SEAT, bubble, sparkle, zzz, drawDesk, drawPaper, drawBin, drawStamp, drawPlacard, drawBell, drawSpeaker, drawNote } from './editcrew_set.js';
import { L, R, blinkAt, director } from './editcrew_scenes1.js';

const ZF = 1.25;
const toFloor = (p) => [480 + (p[0] - 480) / ZF, F + (p[1] - F) / ZF];
const mmss = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

// ─────────────────────────────────────────────── ⑨ 중간 점검
export const CHECKPOINT = {
  id: 'checkpoint', no: 9, tag: 'CHECKPOINT', ko: '중간 점검',
  caps: [
    { from: 0, tag: 'HOLD', text: '브라우저 작업 대기 — 그림·영상·목소리·음악을 받아 올 차례' },
    { from: 3.2, tag: 'VOICE', text: 'Claude 창에 "생성 작업 해 줘"라고 말해 주세요' },
    { from: 5.0, tag: 'AWAKE', text: '기다리다 조는 로봇도 있습니다' },
  ],
  board: (t, S) => ['WAITING', mmss(S.lap * L + t)],
  screen(ctx, r, t) {
    const p = 0.6 + 0.4 * Math.sin(t * 3);
    glow(ctx, r.x + r.w / 2, r.y + r.h / 2 - 8, 60, GOLD_RGB, 0.18 * p);
    ctx.beginPath();
    ctx.moveTo(r.x + r.w / 2 - 14, r.y + r.h / 2 - 30);
    ctx.lineTo(r.x + r.w / 2 + 20, r.y + r.h / 2 - 8);
    ctx.lineTo(r.x + r.w / 2 - 14, r.y + r.h / 2 + 14);
    ctx.closePath();
    ctx.fillStyle = `rgba(${GOLD_RGB},${0.6 + 0.4 * p})`;
    ctx.fill();
    label(ctx, '브라우저 작업 대기', r.x + r.w / 2, r.y + r.h - 30, { size: 13, weight: 800, family: FONT_BODY, color: PAPER, align: 'center' });
    label(ctx, '그림 · 영상 · 목소리 · 음악', r.x + r.w / 2, r.y + r.h - 12, { size: 9, color: GRAY, align: 'center', tracking: 0.1 });
  },
  draw(ctx, t) {
    // 팻말 로봇(헤드폰)
    const ax = 290;
    const lift = 0.5 + 0.5 * Math.sin(t * 2.2);
    const ah = [ax + 22, F - 66 - lift * 4];
    drawRobot(ctx, R(ax, 1.2, 1, { hat: 'phones', blink: blinkAt(t, 51), armA: { w: ah }, armB: { l: [-6, 16] }, look: [0, 0.1], hop: lift * 1.5 }));
    drawPlacard(ctx, ah[0], ah[1], '확인해 주세요', 1, 0.04 * Math.sin(t * 2.2));
    // 발 구르는 로봇(안전모)
    const bx = 410;
    const nudge = pulse(t, 4.8, 0.6);
    const tap = Math.max(0, Math.sin(t * 9)) * (t < 4.6 || t > 5.6 ? 1 : 0);
    drawRobot(ctx, R(bx, 1.2, 1, {
      hat: 'hard', blink: blinkAt(t, 52), armA: { l: [10 + nudge * 26, 10 - nudge * 6] }, armB: { l: [-8, 16] },
      look: nudge > 0.1 ? [1, 0] : [0.2, 0.1], hop: tap * 1.5, lean: 0.2 * nudge,
    }));
    // 조는 로봇(용접면 올림)
    const cx = 520;
    const asleep = t > 1.4 && t < 4.95;
    const jolt = pulse(t, 4.95, 0.5);
    drawRobot(ctx, R(cx, 1.2, -1, {
      hat: 'mask', maskUp: 1, blink: asleep ? 0 : blinkAt(t, 53), eyes: asleep ? 'sleep' : 'normal', wide: jolt, hop: jolt * 8,
      headTilt: asleep ? 0.18 : 0, headDy: asleep ? 2 : 0, armA: { l: [6, 18] }, armB: { l: [-6, 18] }, ant: wobble(t, 4.95, 5, 3) * 0.7,
    }));
    if (asleep) zzz(ctx, cx + 10, F - 112, t);
    // 감독: 종을 친다
    const bell = [CHAIR.x - 40, F - 48];
    plate(ctx, bell[0] - 16, F - 46, 32, 6, 2, '#2a2a2a', INK, 1);
    limb(ctx, bell[0], F - 40, bell[0], F - 1, 3, '#3a3a3a');
    const ding = Math.max(pulse(t, 1.0, 0.25), pulse(t, 4.4, 0.25));
    drawBell(ctx, bell[0], bell[1], 1.1, Math.max(wobble(t, 1.05, 3, 4) > 0 ? clamp(1 - (t - 1.05)) : 0, wobble(t, 4.45, 3, 4) > 0 ? clamp(1 - (t - 4.45)) : 0));
    director(ctx, t, { hand: [bell[0] + 2, bell[1] - 16 + ding * 6], look: [0.3, 0.2], say: '띵—', sayA: win(t, 1.0, 1.8, 0.12) + win(t, 4.4, 5.2, 0.12) });
  },
};

// ─────────────────────────────────────────────── ⑩ 종편
export const FINAL = {
  id: 'final', no: 10, tag: 'FINAL CUT', ko: '종편',
  caps: [
    { from: 0, tag: 'SUBS', text: '자막을 내리는 중' },
    { from: 2.1, tag: 'TILT', text: '삐뚤어졌습니다. 바로잡았습니다' },
    { from: 3.9, tag: 'MOTION', text: '모션 그래픽 쾅' },
    { from: 5.3, tag: 'MIX', text: '소리 크기 -11 LUFS로 맞춤' },
  ],
  board: (t) => ['LUFS', keyed([[0, -14.2], [5.0, -14.2], [6.2, -11.0], [7.6, -11.0], [7.95, -14.2]], t).toFixed(1)],
  screen(ctx, r, t) {
    const fade = 1 - win(t, 7.55, 9, 0.3);
    // 자막 막대(크레인으로 내려와 앉음)
    const down = keyed([[0, 0], [0.4, 0], [2.0, 1]], t, ease.outCubic);
    const tilt = keyed([[0, 0.28], [2.6, 0.28], [2.8, 0]], t) + wobble(t, 2.75, 4, 6) * 0.08;
    const by = mix(r.y - 30, r.y + r.h - 26, down);
    ctx.save();
    ctx.globalAlpha *= fade;
    ctx.translate(r.x + r.w / 2, by);
    ctx.rotate(tilt);
    plate(ctx, -96, -11, 192, 22, 5, 'rgba(0,0,0,0.75)', null);
    label(ctx, '이 한 문장으로 다 됐습니다', 0, 0.5, { size: 12, weight: 700, family: FONT_BODY, color: PAPER, align: 'center' });
    ctx.restore();
    // 모션 그래픽 스티커
    const st = keyed([[0, 0], [4.15, 0], [4.35, 1.2], [4.5, 1]], t) * fade;
    if (st > 0) {
      ctx.save();
      ctx.translate(r.x + 74, r.y + 52);
      ctx.rotate(-0.12);
      ctx.scale(st, st);
      ctx.beginPath();
      for (let i = 0; i < 20; i++) {
        const a = (i / 20) * TAU, rr = i % 2 ? 22 : 34;
        if (i) ctx.lineTo(Math.cos(a) * rr * 1.5, Math.sin(a) * rr);
        else ctx.moveTo(rr * 1.5, 0);
      }
      ctx.closePath();
      ctx.fillStyle = GOLD;
      ctx.fill();
      ctx.strokeStyle = INK;
      ctx.lineWidth = 2;
      ctx.stroke();
      label(ctx, '쾅!', 0, 1, { size: 18, weight: 900, family: FONT_DISPLAY, color: INK, align: 'center' });
      ctx.restore();
    }
  },
  draw(ctx, t) {
    // 크레인 줄(천장에서 자막 막대까지)
    const down = keyed([[0, 0], [0.4, 0], [2.0, 1]], t, ease.outCubic);
    const up = win(t, 2.2, 9, 0.2);
    const barTop = toFloor([SCR.x + SCR.w / 2, mix(SCR.y - 40, SCR.y + SCR.h - 38, down)]);
    if (up < 0.99 || t < 2.2) {
      ctx.strokeStyle = METAL;
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.moveTo(barTop[0], 60);
      ctx.lineTo(barTop[0], mix(barTop[1], 60, t > 2.2 ? clamp((t - 2.2) / 0.8) : 0));
      ctx.stroke();
    }
    // 사다리 로봇(안전모): 지시봉으로 막대를 바로잡고, 스티커를 붙인다
    const lad = { cx: 262, top: 372 };
    drawLadder(ctx, lad.cx, lad.top, F, 20, 34);
    const fix = pulse(t, 2.45, 0.5);
    const slap = pulse(t, 3.95, 0.55);
    const barFix = toFloor([SCR.x + SCR.w / 2 - 60, SCR.y + SCR.h - 30]);
    const stick = toFloor([SCR.x + 74, SCR.y + 52]);
    let hand = [lad.cx + 30, lad.top - 50];
    hand = mixPt(hand, barFix, fix);
    hand = mixPt(hand, stick, slap);
    drawRobot(ctx, R(lad.cx, 1.2, 1, {
      y: lad.top, hat: 'hard', blink: blinkAt(t, 61), armA: { w: hand, stretch: true }, armB: { l: [-4, 20] }, look: [0.6, -0.9],
      eyes: t > 4.4 && t < 5.6 ? 'happy' : 'normal',
    }));
    if (slap > 0.05 && t < 4.3) {
      ctx.save();
      ctx.translate(hand[0], hand[1]);
      plate(ctx, -10, -8, 20, 16, 4, GOLD, INK, 1.2);
      ctx.restore();
    }
    // 믹서 로봇(헤드폰) + 스피커
    const mx = 560;
    plate(ctx, mx + 20, F - 44, 70, 44, 6, '#141414', STEEL_LINE, 1.3);
    const lv = keyed([[0, -14.2], [5.0, -14.2], [6.2, -11.0], [7.6, -11.0], [7.95, -14.2]], t);
    label(ctx, `${lv.toFixed(1)} LUFS`, mx + 55, F - 30, { size: 9, weight: 800, color: lv > -11.5 ? GOLD : GRAY, align: 'center' });
    for (let i = 0; i < 3; i++) {
      const fy = F - 14 - (0.5 + 0.5 * Math.sin(t * 2 + i)) * 6 * (t > 5 && t < 6.3 ? 1 : 0.3);
      limb(ctx, mx + 34 + i * 14, F - 20, mx + 34 + i * 14, F - 8, 2, '#333');
      plate(ctx, mx + 30 + i * 14, fy - 2, 8, 5, 2, METAL, INK, 1);
    }
    const knob = t > 5.0 && t < 6.3;
    drawRobot(ctx, R(mx, 1.2, 1, {
      hat: 'phones', blink: blinkAt(t, 62), armA: { w: [mx + 48 + (knob ? Math.sin(t * 10) * 3 : 0), F - 50] }, armB: { l: [-6, 16] },
      look: [0.6, 0.6], eyes: t > 6.3 && t < 7.4 ? 'happy' : 'normal',
    }));
    const beat = 0.5 + 0.5 * Math.sin(t * 8);
    drawSpeaker(ctx, 700, F, 1.1, beat);
    for (let i = 0; i < 4; i++) {
      const u = (t * 0.5 + i / 4) % 1;
      drawNote(ctx, 700 - u * 40 + Math.sin(u * 8 + i) * 8, F - 60 - u * 70, Math.sin(u * Math.PI), 1);
    }
    director(ctx, t, {
      say: t < 3.5 ? '삐뚤어!' : '좋아, 그대로!', sayA: win(t, 2.0, 2.7, 0.12) + win(t, 5.6, 7.0, 0.15), mega: win(t, 1.9, 2.8, 0.15),
      eyes: t > 5.6 && t < 7.0 ? 'happy' : 'normal',
    });
  },
};

// ─────────────────────────────────────────────── ⑪ 제목·설명·목차
const BALLS = [1.6, 3.4, 5.2];
export const META = {
  id: 'meta', no: 11, tag: 'TITLES', ko: '제목·설명·목차',
  caps: [
    { from: 0, tag: 'TITLE', text: '제목 세 가지를 쓰는 중' },
    { from: 2.0, tag: 'DRAFT', text: '버린 초안은 셀 수 없습니다' },
    { from: 5.8, tag: 'PICK', text: '썸네일 글자는 크게, 한 곳만 강조' },
  ],
  board: (t, S) => ['DRAFTS', String(37 + S.lap * 3 + BALLS.filter((b) => t > b).length).padStart(4, '0')],
  screen(ctx, r, t) {
    label(ctx, 'TITLES · A/B', r.x + 10, r.y + 14, { size: 8, color: GRAY, tracking: 0.18 });
    ['A', 'B', 'C'].forEach((k, i) => {
      const y = r.y + 40 + i * 32;
      const u = clamp((t - i * 1.6) / 1.6);
      plate(ctx, r.x + 12, y - 10, 20, 20, 4, i === 1 && t > 6.2 ? GOLD : '#1d1d1d', STEEL_LINE, 1);
      label(ctx, k, r.x + 22, y, { size: 11, weight: 800, color: i === 1 && t > 6.2 ? INK : PAPER, align: 'center' });
      ctx.fillStyle = 'rgba(242,240,234,0.55)';
      ctx.fillRect(r.x + 42, y - 3, (150 + i * 30) * u, 6);
    });
  },
  draw(ctx, t) {
    // 쓰레기통 + 종이 뭉치
    const bin = [150, F];
    drawBin(ctx, bin[0], bin[1], 1.15, 'DRAFT');
    // 책상과 쓰는 로봇(헤드폰)
    drawDesk(ctx, 196, 110);
    drawPaper(ctx, 250, F - 52, -0.1, 1, '');
    const wx = 330;
    let toss = 0;
    BALLS.forEach((b) => { toss = Math.max(toss, pulse(t, b - 0.3, 0.5)); });
    const wr = Math.sin(t * 18) * 3 * (1 - toss);
    const wh = mixPt([262 + wr, F - 50], [wx - 10, F - 96], toss);
    drawRobot(ctx, R(wx, 1.2, -1, { hat: 'phones', blink: blinkAt(t, 71), armA: { w: wh }, armB: { l: [-6, 16] }, look: toss > 0.2 ? [1, -0.6] : [0.6, 0.8], lean: 0.08 }));
    limb(ctx, wh[0], wh[1], wh[0] - 6, wh[1] + 10, 2, GOLD);
    BALLS.forEach((b, i) => {
      const u = (t - b) / 0.75;
      const miss = i === 2;
      const end = miss ? [186, F - 6] : [bin[0], F - 40];
      if (u < 0) return;
      if (u > 1) {
        if (miss) drawPaper(ctx, end[0], end[1], 0, 1, '', 1);
        return;
      }
      const p = mixPt([wx - 14, F - 104], end, u);
      drawPaper(ctx, p[0], p[1] - Math.sin(u * Math.PI) * 50, u * 8, 1, '', 1);
    });
    // 이젤과 칠하는 로봇(안전모)
    const ez = { x: 470, y: F - 118, w: 112, h: 63 };
    limb(ctx, ez.x + 20, ez.y + ez.h, ez.x + 6, F - 1, 3, '#6a5330');
    limb(ctx, ez.x + ez.w - 20, ez.y + ez.h, ez.x + ez.w - 6, F - 1, 3, '#6a5330');
    plate(ctx, ez.x, ez.y, ez.w, ez.h, 3, '#0e0e0e', PAPER, 1.6);
    const b1 = keyed([[0, 0], [2.0, 0], [3.0, 1], [7.5, 1], [7.9, 0]], t);
    const b2 = keyed([[0, 0], [3.2, 0], [4.2, 1], [7.5, 1], [7.9, 0]], t);
    plate(ctx, ez.x + 8, ez.y + 12, 64 * b1, 12, 2, PAPER, null);
    plate(ctx, ez.x + 8, ez.y + 30, 80 * b2, 16, 2, GOLD, null);
    if (t > 4.4 && t < 7.6) plate(ctx, ez.x + 6, ez.y + ez.h - 12, 9, 9, 2, PAPER, null);
    const px = 620;
    const painting = t > 2.0 && t < 4.4;
    const target = t < 3.1 ? [ez.x + 8 + 64 * b1, ez.y + 18] : [ez.x + 8 + 80 * b2, ez.y + 38];
    const ph = painting ? target : [px - 26, F - 46];
    drawRobot(ctx, R(px, 1.2, -1, {
      hat: 'hard', blink: blinkAt(t, 72), armA: { w: ph, stretch: true }, armB: { l: [-6, 16] }, look: painting ? [0.8, -0.4] : [0.4, 0.2],
      eyes: t > 4.4 && t < 6 ? 'happy' : 'normal',
    }));
    limb(ctx, ph[0], ph[1], ph[0] + 12, ph[1] + 6, 2.4, '#6a5330');
    dot(ctx, ph[0] - 1, ph[1] - 1, 3, t < 3.1 ? PAPER : GOLD);
    director(ctx, t, { say: 'B안으로!', sayA: win(t, 6.0, 7.3, 0.15), mega: win(t, 5.9, 7.2, 0.2) });
  },
};

// ─────────────────────────────────────────────── ⑫ 마무리 보고
const CRATES = [[190, '자막'], [270, '소리'], [350, '줌'], [430, '모션'], [510, '썸네일']];
const CHECK_AT = [1.0, 2.0, 3.7, 4.5, 5.3];
export const REPORT = {
  id: 'report', no: 12, tag: 'REPORT', ko: '마무리 보고',
  caps: [
    { from: 0, tag: 'CHECK', text: 'SOP 검문소 — 하나씩 재 봅니다' },
    { from: 2.8, tag: 'HMM', text: '이건 다시 한 번 봅니다' },
    { from: 6.0, tag: 'PASS', text: '도장 쾅 — 보고서를 남깁니다' },
  ],
  board: (t) => ['SOP', `${String(CHECK_AT.filter((c) => t > c).length * 4 - (t > 5.3 ? 1 : 0)).padStart(2, '0')}/19`],
  screen(ctx, r, t) {
    label(ctx, 'SOP CHECKPOINT', r.x + 10, r.y + 14, { size: 8, color: GRAY, tracking: 0.18 });
    CRATES.forEach(([, k], i) => {
      const y = r.y + 30 + i * 20;
      const ok = t > CHECK_AT[i] && t < 7.7;
      label(ctx, ok ? '✓' : i === 2 && t > 2.8 && t < 3.7 ? '?' : '·', r.x + 16, y + 3, { size: 12, weight: 800, color: ok ? GOLD : GRAY });
      label(ctx, k, r.x + 34, y + 3, { size: 11, weight: 700, family: FONT_BODY, color: ok ? PAPER : GRAY });
    });
    if (t > 6.2 && t < 7.7) label(ctx, 'PASS', r.x + r.w - 20, r.y + r.h - 24, { size: 22, weight: 800, family: FONT_DISPLAY, color: GOLD, align: 'right', tracking: 0.1 });
  },
  draw(ctx, t) {
    CRATES.forEach(([x, k], i) => {
      plate(ctx, x - 24, F - 34, 48, 34, 4, '#1f1a10', `rgba(${GOLD_RGB},0.55)`, 1.2);
      label(ctx, k, x, F - 17, { size: 10, weight: 700, family: FONT_BODY, color: PAPER, align: 'center' });
      const ok = pulse(t, CHECK_AT[i], 0.5) > 0 || (t > CHECK_AT[i] && t < 7.7);
      if (ok) {
        const pop = 1 + pulse(t, CHECK_AT[i], 0.35) * 0.4;
        label(ctx, '✓', x, F - 52, { size: 18 * pop, weight: 900, color: GOLD, align: 'center' });
      }
      if (i === 2 && t > 2.8 && t < 3.7) label(ctx, '?', x, F - 52, { size: 18, weight: 900, color: GRAY, align: 'center' });
    });
    // 검사 로봇(안전모, 클립보드)
    const ix = keyed([[0, 60], [0.7, 150], [1.2, 150], [1.6, 230], [2.3, 230], [2.7, 310], [3.9, 310], [4.2, 390], [4.8, 390], [5.1, 470], [5.6, 470], [7.9, 930]], t);
    const walking = Math.abs(keyed([[0, 60], [0.7, 150], [1.2, 150], [1.6, 230], [2.3, 230], [2.7, 310], [3.9, 310], [4.2, 390], [4.8, 390], [5.1, 470], [5.6, 470], [7.9, 930]], t + 0.05) - ix) > 0.5;
    const squint = win(t, 2.8, 3.7, 0.15);
    const ih = [ix + 24, F - 62];
    drawRobot(ctx, R(ix, 1.2, 1, {
      hat: 'hard', blink: blinkAt(t, 81), armA: { w: ih }, armB: { l: [6, 14] }, walk: walking ? t * 15 : undefined,
      look: [0.8, 0.8], lean: 0.18 * squint, wide: squint,
    }));
    plate(ctx, ih[0] - 2, ih[1] - 22, 20, 26, 2, '#6a5330', INK, 1);
    plate(ctx, ih[0] + 1, ih[1] - 18, 14, 18, 1, PAPER, null);
    // 도장 로봇(헤드폰) + 책상
    drawDesk(ctx, 610, 80);
    drawPaper(ctx, 650, F - 52, 0, 1.05, '');
    const sd = pulse(t, 6.0, 0.45);
    const sh = [650, F - 84 + sd * 22];
    drawRobot(ctx, R(694, 1.2, -1, { hat: 'phones', blink: blinkAt(t, 82), armA: { w: sh }, armB: { l: [-6, 16] }, look: [0.6, 0.8], eyes: t > 6.3 && t < 7.6 ? 'happy' : 'normal' }));
    drawStamp(ctx, sh[0], sh[1] - 2, 1.15);
    if (t > 6.15 && t < 7.7) {
      ctx.save();
      ctx.translate(650, F - 54);
      ctx.rotate(-0.15);
      plate(ctx, -14, -7, 28, 14, 2, 'rgba(0,0,0,0)', GOLD, 1.6);
      label(ctx, 'PASS', 0, 0, { size: 8, weight: 900, color: GOLD, align: 'center' });
      ctx.restore();
    }
    sparkle(ctx, 650, F - 60, 20, pulse(t, 6.1, 0.5));
    director(ctx, t, { eyes: t > 6.2 && t < 7.6 ? 'happy' : 'normal', nod: pulse(t, 6.3, 0.4) });
  },
};

// ─────────────────────────────────────────────── ⑬ 업로드
export const UPLOAD = {
  id: 'upload', no: 13, tag: 'UPLOAD', ko: '업로드',
  caps: [
    { from: 0, tag: 'READY', text: '올릴 준비 끝' },
    { from: 2.0, tag: 'WAIT', text: '업로드는 사람이 말할 때만' },
    { from: 4.6, tag: 'HOLD', text: '대기 쪽지를 붙여 둡니다' },
  ],
  board: () => ['UPLOAD', 'HOLD'],
  screen(ctx, r, t) {
    label(ctx, 'READY TO UPLOAD', r.x + r.w / 2, r.y + 30, { size: 11, weight: 800, color: GOLD, align: 'center', tracking: 0.2 });
    ctx.strokeStyle = `rgba(242,240,234,${0.35 + 0.2 * Math.sin(t * 3)})`;
    ctx.lineWidth = 4;
    ctx.lineCap = 'round';
    const cx = r.x + r.w / 2, cy = r.y + 78;
    ctx.beginPath();
    ctx.moveTo(cx, cy + 18);
    ctx.lineTo(cx, cy - 18);
    ctx.moveTo(cx - 14, cy - 4);
    ctx.lineTo(cx, cy - 18);
    ctx.lineTo(cx + 14, cy - 4);
    ctx.stroke();
    label(ctx, '말씀하실 때 올립니다', cx, r.y + r.h - 22, { size: 12, weight: 700, family: FONT_BODY, color: PAPER, align: 'center' });
  },
  draw(ctx, t) {
    // 로켓(필름 통) + 발사대
    const rx = 440;
    const shake = win(t, 1.8, 2.6, 0.1) * Math.sin(t * 60) * 1.6;
    plate(ctx, rx - 34, F - 10, 68, 10, 3, '#2a2a2a', INK, 1.2);
    ctx.save();
    ctx.translate(rx + shake, F - 10);
    ctx.beginPath();
    ctx.moveTo(-18, -24);
    ctx.lineTo(-30, 0);
    ctx.lineTo(-14, 0);
    ctx.closePath();
    ctx.moveTo(18, -24);
    ctx.lineTo(30, 0);
    ctx.lineTo(14, 0);
    ctx.closePath();
    ctx.fillStyle = GOLD;
    ctx.fill();
    plate(ctx, -18, -96, 36, 92, 10, PAPER, INK, 1.4);
    ctx.fillStyle = GOLD;
    ctx.fillRect(-18, -64, 36, 6);
    ctx.fillRect(-18, -40, 36, 6);
    ctx.beginPath();
    ctx.moveTo(-18, -94);
    ctx.quadraticCurveTo(0, -132, 18, -94);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = INK;
    ctx.lineWidth = 1.4;
    ctx.stroke();
    dot(ctx, 0, -78, 7, INK);
    dot(ctx, 0, -78, 4, `rgba(${GOLD_RGB},0.8)`);
    ctx.restore();
    const puff = win(t, 1.9, 2.8, 0.15);
    for (let i = 0; i < 6; i++) {
      const u = ((t * 1.8 + i / 6) % 1);
      dot(ctx, rx + (hash(i) - 0.5) * 50 * u, F - 4 - u * 10, 5 + u * 9, `rgba(160,160,160,${0.35 * puff * (1 - u)})`);
    }
    // 쪽지
    const note = keyed([[0, 0], [4.7, 0], [5.0, 1], [7.5, 1], [7.9, 0]], t);
    drawSticky(ctx, rx + 4, F - 60, -0.12, note, '#f2d36b', 'WAIT');
    // 발사 버튼 콘솔 + 로봇(안전모)
    const bx = 560;
    plate(ctx, bx, F - 46, 56, 46, 6, '#141414', STEEL_LINE, 1.3);
    dot(ctx, bx + 28, F - 48, 10, '#2a2a2a');
    dot(ctx, bx + 28, F - 50, 8, '#b5651d');
    label(ctx, 'LAUNCH', bx + 28, F - 14, { size: 7.5, color: GRAY, align: 'center', tracking: 0.2 });
    const rxw = keyed([[0, 650], [3.8, 650], [4.4, 500], [5.4, 500], [6.2, 650]], t);
    const reach = keyed([[0, 0], [1.2, 0], [2.1, 1], [2.9, 1], [3.3, 0]], t);
    const stick = win(t, 4.5, 5.3, 0.15);
    const walking = win(t, 3.8, 4.4, 0.05) + win(t, 5.4, 6.2, 0.05);
    let hand = mixPt([rxw - 20, F - 40], [bx + 30, F - 64], reach);
    if (stick > 0) hand = mixPt(hand, [rx + 4 + 12, F - 64], stick);
    const sad = t > 2.9 && t < 4.0;
    drawRobot(ctx, R(rxw, 1.2, -1, {
      hat: 'hard', blink: blinkAt(t, 91), armA: { w: hand }, armB: { l: [-6, 16] }, walk: walking > 0.1 ? t * 15 : undefined,
      look: reach > 0.5 && t > 2.2 ? [-0.2, -0.4] : [0.6, 0.6], eyes: sad ? 'sad' : t > 5.3 && t < 6.6 ? 'happy' : 'normal',
      wide: win(t, 2.15, 2.9, 0.1), face: t > 5.4 && t < 6.2 ? 1 : -1,
    }));
    director(ctx, t, { say: '잠깐! 말씀하실 때!', sayA: win(t, 2.0, 3.6, 0.15), mega: win(t, 1.9, 3.5, 0.15), wide: win(t, 1.9, 2.6, 0.1), nod: pulse(t, 5.4, 0.4), eyes: t > 5.3 && t < 6.6 ? 'happy' : 'normal' });
  },
};

// ─────────────────────────────────────────────── 대기(STANDBY)
export const IDLE = {
  id: 'idle', no: 0, tag: 'STANDBY', ko: '주제나 대본을 기다리는 중',
  caps: [
    { from: 0, tag: 'STANDBY', text: '주제나 대본을 기다리는 중' },
    { from: 4, tag: 'READY', text: '[＋ 새로 만들기]를 누르거나, 말로 시작하세요' },
  ],
  board: (t, S) => ['CREW', 'READY'],
  photo: false,
  onAir: 0,
  screen(ctx, r, t) {
    const p = 0.55 + 0.45 * Math.sin(t * (TAU / 4));
    glow(ctx, r.x + r.w / 2, r.y + r.h / 2, 80, GOLD_RGB, 0.12 * p);
    label(ctx, 'LUMIÈRE GEN', r.x + r.w / 2, r.y + r.h / 2 - 8, { size: 22, weight: 800, family: FONT_DISPLAY, color: PAPER, align: 'center', tracking: 0.12, alpha: 0.6 + 0.4 * p });
    label(ctx, 'ARTGOURMET GEN SYSTEM', r.x + r.w / 2, r.y + r.h / 2 + 20, { size: 9, weight: 700, color: GOLD, align: 'center', tracking: 0.3 });
  },
  draw(ctx, t) {
    // 충전하며 자는 로봇
    const dock = [150, F];
    plate(ctx, dock[0] - 13, F - 70, 26, 70, 5, '#141414', STEEL_LINE, 1.2);
    for (let i = 0; i < 4; i++) plate(ctx, dock[0] - 7, F - 60 + i * 13, 14, 8, 2, i >= 3 - (Math.floor(t * 1.5) % 4) ? GOLD : '#2a2a2a', null);
    ctx.strokeStyle = '#3a3a3a';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(dock[0] + 10, F - 30);
    ctx.quadraticCurveTo(190, F + 2, 214, F - 26);
    ctx.stroke();
    drawRobot(ctx, R(232, 1.15, -1, { y: F, sit: true, legsOut: true, eyes: 'sleep', headTilt: 0.12, armA: { l: [8, 20] }, armB: { l: [-6, 20] }, led: `rgba(${GOLD_RGB},${0.4 + 0.6 * (0.5 + 0.5 * Math.sin(t * 3))})` }));
    zzz(ctx, 230, F - 74, t);
    // 비질하는 로봇(헤드폰)
    const sx = 420 + Math.sin(t * (TAU / 8)) * 60;
    const dir = Math.cos(t * (TAU / 8)) >= 0 ? 1 : -1;
    const sw = Math.sin(t * 7);
    const sh = [sx + 18 * dir + sw * 4, F - 44];
    drawRobot(ctx, R(sx, 1.2, dir, { hat: 'phones', blink: blinkAt(t, 101), armA: { w: sh }, armB: { w: [sx + 4 * dir, F - 60] }, walk: t * 9, look: [0.6, 0.8] }));
    limb(ctx, sx + 4 * dir, F - 62, sh[0] + 8 * dir + sw * 3, F - 6, 2.4, '#6a5330');
    for (let i = -3; i <= 3; i++) limb(ctx, sh[0] + 8 * dir + sw * 3, F - 8, sh[0] + 8 * dir + sw * 3 + i * 2.4, F - 1, 1.2, GOLD);
    // 청소 로봇이 천천히 오간다
    const vx = 560 + Math.sin(t * (TAU / 8) + 1.5) * 90;
    drawVacuum(ctx, vx, F + 1, 1.1, Math.cos(t * (TAU / 8) + 1.5) >= 0 ? 1 : -1, t, { blink: blinkAt(t, 102) > 0.5 });
    director(ctx, t, { hand: [CHAIR.x - 30, SEAT - 30], prop: (h) => drawPaper(ctx, h[0] - 4, h[1] - 8, -0.15, 1.1, ''), look: [0.8, 0.6], headDy: 0, nod: pulse(t, 4, 0.5) });
  },
};

// ─────────────────────────────────────────────── 완료(WRAP)
export const DONE = {
  id: 'done', no: 0, tag: "THAT'S A WRAP", ko: '제작 완료',
  caps: [
    { from: 0, tag: 'WRAP', text: '제작 완료 — 완성본이 준비됐습니다' },
    { from: 4, tag: 'CUT', text: '감독 로봇: "컷! 수고했어"' },
  ],
  board: () => ['STATUS', 'DONE'],
  onAir: 0,
  screen(ctx, r, t) {
    const p = 0.6 + 0.4 * Math.sin(t * 2);
    glow(ctx, r.x + r.w / 2, r.y + r.h / 2, 90, GOLD_RGB, 0.2 * p);
    label(ctx, '✓', r.x + r.w / 2, r.y + r.h / 2 - 16, { size: 40, weight: 900, color: GOLD, align: 'center' });
    label(ctx, '제작 완료', r.x + r.w / 2, r.y + r.h / 2 + 26, { size: 16, weight: 800, family: FONT_BODY, color: PAPER, align: 'center' });
  },
  draw(ctx, t) {
    for (let i = 0; i < 46; i++) {
      const u = (t / L + hash(i)) % 1;
      const x = 110 + hash(i + 50) * 620 + Math.sin(u * 9 + i) * 12;
      const y = 80 + u * 380;
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(u * 12 + i);
      ctx.fillStyle = i % 3 ? GOLD : PAPER;
      ctx.fillRect(-3, -1.5, 6, 3);
      ctx.restore();
    }
    const cast = [[230, 'hard', 1], [350, 'phones', 1], [470, 'mask', -1], [590, 'phones', -1]];
    cast.forEach(([x, hat, face], i) => {
      const ph = t * 5 + i * 1.3;
      const hop = Math.max(0, Math.sin(ph)) * 12;
      drawRobot(ctx, R(x, 1.2, face, {
        hat, maskUp: 1, eyes: 'happy', hop, armA: { l: [10, -26 - hop * 0.3] }, armB: { l: [-10, -24] }, ant: Math.sin(ph) * 0.4,
      }));
    });
    director(ctx, t, { say: '컷! 수고했어', sayA: win(t, 3.8, 6.4, 0.2), mega: win(t, 3.6, 6.5, 0.2), eyes: 'happy' });
  },
};
