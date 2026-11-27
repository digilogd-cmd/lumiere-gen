// 로봇 스튜디오 위에 겹치는 "실제 진행" 표시 두 가지(대시보드에서만 — 미리보기 영상에는 없음).
//  ① 오른쪽 위 LIVE LOG: 실행기 기록(events.jsonl의 log)이 코드처럼 한 줄씩 타자로 올라온다
//  ② 왼쪽 위 이벤트 카드: 잘린 곳·개인정보 가림·단계 시작 같은 순간을 실제 장면 썸네일과 함께 잠깐 띄운다
import { clamp, roundRectPath, FONT_BODY, FONT_MONO } from './core.js';
import { GOLD, GOLD_RGB, PAPER, GRAY, STEEL_LINE, plate, label, dot } from './crew.js';

const LOG = { x: 658, y: 104, w: 278, h: 140, lines: 5, lh: 21, cps: 40 };
const CARD = { x: 30, y: 100, w: 278, h: 126, life: 3.6 };

function fit(ctx, s, w) {
  if (ctx.measureText(s).width <= w) return s;
  let lo = 0, hi = s.length;
  while (lo < hi) {
    const m = (lo + hi + 1) >> 1;
    if (ctx.measureText(s.slice(0, m) + '…').width <= w) lo = m;
    else hi = m - 1;
  }
  return s.slice(0, lo) + '…';
}

/** logs: [{ text, t0, kind:'info'|'warn'|'cut'|'ok' }] (오래된 것 → 새것) */
export function drawLog(ctx, now, logs) {
  if (!logs.length) return;
  const { x, y, w, h } = LOG;
  plate(ctx, x, y, w, h, 8, 'rgba(10,10,10,0.92)', STEEL_LINE, 1.2);
  label(ctx, 'LIVE LOG', x + 12, y + 13, { size: 9, weight: 700, color: GRAY, tracking: 0.25 });
  dot(ctx, x + w - 14, y + 13, 2.6, `rgba(${GOLD_RGB},${0.4 + 0.6 * (Math.floor(now * 2) % 2)})`);
  ctx.save();
  roundRectPath(ctx, x + 6, y + 22, w - 12, h - 28, 4);
  ctx.clip();
  // 새 줄이 들어오면 위로 밀려 올라간다(0.25초)
  const last = logs[logs.length - 1];
  const push = clamp((now - last.t0) / 0.25);
  const shown = logs.slice(-LOG.lines - 1);
  ctx.font = `500 12.5px ${FONT_MONO}`;
  shown.forEach((ln, i) => {
    const row = shown.length - 1 - i; // 0 = 맨 아래(새것)
    const yy = y + h - 14 - row * LOG.lh + (1 - push) * LOG.lh;
    const typed = Math.floor((now - ln.t0) * LOG.cps);
    if (typed <= 0) return;
    const full = fit(ctx, ln.text, w - 40);
    const txt = full.slice(0, typed);
    const col = ln.kind === 'warn' ? '#ffb224' : ln.kind === 'cut' ? '#ff6b5e' : ln.kind === 'ok' ? '#3ad07a' : PAPER;
    const fade = row >= LOG.lines - 1 ? 0.45 : 1 - row * 0.1;
    label(ctx, '›', x + 12, yy, { size: 12.5, weight: 700, color: GOLD, alpha: fade });
    label(ctx, txt, x + 25, yy, { size: 12.5, weight: 500, color: col, alpha: fade });
    if (row === 0 && typed < full.length + 6 && Math.floor(now * 3) % 2 === 0) {
      ctx.fillStyle = GOLD;
      ctx.fillRect(x + 26 + ctx.measureText(txt).width, yy - 7, 7, 14);
    }
  });
  ctx.restore();
}

/** card: { k, title, meta, img, t0 } */
export function drawCard(ctx, now, card) {
  if (!card) return;
  const age = now - card.t0;
  if (age < 0 || age > CARD.life) return;
  const a = clamp(Math.min(age / 0.25, (CARD.life - age) / 0.4));
  const { x, y, w, h } = CARD;
  ctx.save();
  ctx.globalAlpha *= a;
  ctx.translate((1 - a) * -14, 0);
  plate(ctx, x, y, w, h, 8, 'rgba(10,10,10,0.94)', `rgba(${GOLD_RGB},0.7)`, 1.4);
  let tx = x + 12;
  if (card.img && card.img.complete && card.img.naturalWidth) {
    const iw = 112, ih = 63;
    ctx.save();
    roundRectPath(ctx, x + 12, y + 12, iw, ih, 4);
    ctx.clip();
    const k = Math.max(iw / card.img.naturalWidth, ih / card.img.naturalHeight);
    ctx.drawImage(card.img, x + 12 + (iw - card.img.naturalWidth * k) / 2, y + 12 + (ih - card.img.naturalHeight * k) / 2, card.img.naturalWidth * k, card.img.naturalHeight * k);
    ctx.restore();
    if (card.cut) {
      ctx.strokeStyle = '#ff3b30';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x + 12, y + 12 + ih);
      ctx.lineTo(x + 12 + iw, y + 12);
      ctx.stroke();
    }
    tx = x + 136;
  }
  const tw = x + w - 12 - tx;
  ctx.font = `700 11px ${FONT_MONO}`;
  label(ctx, fit(ctx, (card.k || '').toUpperCase(), tw), tx, y + 21, { size: 11, weight: 700, color: GOLD, tracking: 0.12 });
  ctx.font = `700 18px ${FONT_BODY}`;
  const words = (card.title || '').split(' ');
  const lines = [''];
  for (const wd of words) {
    const tryL = lines[lines.length - 1] ? lines[lines.length - 1] + ' ' + wd : wd;
    if (ctx.measureText(tryL).width <= tw || !lines[lines.length - 1]) lines[lines.length - 1] = tryL;
    else if (lines.length < 2) lines.push(wd);
    else { lines[1] = fit(ctx, lines[1] + ' ' + wd, tw); break; }
  }
  lines.forEach((ln, i) => label(ctx, fit(ctx, ln, tw), tx, y + 46 + i * 24, { size: 18, weight: 700, family: FONT_BODY, color: PAPER }));
  if (card.meta) {
    ctx.font = `500 12px ${FONT_MONO}`;
    label(ctx, fit(ctx, card.meta, w - 24), x + 12, y + h - 17, { size: 12, weight: 500, color: GRAY });
  }
  ctx.restore();
}
