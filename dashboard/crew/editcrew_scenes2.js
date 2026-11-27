// 편집 단계 장면 ⑤~⑧: 내용 컷 · 줌·PIP·블러 · 가편 렌더 · 구성 재편집 (각 8초 반복)
import { TAU, FONT_BODY, FONT_DISPLAY, clamp, ease, hash, roundRectPath } from './core.js';
import { GOLD, GOLD_RGB, PAPER, INK, STEEL, STEEL_LINE, METAL, GRAY, rad, mix, mixPt, sm, win, pulse, wobble, keyed, limb, plate, dot, glow, label, drawRobot, drawWrench, drawLadder } from './crew.js';
import { F, SCR, CHAIR, SEAT, bubble, sparkle, zzz, drawDesk, drawPaper, drawBin, drawStamp, drawSpray, drawChunk } from './editcrew_set.js';
import { L, R, blinkAt, director } from './editcrew_scenes1.js';

const ZF = 1.25;
/** 화면(모니터) 좌표 -> 바닥 무대(1.25배 확대 전) 좌표 */
const toFloor = (p) => [480 + (p[0] - 480) / ZF, F + (p[1] - F) / ZF];

// ─────────────────────────────────────────────── ⑤ 내용 컷
const TOSS = [0.8, 2.3, 3.8];
const TOSS_WORD = ['곁가지', '반복', '중계'];
const CUT_AT = { 1: 1.4, 3: 2.9, 4: 4.4 };
export const CONTENT = {
  id: 'content', no: 5, tag: 'CONTENT CUT', ko: '내용 컷',
  caps: [
    { from: 0, tag: 'SCRIPT', text: '감독 로봇이 대본을 읽고 덜어냅니다' },
    { from: 4.4, tag: 'MISS', text: '한 장이 통을 빗나갔습니다' },
    { from: 5.4, tag: 'KEEP', text: '애매하면 살립니다 — 나중에 고를 수 있게' },
  ],
  board: () => ['CUTS', '0022'],
  screen(ctx, r, t) {
    label(ctx, 'SCRIPT', r.x + 10, r.y + 14, { size: 8, color: GRAY, tracking: 0.18 });
    for (let i = 0; i < 6; i++) {
      const y = r.y + 30 + i * 19;
      const w = 140 + ((i * 47) % 110);
      ctx.fillStyle = 'rgba(242,240,234,0.5)';
      ctx.fillRect(r.x + 14, y, w, 5);
      const kept = i === 4 && t > 7.0;
      if (CUT_AT[i] !== undefined && t > CUT_AT[i] && !kept) {
        ctx.strokeStyle = GOLD;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(r.x + 10, y + 2.5);
        ctx.lineTo(r.x + 18 + w, y + 2.5);
        ctx.stroke();
        label(ctx, 'CUT', r.x + r.w - 14, y + 3, { size: 8, weight: 800, color: GOLD, align: 'right', tracking: 0.15 });
      }
      if (kept) label(ctx, 'KEEP', r.x + r.w - 14, y + 3, { size: 8, weight: 800, color: PAPER, align: 'right', tracking: 0.15 });
    }
  },
  draw(ctx, t) {
    const bin = [140, F];
    drawBin(ctx, bin[0], bin[1], 1.2, 'CUT');
    // 도장 로봇(안전모) + 책상
    drawDesk(ctx, 486, 130);
    const ex = 462;
    const ph = t % 1.0;
    const down = ph < 0.18 ? sm(ph / 0.18) : ph < 0.32 ? 1 - sm((ph - 0.18) / 0.14) : 0;
    const sh = [534, F - 76 + down * 16];
    drawRobot(ctx, R(ex, 1.2, 1, { hat: 'hard', blink: blinkAt(t, 11), armA: { w: sh }, armB: { l: [-6, 18] }, look: [0.6, 0.7], lean: 0.05 * down }));
    for (let i = 0; i < 3; i++) drawPaper(ctx, 512 + i * 26, F - 52, 0.08 * (i - 1), 0.9, Math.floor(t) % 3 >= i ? 'CUT' : '');
    drawStamp(ctx, sh[0], sh[1] - 4, 1.1);
    plate(ctx, 584, F - 50, 40, 6, 2, '#262626', STEEL_LINE, 1);
    label(ctx, 'KEEP', 604, F - 36, { size: 7.5, weight: 800, color: GRAY, align: 'center', tracking: 0.15 });
    if (t > 7.55) drawPaper(ctx, 604, F - 62, -0.05, 0.85, '반복');
    // 주워 오는 로봇(헤드폰)
    const kx = keyed([[0, 196], [4.7, 196], [5.2, 214], [5.8, 238], [7.2, 238], [7.9, 196]], t);
    const pick = win(t, 4.55, 5.2, 0.15);
    const holdUp = win(t, 5.15, 7.05, 0.15);
    const missAt = [212, F - 8];
    let khand = mixPt([kx + 20, F - 34], [missAt[0], missAt[1] - 6], pick);
    khand = mixPt(khand, [kx + 22, F - 86], holdUp);
    const walking = win(t, 5.15, 5.85, 0.05) + win(t, 7.2, 7.95, 0.05);
    drawRobot(ctx, R(kx, 1.2, 1, {
      hat: 'phones', blink: blinkAt(t, 12), crouch: 0.9 * pick, armA: { w: khand }, armB: { l: [-6, 16] },
      walk: walking > 0.1 ? t * 14 : undefined, look: pick ? [0.6, 0.9] : holdUp ? [0.9, -0.4] : [0.8, -0.2],
      eyes: holdUp > 0.5 ? 'happy' : 'normal',
    }));
    if (t > 4.62 && t < 7.05) drawPaper(ctx, khand[0] + 4, khand[1] - 12, 0.1, 0.95, '반복');
    if (t >= 7.05 && t < 7.55) {
      const u = clamp((t - 7.05) / 0.5);
      const pp = mixPt([kx + 26, F - 98], [604, F - 62], ease.inOutCubic(u));
      drawPaper(ctx, pp[0], pp[1] - Math.sin(u * Math.PI) * 40, u * 6.28, 0.9, '반복');
    }
    bubble(ctx, kx + 6, F - 128, '이건 살릴까요?', win(t, 5.3, 6.8, 0.15), -10, 13);
    // 서서 대본을 읽는 감독(의자는 비어 있다)
    const dx = 300;
    let toss = 0;
    TOSS.forEach((t0) => { toss = Math.max(toss, pulse(t, t0, 0.5)); });
    const back = win(t, 5.6, 7.4, 0.2);
    const dh = mixPt([dx + 24, F - 60], [dx - 8, F - 96], toss);
    drawRobot(ctx, R(dx, 1.2, 1, {
      hat: 'band', blink: blinkAt(t, 3), armA: { w: dh }, armB: { l: [6, 16] }, lean: -0.12 * toss,
      look: back > 0.3 ? [-1, -0.2] : [0.5, 0.3], eyes: t > 6.6 && t < 7.4 ? 'happy' : 'normal', headDy: pulse(t, 6.6, 0.4) * 2.4,
    }));
    const holding = !TOSS.some((t0) => t > t0 + 0.12 && t < t0 + 0.55);
    if (holding) drawPaper(ctx, dh[0] + 6, dh[1] - 14, 0.15, 1, '');
    bubble(ctx, dx + 4, F - 132, '살려!', win(t, 6.7, 7.6, 0.12), 0);
    // 날아가는 종이
    TOSS.forEach((t0, i) => {
      const u = (t - t0 - 0.15) / 0.8;
      if (u < 0) return;
      const miss = i === 2;
      const end = miss ? missAt : [bin[0], F - 46];
      if (u > 1) {
        if (miss && t < 4.62) drawPaper(ctx, missAt[0], missAt[1], 1.4, 0.95, TOSS_WORD[i]);
        return;
      }
      const p = mixPt([dx - 14, F - 110], end, u);
      drawPaper(ctx, p[0], p[1] - Math.sin(u * Math.PI) * 60, u * (miss ? 5 : 7), 0.95 - u * 0.15, TOSS_WORD[i]);
    });
  },
};

