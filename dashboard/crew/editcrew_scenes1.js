// 편집 단계 장면 ①~④: 싱크 맞추기 · 받아쓰기 · 버벅임 찾기 · 습관어·무음 컷 (각 8초 반복)
import { TAU, FONT_BODY, FONT_DISPLAY, clamp, ease, hash } from './core.js';
import { GOLD, GOLD_RGB, PAPER, INK, STEEL, STEEL_LINE, METAL, GRAY, rad, mix, mixPt, sm, win, pulse, wobble, keyed, limb, plate, dot, glow, label, lookAt, drawRobot, drawVacuum, drawWrench } from './crew.js';
import { F, SCR, CHAIR, SEAT, bubble, sparkle, drawClapper, drawMegaphone, drawDesk, drawLaptop, drawSpeaker, drawMagnifier, drawScissors, drawBin, drawTile, wave } from './editcrew_set.js';

export const L = 8;
export const R = (x, s, face, o = {}) => Object.assign({ x, y: F, s, face, blink: 0 }, o);
/** 눈 깜빡임(로봇마다 다른 박자) */
export const blinkAt = (t, seed) => {
  const per = 2.6 + hash(seed) * 2.2;
  const u = (t + hash(seed + 7) * per) % per;
  return u < 0.12 ? Math.sin((u / 0.12) * Math.PI) : 0;
};

/** 감독 로봇(의자에 앉아 왼쪽을 본다). o: { say, sayA, mega(0~1 메가폰 들기), nod, eyes, wide, look } */
export function director(ctx, t, o = {}) {
  const x = CHAIR.x, s = 1.15;
  const mega = o.mega || 0;
  const p = R(x, s, -1, {
    y: SEAT, sit: true, hat: 'band', eyes: o.eyes || 'normal', wide: o.wide || 0, blink: blinkAt(t, 3),
    look: o.look || [0.4, -0.1], headDy: (o.nod || 0) * 2.2, ant: Math.sin(t * 1.7) * 0.15 + (o.ant || 0),
    led: GOLD,
  });
  const sh = [x - 16, SEAT - 24];
  const hand = o.hand || mixPt([x - 20, SEAT - 6], [x - 30, SEAT - 40], mega);
  p.armA = { w: hand };
  p.armB = { l: [-4, 18] };
  drawRobot(ctx, p);
  if (!o.hand) drawMegaphone(ctx, hand[0], hand[1], mix(rad(150), rad(195), mega), 1);
  if (o.prop) o.prop(hand);
  if (o.say) bubble(ctx, x - 40, SEAT - 92, o.say, o.sayA || 0, 22);
}

// 공통: 장면 아래 문구 고르기
export function captionAt(caps, t) {
  let c = caps[0];
  for (const x of caps) if (t >= x.from) c = x;
  return c;
}

