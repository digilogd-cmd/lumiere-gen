# -*- coding: utf-8 -*-
"""생성형 완성 폴더: work/<프로젝트>/완성/ 에 사용자가 쓸 파일만 알아보기 쉬운 이름으로(deliver.collect 가 생성형이면 여기로)."""
import glob, os

from ..core import jload
from ..deliver import _put
from .common import sdir


def collect_gen(P):
    out = P.p("완성")
    os.makedirs(out, exist_ok=True)
    got = []
    fd, td = sdir(P, "gen_final"), sdir(P, "gen_thumbs")
    fi = jload(os.path.join(fd, "final_info.json"), {})
    pairs = [(fi.get("out") or os.path.join(fd, "final.mp4"), "1_완성본.mp4"), (os.path.join(fd, "final.srt"), "1_자막.srt"),
             (os.path.join(td, "제목.txt"), "2_제목_후보.txt"), (os.path.join(td, "설명.txt"), "2_설명.txt"),
             (os.path.join(sdir(P, "gen_storyboard"), "콘티_스토리보드.jpg"), "5_콘티_스토리보드.jpg"),
             (os.path.join(sdir(P, "gen_script"), "대본.md"), "5_대본.md"), (P.p("결과_요약.md"), "0_결과_요약.md")]
    pairs += [(f, "3_" + os.path.basename(f)) for f in sorted(glob.glob(os.path.join(td, "썸네일_*.jpg"))) if not f.endswith("_s.jpg")]
    for src, name in pairs:
        if _put(src, os.path.join(out, name)):
            got.append(name)
    open(os.path.join(out, "읽어 주세요.txt"), "w", encoding="utf-8").write(
        "LUMIÈRE — 대본으로 만든 영상(생성형) 완성 파일 모음\n\n"
        "1_ 완성본과 자막 / 2_ 제목 후보·설명 / 3_ 썸네일 / 5_ 콘티 스토리보드·대본 / 0_ 결과 요약\n"
        "그림·영상 원본(워터마크 지운 것)은 gen_04_images/images, gen_06_video/video 에 있어요.\n"
        "유튜브에 올릴 때 'AI로 만든 콘텐츠' 항목을 체크해 주세요.\n")
    return out, got