// ─────────────────────────────────────────────── ⑥ 줌·PIP·블러
const ZT = { tx: 0.52, ty: 0.18, tw: 0.4, th: 0.42 };
function zoomRect(t, r) {
  const u = keyed([[0, 0], [0.8, 0], [2.0, 1], [3.2, 1], [4.0, 0]], t, ease.inOutCubic);
  return { x: r.x + mix(0, ZT.tx * r.w, u) + 4, y: r.y + mix(0, ZT.ty * r.h, u) + 4, w: mix(r.w, ZT.tw * r.w, u) - 8, h: mix(r.h, ZT.th * r.h, u) - 8, u };
}
export const ZOOM = {
  id: 'zoom', no: 6, tag: 'ZOOM · PIP · BLUR', ko: '줌·얼굴 화면·개인정보 가림',
  caps: [
    { from: 0, tag: 'ZOOM', text: '중요한 곳을 당겨서 보여 줍니다' },
    { from: 2.6, tag: 'PIP', text: '얼굴 화면 자리 잡기' },
    { from: 4.2, tag: 'BLUR', text: '비밀번호·토큰은 안개로 덮습니다' },
  ],
  board: (t, S) => ['BLURS', String(132 + S.lap).padStart(4, '0')],
  screen(ctx, r, t, S) {
    if (!S.img) {
      plate(ctx, r.x + 8, r.y + 8, r.w - 16, r.h - 16, 4, '#0d0d0d', STEEL_LINE, 1);
      ctx.fillStyle = '#1c1c1c';
      ctx.fillRect(r.x + 8, r.y + 8, 64, r.h - 16);
      for (let i = 0; i < 6; i++) {
        ctx.fillStyle = 'rgba(242,240,234,0.35)';
        ctx.fillRect(r.x + 84, r.y + 24 + i * 16, 90 + ((i * 41) % 100), 4);
      }
    }
    const tk = { x: r.x + r.w - 128, y: r.y + r.h - 30 };
    const fog = keyed([[0, 0], [4.6, 0], [5.4, 1], [7.5, 1], [7.9, 0]], t);
    label(ctx, 'sk-proj-8f3k…Q2', tk.x, tk.y, { size: 10, weight: 700, color: PAPER, alpha: 1 - fog });
    if (fog > 0) {
      for (let i = 0; i < 14; i++) {
        const a = hash(i) * TAU, d = hash(i + 3) * 18 * fog;
        glow(ctx, tk.x + 52 + Math.cos(a) * d * 2.4, tk.y + Math.sin(a) * d * 0.6, 22 * fog, '190,190,190', 0.35 * fog);
      }
      label(ctx, 'BLUR', tk.x + 52, tk.y, { size: 9, weight: 800, color: GOLD, align: 'center', tracking: 0.2, alpha: fog });
    }
    const pip = keyed([[0, 0], [2.6, 0], [3.0, 1], [7.5, 1], [7.9, 0]], t, ease.outCubic);
    if (pip > 0) {
      const px = r.x + 10 - (1 - pip) * 90, py = r.y + r.h - 54;
      plate(ctx, px, py, 70, 46, 6, '#1c1c1c', PAPER, 1.6);
      plate(ctx, px + 22, py + 9, 26, 20, 6, PAPER, INK, 1);
      roundRectPath(ctx, px + 26, py + 14, 18, 9, 3.5);
      ctx.fillStyle = INK;
      ctx.fill();
      dot(ctx, px + 31, py + 18.5, 1.8, GOLD);
      dot(ctx, px + 39, py + 18.5, 1.8, GOLD);
      plate(ctx, px + 20, py + 31, 30, 13, 5, PAPER, INK, 1);
    }
    const z = zoomRect(t, r);
    ctx.strokeStyle = GOLD;
    ctx.lineWidth = 2.4;
    const c = 14;
    for (const [cx, cy, sx, sy] of [[z.x, z.y, 1, 1], [z.x + z.w, z.y, -1, 1], [z.x, z.y + z.h, 1, -1], [z.x + z.w, z.y + z.h, -1, -1]]) {
      ctx.beginPath();
      ctx.moveTo(cx, cy + sy * c);
      ctx.lineTo(cx, cy);
      ctx.lineTo(cx + sx * c, cy);
      ctx.stroke();
    }
    if (z.u > 0.5) label(ctx, `×${(1 + 0.6 * z.u).toFixed(1)}`, z.x + z.w - 4, z.y + 12, { size: 10, weight: 800, color: GOLD, align: 'right', alpha: z.u });
  },
  draw(ctx, t) {
    // 사다리 위 지시봉 로봇(안전모)
    const lad = { cx: 262, top: 372 };
    drawLadder(ctx, lad.cx, lad.top, F, 20, 34);
    const z = zoomRect(t, SCR);
    const tip = toFloor([z.x + 8, z.y + z.h - 8]);
    const lh = [lad.cx + 34, lad.top - 58];
    drawRobot(ctx, R(lad.cx, 1.2, 1, { y: lad.top, hat: 'hard', blink: blinkAt(t, 21), armA: { w: lh }, armB: { l: [-4, 20] }, look: [0.7, -0.9], lean: -0.06 }));
    limb(ctx, lh[0], lh[1], tip[0], tip[1], 2.2, METAL);
    dot(ctx, tip[0], tip[1], 3.4, GOLD);
    // 버튼 누르는 로봇(헤드폰) — PIP
    const bx = 500;
    plate(ctx, bx, F - 46, 64, 46, 6, '#141414', STEEL_LINE, 1.3);
    label(ctx, 'PIP', bx + 32, F - 10, { size: 8, color: GRAY, align: 'center', tracking: 0.25 });
    const press = pulse(t, 2.45, 0.4);
    dot(ctx, bx + 22, F - 50 + press * 3, 9, '#2a2a2a');
    dot(ctx, bx + 22, F - 52 + press * 3, 7, t > 2.6 && t < 7.6 ? GOLD : '#5a3a08');
    drawRobot(ctx, R(472, 1.2, 1, {
      hat: 'phones', blink: blinkAt(t, 22), armA: { w: [bx + 22, F - 60 + press * 6] }, armB: { l: [-6, 16] },
      look: t > 2.6 && t < 4 ? [0.2, -1] : [0.6, 0.5], eyes: t > 3.0 && t < 4.2 ? 'happy' : 'normal',
    }));
    // 스프레이 로봇(용접면)
    const wx = 690;
    const spray = win(t, 4.5, 5.5, 0.12);
    const wh = [672, F - 62];
    const target = toFloor([SCR.x + SCR.w - 76, SCR.y + SCR.h - 30]);
    const ang = Math.atan2(target[1] - wh[1], target[0] - wh[0]);
    drawRobot(ctx, R(wx, 1.2, -1, {
      hat: 'mask', maskUp: 1 - spray, maskGlow: spray, blink: blinkAt(t, 23), armA: { w: wh }, armB: { l: [-6, 16] },
      look: [0.5, -0.9], lean: 0.05 * spray,
    }));
    drawSpray(ctx, wh[0], wh[1], ang, 1.1);
    if (spray > 0) {
      for (let i = 0; i < 16; i++) {
        const u = (t * 2.2 + i / 16) % 1;
        const nx = wh[0] + Math.cos(ang) * 24, ny = wh[1] + Math.sin(ang) * 24;
        const px = mix(nx, target[0], u) + (hash(i) - 0.5) * 30 * u, py = mix(ny, target[1], u) + (hash(i + 9) - 0.5) * 24 * u;
        dot(ctx, px, py, 1.5 + u * 3, `rgba(200,200,200,${0.5 * spray * (1 - u)})`);
      }
    }
    director(ctx, t, { say: '그건 가려!', sayA: win(t, 3.9, 5.1, 0.15), wide: win(t, 3.9, 4.6, 0.15), mega: win(t, 3.9, 5.0, 0.2) });
  },
};