// ─────────────────────────────────────────────── ① 싱크 맞추기
export const SYNC = {
  id: 'sync', no: 1, tag: 'SYNC', ko: '싱크 맞추기',
  caps: [
    { from: 0, tag: 'SLATE', text: '슬레이트를 칩니다 — 레디, 액션' },
    { from: 2.3, tag: 'ALIGN', text: '화면 소리와 얼굴 소리를 겹쳐 맞추는 중' },
    { from: 4.7, tag: 'LOCK', text: '딱 맞았습니다. 0.03초까지 봤습니다' },
  ],
  board: (t) => ['OFFSET', `${(keyed([[0, 3.5], [2.3, 3.5], [4.6, 0.03], [7.6, 0.03], [7.95, 3.5]], t)).toFixed(2)}s`],
  screen(ctx, r, t) {
    const off = keyed([[0, 46], [2.3, 46], [4.6, 0], [7.6, 0], [7.95, 46]], t);
    const spike = t >= 2.2 && t < 7.7 ? 150 : -99;
    label(ctx, 'SCREEN', r.x + 10, r.y + 16, { size: 8, color: GRAY, tracking: 0.2 });
    label(ctx, 'FACE CAM', r.x + 10, r.y + 78, { size: 8, color: GRAY, tracking: 0.2 });
    wave(ctx, r.x + 10, r.y + 46, r.w - 20, 14, 1.3, t, 0, PAPER, spike);
    wave(ctx, r.x + 10, r.y + 108, r.w - 20, 14, 1.3, t, -off, `rgba(${GOLD_RGB},0.9)`, spike);
    if (spike > 0) {
      ctx.strokeStyle = `rgba(${GOLD_RGB},0.8)`;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(r.x + 10 + 150, r.y + 28);
      ctx.lineTo(r.x + 10 + 150 + off, r.y + 126);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    const lock = win(t, 4.6, 7.6, 0.2);
    if (lock > 0) label(ctx, '✓ SYNC LOCK', r.x + r.w - 12, r.y + 16, { size: 9.5, weight: 800, color: GOLD, align: 'right', tracking: 0.15, alpha: lock });
  },
  draw(ctx, t) {
    // 슬레이트 든 로봇(헤드폰)
    const x = 214;
    const clap1 = 1.0, clap2 = 2.2;
    let open = keyed([[0, 0], [0.5, 1], [0.95, 1], [1.02, 0.15], [1.3, 0.5], [1.7, 1], [2.15, 1], [2.22, 0], [7.4, 0], [7.9, 0]], t);
    open += wobble(t, clap1 + 0.03, 6, 9) * 0.25; // 첫 번째는 안 닫히고 튕긴다
    const hand = [x + 30, F - 62 + pulse(t, clap2, 0.25) * 4];
    const p = R(x, 1.2, 1, {
      hat: 'phones', blink: blinkAt(t, 1), armA: { w: hand }, armB: { l: [10, -22] },
      look: t > clap1 && t < clap1 + 0.9 ? [0.6, -0.8] : [0.5, -0.5], wide: pulse(t, clap1 + 0.05, 0.8),
      hop: pulse(t, clap2, 0.35) * 5, eyes: t > clap2 && t < 4 ? 'happy' : 'normal',
    });
    drawRobot(ctx, p);
    drawClapper(ctx, hand[0] - 2, hand[1] - 26, -0.12, clamp(open), 1.05);
    const bang = pulse(t, clap2, 0.5);
    sparkle(ctx, hand[0] + 6, hand[1] - 34, 18 * bang, bang);
    if (bang > 0.05) label(ctx, '딱!', hand[0] + 34, hand[1] - 52, { size: 18, weight: 900, family: FONT_DISPLAY, color: GOLD, alpha: bang });
    if (t > clap1 && t < clap1 + 1.0) label(ctx, '…', hand[0] + 30, hand[1] - 46, { size: 16, weight: 900, color: GRAY, alpha: win(t, clap1, clap1 + 1, 0.15) });

    // 다이얼 돌리는 로봇(안전모) + 조정 상자
    const bx = 594, by = F - 52;
    plate(ctx, bx, by, 66, 52, 6, '#141414', STEEL_LINE, 1.3);
    label(ctx, 'SYNC', bx + 33, by + 42, { size: 7.5, color: GRAY, align: 'center', tracking: 0.25 });
    const turning = win(t, 2.4, 4.7, 0.2);
    const ang = keyed([[0, 0], [2.4, 0], [4.7, -4.2], [7.6, -4.2], [7.95, 0]], t);
    const kx = bx + 26, ky = by + 18;
    dot(ctx, kx, ky, 11, '#2b2b2b');
    dot(ctx, kx, ky, 8, METAL);
    limb(ctx, kx, ky, kx + Math.cos(ang) * 7, ky + Math.sin(ang) * 7, 2.2, INK);
    dot(ctx, bx + 52, by + 14, 3, win(t, 4.6, 7.6, 0.15) ? GOLD : '#3a2a10');
    const gh = [kx + Math.cos(ang) * 6, ky + Math.sin(ang) * 6];
    const g = R(566, 1.2, 1, {
      hat: 'hard', blink: blinkAt(t, 2), lean: 0.08 * turning, armA: { w: mixPt([kx - 4, ky + 22], gh, turning + win(t, 0, 2.4, 0.3) * 0.0) },
      armB: { l: [-6, 18] }, look: turning ? [0.8, 0.3] : lookAt({ x: 566, y: F, s: 1.2, face: 1 }, 480, 160),
      eyes: t > 4.7 && t < 7.5 ? 'happy' : 'normal',
    });
    drawRobot(ctx, g);
    // 감독
    director(ctx, t, {
      mega: win(t, 0.4, 2.1, 0.25), say: t < 3 ? '레디… 액션!' : '싱크 OK!', sayA: win(t, 0.6, 2.2, 0.2) + win(t, 5.0, 7.0, 0.2),
      eyes: t > 5 && t < 7 ? 'happy' : 'normal', nod: pulse(t, 5.1, 0.4),
    });
  },
};

// ─────────────────────────────────────────────── ② 받아쓰기
const SYL = Array.from('안녕하세요오늘은클로드코드로뉴스레터를만들어보겠습니다');
export const ASR = {
  id: 'asr', no: 2, tag: 'TRANSCRIBE', ko: '받아쓰기',
  caps: [
    { from: 0, tag: 'LISTEN', text: '한 마디씩 받아 적는 중' },
    { from: 4.5, tag: 'OOPS', text: '글자 하나가 떨어졌습니다' },
    { from: 6.1, tag: 'CLEAN', text: '청소 로봇이 주워 갔습니다. 다시 들어 봅니다' },
  ],
  board: (t, S) => ['WORDS', String(Math.floor(1180 + (S.lap * L + t) * 6.3)).padStart(5, '0')],
  screen(ctx, r, t) {
    label(ctx, 'TRANSCRIPT · large-v3', r.x + 10, r.y + 14, { size: 8, color: GRAY, tracking: 0.18 });
    const n = Math.floor(t * 7) % 60;
    for (let ln = 0; ln < 5; ln++) {
      const full = ln < Math.floor(n / 12);
      const w = full ? 180 + ((ln * 53) % 90) : ln === Math.floor(n / 12) ? (n % 12) * 18 : 0;
      ctx.fillStyle = 'rgba(242,240,234,0.55)';
      ctx.fillRect(r.x + 12, r.y + 30 + ln * 20, w, 5);
      if (!full && w > 0) {
        ctx.fillStyle = GOLD;
        ctx.fillRect(r.x + 14 + w, r.y + 27 + ln * 20, 2, 11 * (Math.floor(t * 3) % 2));
      }
    }
  },
  draw(ctx, t) {
    // 스피커 → 글자 타일 → 노트북
    const spk = [124, F];
    const beat = 0.5 + 0.5 * Math.sin(t * 9);
    drawSpeaker(ctx, spk[0], spk[1], 1.15, beat);
    drawDesk(ctx, 172, 112);
    const lap = [226, F - 44];
    drawLaptop(ctx, lap[0], lap[1], 1.3, 0.9, Math.floor(t * 3) % 5);
    const from = [spk[0] + 12, F - 40], to = [lap[0] - 4, lap[1] - 18];
    const DROP = 8; // 이 번호 타일이 떨어진다
    for (let i = 0; i < 15; i++) {
      const t0 = i * 0.55, u = (t - t0) / 1.1;
      if (u < 0 || u > 1) continue;
      const ch = SYL[i % SYL.length];
      if (i === DROP) {
        // 가다가 떨어짐
        const v = clamp(u / 0.45);
        let x = mix(from[0], to[0], v * 0.5), y = mix(from[1], to[1], v * 0.5) - Math.sin(v * Math.PI * 0.5) * 30;
        if (u > 0.45) {
          const w = clamp((u - 0.45) / 0.55);
          y = mix(y, F - 10, ease.inCubic(w));
          x += w * 14;
        }
        drawTile(ctx, x, y, ch, 0.85, 0, u * 3);
        continue;
      }
      const x = mix(from[0], to[0], u), y = mix(from[1], to[1], u) - Math.sin(u * Math.PI) * 38;
      drawTile(ctx, x, y, ch, 0.8 - u * 0.25, 0, Math.sin(u * 6) * 0.2);
    }
    // 떨어진 타일이 바닥에 있다가 청소 로봇이 먹는다
    const dropT = DROP * 0.55 + 1.1;
    const vx = keyed([[0, 1010], [5.0, 1010], [6.3, 168], [7.9, -70]], t, ease.linear);
    if (t > dropT && vx > 172) drawTile(ctx, from[0] + (to[0] - from[0]) * 0.5 + 14, F - 10, SYL[DROP], 0.85, 0, 0.3);
    drawVacuum(ctx, vx, F + 1, 1.15, -1, t, { suck: win(t, 5.9, 6.5, 0.1), blink: blinkAt(t, 9) > 0.5 });
    // 타자 치는 로봇(헤드폰)
    const x = 282;
    const tap = Math.abs(Math.sin(t * 13));
    const lookDrop = win(t, 5.0, 6.9, 0.25);
    const p = R(x, 1.2, -1, {
      hat: 'phones', blink: blinkAt(t, 4), armA: { w: [lap[0] + 8, F - 47 - tap * 3] }, armB: { w: [lap[0] + 22, F - 46 - (1 - tap) * 3] },
      look: mixPt([-0.4, -0.6], [0.6, 0.9], lookDrop), eyes: lookDrop > 0.5 && t < 6.4 ? 'sad' : 'normal', headTilt: -0.1 * lookDrop,
      ant: Math.sin(t * 2) * 0.2,
    });
    drawRobot(ctx, p);
    bubble(ctx, x - 6, F - 96, '어?', win(t, 4.9, 5.9, 0.15), 6);
    director(ctx, t, { say: '또박또박!', sayA: win(t, 0.8, 2.4, 0.2), nod: Math.max(0, Math.sin(t * 4.5)) * 0.6 * (t > 2.4 ? 1 : 0) });
  },
};

// ─────────────────────────────────────────────── ③ 버벅임 찾기
const STUM = { v: 50, P: 230, lens: 362 };
const stumOff = (t) => (t < 3.2 ? t * STUM.v : t < 6.6 ? 3.2 * STUM.v : (3.2 + (t - 6.6)) * STUM.v);
export const STUMBLE = {
  id: 'stumble', no: 3, tag: 'STUMBLE HUNT', ko: '버벅임 찾기',
  caps: [
    { from: 0, tag: 'SCAN', text: '같은 말을 되풀이한 곳을 찾는 중' },
    { from: 3.3, tag: 'FOUND', text: '"그 그 그" — 찾았습니다' },
    { from: 6.4, tag: 'HMM', text: '감독님도 방금 그러셨습니다' },
  ],
  board: (t, S) => ['FOUND', String(4 + S.lap + (t > 3.3 ? 1 : 0)).padStart(4, '0')],
  screen(ctx, r, t) {
    label(ctx, 'WORD SCAN', r.x + 10, r.y + 14, { size: 8, color: GRAY, tracking: 0.18 });
    const words = ['그래서', '그', '그', '그', '이렇게', '하면', '돼요'];
    let x = r.x + 14;
    const hot = win(t, 3.2, 6.6, 0.2);
    words.forEach((w, i) => {
      ctx.font = `700 13px ${FONT_BODY}`;
      const ww = ctx.measureText(w).width + 14;
      const rep = i >= 1 && i <= 3;
      const gone = rep && t > 5.4 && t < 7.7;
      if (!gone) {
        plate(ctx, x, r.y + 56, ww, 24, 5, rep && hot ? GOLD : '#1d1d1d', rep && hot ? INK : STEEL_LINE, 1);
        label(ctx, w, x + ww / 2, r.y + 68, { size: 13, weight: 700, family: FONT_BODY, color: rep && hot ? INK : PAPER, align: 'center' });
      }
      x += ww + 6;
    });
    if (hot > 0.3) label(ctx, '반복 ×3', r.x + 14, r.y + 102, { size: 11, weight: 800, family: FONT_BODY, color: GOLD, alpha: hot });
  },
  draw(ctx, t) {
    const off = stumOff(t);
    const c0 = STUM.lens + 3.2 * STUM.v;
    // 바닥에 놓인 받아쓰기 띠(흐르다 멈춘다)
    const lifted = win(t, 4.4, 9, 0.1);
    const liftU = clamp((t - 4.4) / 1.4);
    // 띠 뒤쪽 로봇들 먼저
    // 돋보기 로봇(안전모)
    const ax = 292;
    const found = win(t, 3.2, 6.4, 0.15);
    const turn = win(t, 6.6, 7.8, 0.2);
    const ah = [ax + 28, F - 38 + Math.sin(t * 3) * 2 * (1 - found)];
    const a = R(ax, 1.2, 1, {
      hat: 'hard', blink: blinkAt(t, 5), armA: { w: ah }, armB: { l: [6, 20] }, lean: 0.18 * (1 - turn),
      look: mixPt([0.7, 0.8], [1, -0.6], turn), wide: found + turn * 0.6, ant: wobble(t, 3.25, 5, 3) * 0.6,
      headTilt: turn * -0.12, eyes: 'normal',
    });
    drawRobot(ctx, a);
    drawMagnifier(ctx, ah[0], ah[1], 0.42, 1, found);
    bubble(ctx, ax - 4, F - 100, '찾았다!', win(t, 3.35, 4.7, 0.15), 8);
    // 집게 로봇(헤드폰): 반복 묶음을 들어 통에 버린다
    const bx = 422;
    const grab = win(t, 4.0, 5.1, 0.25);
    const tossU = clamp((t - 5.0) / 0.6);
    const g0 = [STUM.lens + 22, F - 14];
    const bin = [528, F];
    let gh = mixPt([bx - 18, F - 30], g0, grab);
    if (t > 4.6 && t < 5.1) gh = mixPt(g0, [bx - 12, F - 70], clamp((t - 4.6) / 0.45));
    if (t >= 5.1) gh = mixPt([bx - 12, F - 70], [bx - 18, F - 30], clamp((t - 5.1) / 0.6));
    const b = R(bx, 1.2, -1, {
      hat: 'phones', blink: blinkAt(t, 6), crouch: 0.9 * grab, armA: { w: gh }, armB: { l: [-4, 18] },
      look: grab > 0.2 ? [0.8, 0.9] : [0.3, 0.2], eyes: t > 5.6 && t < 6.6 ? 'happy' : 'normal',
    });
    drawRobot(ctx, b);
    drawBin(ctx, bin[0], bin[1], 1.15, 'CUT');
    // 띠
    plate(ctx, 40, F - 26, 690, 22, 4, '#121212', STEEL_LINE, 1.2);
    ctx.save();
    ctx.beginPath();
    ctx.rect(42, F - 40, 686, 40);
    ctx.clip();
    for (let n = -1; n < 5; n++) {
      const base = c0 + n * STUM.P - off;
      drawTile(ctx, base - 150, F - 15, '그래서'.slice(0, 1), 0.9);
      drawTile(ctx, base - 128, F - 15, '래', 0.9);
      drawTile(ctx, base - 106, F - 15, '서', 0.9);
      drawTile(ctx, base - 70, F - 15, '이', 0.9);
      drawTile(ctx, base - 48, F - 15, '렇', 0.9);
      drawTile(ctx, base + 60, F - 15, '게', 0.9);
      if (n === -1) continue; // 지난 바퀴에 이미 뽑혀 나감
      if (n === 0 && t > 4.6) continue;
      const hot = n === 0 ? found : 0;
      for (const d of [-22, 0, 22]) drawTile(ctx, base + d, F - 15, '그', 0.9, hot);
    }
    ctx.restore();
    // 뽑힌 묶음(집게에서 통으로)
    if (t > 4.6 && t < 5.7) {
      let p0 = [gh[0] - 22, gh[1] + 4];
      if (t > 5.05) p0 = mixPt([bx - 34, F - 66], [bin[0], F - 40], ease.inCubic(tossU));
      for (const d of [-22, 0, 22]) drawTile(ctx, p0[0] + d * (1 - tossU * 0.6), p0[1] - (t > 5.05 ? Math.sin(tossU * Math.PI) * 30 : 0), '그', 0.9 * (1 - tossU * 0.4), 1, tossU * 2);
    }
    director(ctx, t, { say: '그, 그러니까…', sayA: win(t, 6.5, 7.75, 0.15), eyes: t > 6.5 && t < 7.7 ? 'sad' : 'normal' });
  },
};

// ─────────────────────────────────────────────── ④ 습관어·무음 컷
const TRIM = { v: 40, P: 320, cut: 300 };
// 패턴 안 구간: [시작, 끝, 종류('s'=말, 'q'=무음, 'u'=음/어)]
const TRIM_SEG = [[0, 70, 's'], [70, 120, 'q'], [120, 200, 's'], [200, 230, 'u'], [230, 280, 's'], [280, 320, 'q']];
export const TIGHTEN = {
  id: 'tighten', no: 4, tag: 'TIGHTEN', ko: '습관어·무음 컷',
  caps: [
    { from: 0, tag: 'TRIM', text: '"음·어"와 빈 시간을 덜어내는 중' },
    { from: 3.0, tag: 'SNIP', text: '0.5초 넘게 쉬면 싹둑' },
    { from: 5.6, tag: 'OOPS', text: '감독님의 "음…"도 같이 잘렸습니다' },
  ],
  board: (t, S) => ['CUTS', String(Math.floor(820 + (S.lap * L + t) * 1.5)).padStart(4, '0')],
  screen(ctx, r, t) {
    label(ctx, 'TIMELINE', r.x + 10, r.y + 14, { size: 8, color: GRAY, tracking: 0.18 });
    const u = (t % L) / L;
    const full = r.w - 24;
    const now = full * (1 - 0.46 * sm(u * 1.2));
    plate(ctx, r.x + 12, r.y + 40, full, 14, 3, '#1a1a1a', STEEL_LINE, 1);
    plate(ctx, r.x + 12, r.y + 40, now, 14, 3, `rgba(${GOLD_RGB},0.85)`, null);
    const mm = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
    label(ctx, `${mm(2891)} → ${mm(2891 * (1 - 0.46 * sm(u * 1.2)))}`, r.x + 12, r.y + 80, { size: 18, weight: 700, family: FONT_DISPLAY, color: PAPER });
    label(ctx, '말은 그대로, 빈 시간만', r.x + 12, r.y + 106, { size: 11, family: FONT_BODY, color: GRAY });
  },
  draw(ctx, t) {
    const off = t * TRIM.v;
    const top = F - 42;
    // 가위 로봇(안전모) — 테이블 뒤
    const sx = 330;
    const snips = [];
    for (let n = -1; n < 4; n++) for (const sg of TRIM_SEG) if (sg[2] !== 's') snips.push((n * TRIM.P + sg[0] + 520 - TRIM.cut) / TRIM.v);
    let snip = 0;
    for (const s0 of snips) snip = Math.max(snip, pulse(t, s0 - 0.05, 0.3));
    const turn = win(t, 5.7, 6.6, 0.15);
    const sh = mixPt([TRIM.cut + 2, top - 6], [sx + 30, F - 92], turn);
    const s = R(sx, 1.2, -1, { hat: 'hard', blink: blinkAt(t, 7), armA: { w: sh }, armB: { l: [-4, 18] }, look: turn ? [-1, -0.8] : [0.3, 0.8], face: turn > 0.5 ? 1 : -1 });
    if (turn > 0.5) s.armA = { w: [sx + 34, F - 84] };
    drawRobot(ctx, s);
    // 파리채 로봇(헤드폰) — "음·어" 말풍선을 친다
    const wx = 168;
    const umms = [];
    for (let n = -1; n < 4; n++) umms.push((n * TRIM.P + 200 + 520 - TRIM.cut) / TRIM.v + 0.35);
    let swat = 0, swatT = -9;
    for (const u0 of umms) if (t > u0 + 0.5 && t < u0 + 1.3) { swat = pulse(t, u0 + 0.6, 0.45); swatT = u0; }
    const wh = [wx + 30, F - 70 - swat * 22];
    const w = R(wx, 1.2, 1, { hat: 'phones', blink: blinkAt(t, 8), armA: { w: wh }, armB: { l: [-6, 16] }, look: [0.6, -0.7], hop: swat * 4 });
    drawRobot(ctx, w);
    limb(ctx, wh[0], wh[1], wh[0] + 24, wh[1] - 26 + swat * 20, 2.4, METAL);
    plate(ctx, wh[0] + 18, wh[1] - 42 + swat * 22, 16, 18, 3, GOLD, INK, 1.2);
    // 테이블 + 파형 띠
    drawDesk(ctx, 40, 640, top + 4);
    ctx.save();
    ctx.beginPath();
    ctx.rect(44, top - 30, 632, 40);
    ctx.clip();
    for (let n = -1; n < 4; n++) {
      for (const [a, b, k] of TRIM_SEG) {
        const x0 = n * TRIM.P + a + 520 - off, x1 = n * TRIM.P + b + 520 - off;
        if (x1 < 40 || x0 > 680) continue;
        if (k !== 's' && x0 < TRIM.cut) continue; // 가위 왼쪽으로 넘어간 무음·습관어는 잘려 나갔다
        plate(ctx, x0 + 1, top - 12, x1 - x0 - 2, 14, 3, k === 's' ? '#1d1a12' : '#151515', k === 's' ? `rgba(${GOLD_RGB},0.6)` : STEEL_LINE, 1);
        if (k === 's') wave(ctx, x0 + 4, top - 5, x1 - x0 - 8, 5, n * 3 + a, t, 0, PAPER);
        else if (k === 'u') label(ctx, '음', (x0 + x1) / 2, top - 5, { size: 9, weight: 800, family: FONT_BODY, color: GRAY, align: 'center' });
        else {
          ctx.strokeStyle = '#444';
          ctx.beginPath();
          ctx.moveTo(x0 + 4, top - 5);
          ctx.lineTo(x1 - 4, top - 5);
          ctx.stroke();
        }
      }
    }
    ctx.restore();
    // 떨어지는 조각
    for (const s0 of snips) {
      const u = (t - s0) / 0.8;
      if (u < 0 || u > 1) continue;
      plate(ctx, TRIM.cut - 20 - u * 10, top - 8 + ease.inCubic(u) * 46, 30, 10, 3, '#151515', STEEL_LINE, 1);
    }
    // "음" 말풍선이 떠오르다 파리채에 맞는다
    for (const u0 of umms) {
      const u = (t - u0) / 1.0;
      if (u < 0 || u > 1.2) continue;
      const hit = t > u0 + 0.75;
      const bx = mix(TRIM.cut - 40, wx + 60, clamp(u)), by = top - 30 - clamp(u) * 60;
      if (!hit) bubble(ctx, bx, by, '음…', 1 - clamp((u - 0.9) / 0.2), 0, 12);
      else sparkle(ctx, wx + 58, F - 108, 14, pulse(t, u0 + 0.75, 0.4));
    }
    drawScissors(ctx, sh[0] - 6, sh[1], rad(turn > 0.5 ? -30 : 200), snip, 1.1);
    const dirSay = win(t, 5.1, 5.95, 0.12);
    director(ctx, t, { say: '음…', sayA: dirSay, wide: win(t, 5.95, 7.0, 0.15), eyes: 'normal' });
    sparkle(ctx, CHAIR.x - 40, SEAT - 108, 18, pulse(t, 5.95, 0.4));
    if (turn > 0.3) label(ctx, '✂', sx + 52, F - 104, { size: 18, weight: 800, color: GOLD, alpha: turn });
  },
};