// ─────────────────────────────────────────────── ⑦ 가편 렌더
const BELT = { x0: 140, gap: 80, v: 60, y: F - 46, a: 110, b: 742, oven: [300, 420], weld: 470, whack: 600 };
const chunkX = (n, t) => BELT.x0 + n * BELT.gap + BELT.v * t;
const rCount = (t, S) => Math.min(45, Math.floor(((S.lap * L + t) * 0.75) % 46));
export const RENDER = {
  id: 'render', no: 7, tag: 'ROUGH RENDER', ko: '가편 렌더',
  caps: [
    { from: 0, tag: 'RENDER', text: '조각마다 따로 굽는 중' },
    { from: 2.5, tag: 'WELD', text: '이음새 용접 — 소리는 통째로 붙입니다' },
    { from: 4.6, tag: 'FIX', text: '삐뚤어진 조각 하나… 바로잡았습니다' },
  ],
  board: (t, S) => ['CHUNKS', `${String(rCount(t, S)).padStart(2, '0')}/45`],
  screen(ctx, r, t, S) {
    const n = rCount(t, S);
    label(ctx, 'ROUGH CUT', r.x + 10, r.y + 14, { size: 8, color: GRAY, tracking: 0.18 });
    const cw = (r.w - 24) / 45;
    for (let i = 0; i < 45; i++) {
      ctx.fillStyle = i < n ? `rgba(${GOLD_RGB},0.9)` : '#1e1e1e';
      ctx.fillRect(r.x + 12 + i * cw, r.y + r.h - 34, cw - 1.2, 16);
    }
    label(ctx, `${n} / 45`, r.x + r.w - 12, r.y + 14, { size: 10, weight: 700, color: GOLD, align: 'right' });
  },
  draw(ctx, t) {
    plate(ctx, BELT.a, F - 32, BELT.b - BELT.a, 10, 5, '#1a1a1a', STEEL_LINE, 1.2);
    for (let x = BELT.a + 10; x < BELT.b; x += 26) {
      dot(ctx, x, F - 27, 3.4, '#2e2e2e');
      limb(ctx, x, F - 27, x + Math.cos(t * 8) * 3, F - 27 + Math.sin(t * 8) * 3, 1, '#555');
    }
    limb(ctx, BELT.a + 8, F - 22, BELT.a + 8, F - 1, 3, '#3a3a3a');
    limb(ctx, BELT.b - 8, F - 22, BELT.b - 8, F - 1, 3, '#3a3a3a');
    for (let n = -9; n < 8; n++) {
      const x = chunkX(n, t);
      if (x < BELT.a + 16 || x > BELT.b - 6) continue;
      const crooked = ((n % 6) + 6) % 6 === 2 && x > BELT.oven[1] && x < BELT.whack;
      const hitT = (BELT.whack - BELT.x0 - n * BELT.gap) / BELT.v;
      const rot = crooked ? 0.32 : ((n % 6) + 6) % 6 === 2 && x >= BELT.whack ? wobble(t, hitT, 5, 6) * 0.15 : 0;
      drawChunk(ctx, x, BELT.y + (crooked ? -3 : 0), 54, 26, rot, x > BELT.oven[1] ? 1 : 0);
    }
    const [o0, o1] = BELT.oven;
    plate(ctx, o0, F - 122, o1 - o0, 94, 10, STEEL, STEEL_LINE, 1.6);
    const heat = 0.6 + 0.4 * Math.sin(t * 5);
    glow(ctx, (o0 + o1) / 2, F - 84, 56, GOLD_RGB, 0.18 * heat);
    plate(ctx, o0 + 16, F - 104, o1 - o0 - 32, 34, 6, `rgba(${GOLD_RGB},${0.25 + 0.2 * heat})`, INK, 1.2);
    label(ctx, 'RENDER', (o0 + o1) / 2, F - 58, { size: 9, weight: 800, color: GOLD, align: 'center', tracking: 0.3 });
    for (let i = 0; i < 3; i++) dot(ctx, o0 + 26 + i * 12, F - 113, 3, i === Math.floor(t * 3) % 3 ? GOLD : '#3a2a10');
    // 용접 로봇(용접면 내림)
    let spark = 0;
    for (let n = -9; n < 8; n++) spark = Math.max(spark, 1 - Math.abs(chunkX(n, t) + BELT.gap / 2 - BELT.weld) / 12);
    spark = clamp(spark);
    drawRobot(ctx, R(518, 1.2, -1, { hat: 'mask', maskUp: 0, maskGlow: spark, armA: { w: [BELT.weld + 2, BELT.y - 6] }, armB: { l: [-6, 16] }, lean: 0.12 }));
    limb(ctx, BELT.weld + 2, BELT.y - 6, BELT.weld - 6, BELT.y + 2, 2.6, METAL);
    for (let i = 0; i < 7 * spark; i++) {
      const a = -Math.PI / 2 + (hash(i + Math.floor(t * 20)) - 0.5) * 2.4;
      const d = 6 + hash(i * 3 + Math.floor(t * 20)) * 16;
      limb(ctx, BELT.weld - 6, BELT.y + 2, BELT.weld - 6 + Math.cos(a) * d, BELT.y + 2 + Math.sin(a) * d, 1.2, GOLD);
    }
    glow(ctx, BELT.weld - 6, BELT.y + 2, 30, GOLD_RGB, 0.4 * spark);
    // 렌치 로봇(안전모) — 삐뚤어진 조각을 '탕'
    const whackT = (BELT.whack - BELT.x0 - 2 * BELT.gap) / BELT.v;
    const sw = pulse(t, whackT - 0.25, 0.4);
    const gh = [622, F - 82 + sw * 30];
    drawRobot(ctx, R(650, 1.2, -1, {
      hat: 'hard', blink: blinkAt(t, 31), armA: { w: gh }, armB: { l: [-4, 18] }, look: [0.6, 0.7], lean: 0.1 * sw,
      eyes: t > whackT && t < whackT + 1.2 ? 'happy' : 'normal',
    }));
    drawWrench(ctx, gh[0], gh[1], rad(150 - sw * 50), 26, 1.1);
    const bang = pulse(t, whackT, 0.35);
    sparkle(ctx, BELT.whack - 4, BELT.y - 12, 16 * bang, bang);
    if (bang > 0.05) label(ctx, '탕!', BELT.whack + 16, BELT.y - 40, { size: 16, weight: 900, family: FONT_DISPLAY, color: GOLD, alpha: bang });
    // 감기는 릴(감독 의자 앞)
    const rx = 740, ry = F - 64;
    limb(ctx, rx - 12, F - 1, rx, ry, 3, '#3a3a3a');
    limb(ctx, rx + 12, F - 1, rx, ry, 3, '#3a3a3a');
    dot(ctx, rx, ry, 30, '#161616');
    ctx.strokeStyle = `rgba(${GOLD_RGB},0.8)`;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(rx, ry, 28, 0, TAU);
    ctx.stroke();
    for (let i = 0; i < 5; i++) {
      const a = t * 3 + (i / 5) * TAU;
      dot(ctx, rx + Math.cos(a) * 16, ry + Math.sin(a) * 16, 5, '#050505');
    }
    dot(ctx, rx, ry, 4, GOLD);
    const sleep = t > 1.2 && t < whackT;
    director(ctx, t, { eyes: sleep ? 'sleep' : 'normal', wide: win(t, whackT, whackT + 0.9, 0.1), look: sleep ? [0, 0.6] : [0.6, 0.3], ant: wobble(t, whackT, 4, 3) * 0.6 });
    if (sleep) zzz(ctx, CHAIR.x - 20, SEAT - 82, t);
  },
};

// ─────────────────────────────────────────────── ⑧ 구성 재편집
const CARD_X = [190, 280, 370, 520];
function drawCard(ctx, x, y, n, rot = 0, hot = 0) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rot);
  plate(ctx, -30, -52, 60, 52, 6, hot ? GOLD : '#171717', hot ? INK : `rgba(${GOLD_RGB},0.7)`, 1.4);
  label(ctx, String(n), 0, -26, { size: 24, weight: 800, family: FONT_DISPLAY, color: hot ? INK : PAPER, align: 'center' });
  ctx.restore();
}
function rsPos(t) {
  const rw = keyed([[0, 0], [7.2, 0], [7.9, 1]], t, ease.inOutCubic); // 되감기
  const slide = keyed([[0, 0], [2.8, 0], [3.5, 1]], t, ease.outCubic) * (1 - rw);
  const place = keyed([[0, 0], [3.6, 0], [4.1, 1]], t) * (1 - rw);
  return { c1: mix(CARD_X[0], CARD_X[1], slide), c2: mix(CARD_X[1], CARD_X[2], slide), c4: CARD_X[3], place, rw };
}
export const RESTRUCTURE = {
  id: 'restructure', no: 8, tag: 'RESTRUCTURE', ko: '구성 재편집',
  caps: [
    { from: 0, tag: 'HOOK', text: '가장 재밌는 장면을 맨 앞으로' },
    { from: 3.4, tag: 'ORDER', text: '이야기는 그 뒤에 차례로 잇습니다' },
    { from: 7.2, tag: 'REWIND', text: '다른 순서도 한 번 더 봅니다' },
  ],
  board: () => ['ORDER', '3·1·2·4'],
  screen(ctx, r, t) {
    const p = rsPos(t);
    label(ctx, 'ORDER', r.x + 10, r.y + 14, { size: 8, color: GRAY, tracking: 0.18 });
    const order = p.place > 0.5 ? [3, 1, 2, 4] : [1, 2, 3, 4];
    order.forEach((n, i) => {
      plate(ctx, r.x + 20 + i * 66, r.y + 44, 56, 44, 5, n === 3 ? GOLD : '#1b1b1b', n === 3 ? INK : STEEL_LINE, 1.2);
      label(ctx, String(n), r.x + 48 + i * 66, r.y + 66, { size: 20, weight: 800, family: FONT_DISPLAY, color: n === 3 ? INK : PAPER, align: 'center' });
    });
    if (p.place > 0.5) label(ctx, 'HOOK FIRST', r.x + 20, r.y + 108, { size: 10, weight: 800, color: GOLD, tracking: 0.2 });
  },
  draw(ctx, t) {
    const p = rsPos(t);
    const cx = keyed([[0, 445], [2.0, 445], [3.5, 236], [6.3, 236], [7.5, 445]], t);
    const carry = win(t, 1.8, 3.8, 0.2);
    const grab = win(t, 1.4, 4.1, 0.2);
    const walking = win(t, 2.0, 3.5, 0.05) + win(t, 6.3, 7.5, 0.05);
    const face = t > 6.3 && t < 7.5 ? 1 : -1;
    const hand = mixPt([cx - 22, F - 40], [cx - 24, F - 66], carry);
    drawCard(ctx, p.c1, F, 1);
    drawCard(ctx, p.c2, F, 2);
    drawCard(ctx, p.c4, F, 4);
    drawRobot(ctx, R(cx, 1.2, face, {
      hat: 'hard', blink: blinkAt(t, 41), crouch: 0.8 * win(t, 1.35, 1.9, 0.15) + 0.8 * win(t, 3.6, 4.15, 0.15),
      armA: { w: grab > 0.1 ? hand : [cx - 18 * face, F - 36] }, armB: { l: [-6, 16] },
      walk: walking > 0.1 ? t * 15 : undefined, look: [0.7, 0.4], eyes: t > 4.1 && t < 6 ? 'happy' : 'normal',
    }));
    let c3 = [CARD_X[2], F];
    if (t >= 1.8 && t < 4.1) c3 = [hand[0] - 8, hand[1] + 30];
    else if (t >= 4.1) c3 = [CARD_X[0], F];
    if (p.rw > 0) c3 = [mix(CARD_X[0], CARD_X[2], p.rw), F];
    drawCard(ctx, c3[0], c3[1], 3, t >= 1.8 && t < 4.1 ? 0.06 : 0, 1);
    if (p.rw > 0 && p.rw < 1) label(ctx, '◀◀', 360, F - 100, { size: 22, weight: 900, color: GOLD, align: 'center' });
    // 박수 치는 로봇(헤드폰)
    const happy = t > 4.1 && t < 6;
    const clap = happy ? Math.abs(Math.sin(t * 12)) : 0;
    drawRobot(ctx, R(610, 1.2, -1, {
      hat: 'phones', blink: blinkAt(t, 42), armA: { l: [8 - clap * 8, -12] }, armB: { l: [24 - clap * 8, -12] }, hop: clap * 2,
      eyes: happy ? 'happy' : 'normal', look: [0.8, 0.3],
    }));
    director(ctx, t, { say: '3번을 맨 앞으로!', sayA: win(t, 0.3, 1.6, 0.15), mega: win(t, 0.2, 1.7, 0.2), eyes: t > 4.2 && t < 6 ? 'happy' : 'normal' });
  },
};
